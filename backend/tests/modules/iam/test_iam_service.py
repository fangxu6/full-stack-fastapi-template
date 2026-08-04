import threading
import uuid

import pytest
from sqlmodel import Session, select

from app import crud
from app.core.audit import ensure_system_actor
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import AuditEvent, IamRole, User
from app.modules.iam import repository, service
from app.modules.iam.constants import PLATFORM_ADMINISTRATOR
from app.schemas.iam import RoleCreate, RoleUpdate
from app.schemas.user import UserCreate
from tests.utils.utils import random_email, random_lower_string


def _create_user(session: Session) -> User:
    return crud.create_user(
        session=session,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )


def test_zero_role_user_has_no_effective_permissions(db: Session) -> None:
    user = _create_user(db)

    result = service.get_effective_permissions(session=db, user_id=user.id)

    assert result.roles == []
    assert result.permissions == []


def test_custom_role_rejects_governance_permissions(db: Session) -> None:
    with pytest.raises(PermissionDeniedError):
        service.create_role(
            session=db,
            role_in=RoleCreate(
                code="forbidden_governance",
                name="Forbidden governance",
                permission_codes=["system.users.read"],
            ),
        )


def test_deactivated_role_stops_contributing_permissions(db: Session) -> None:
    user = _create_user(db)
    role = service.create_role(
        session=db,
        role_in=RoleCreate(
            code="document_reader",
            name="Document reader",
            permission_codes=["inventory.documents.read"],
        ),
    )
    service.replace_user_roles(session=db, user_id=user.id, role_ids=[role.id])

    assert (
        "inventory.documents.read"
        in service.get_effective_permissions(session=db, user_id=user.id).permissions
    )

    service.update_role(
        session=db, role_id=role.id, role_in=RoleUpdate(is_active=False)
    )

    assert (
        service.get_effective_permissions(session=db, user_id=user.id).permissions == []
    )


def test_replace_user_roles_retains_existing_inactive_role(db: Session) -> None:
    user = _create_user(db)
    role = service.create_role(
        session=db,
        role_in=RoleCreate(
            code="retained_inactive_role",
            name="Retained inactive role",
        ),
    )
    service.replace_user_roles(session=db, user_id=user.id, role_ids=[role.id])
    service.update_role(
        session=db, role_id=role.id, role_in=RoleUpdate(is_active=False)
    )

    roles = service.replace_user_roles(session=db, user_id=user.id, role_ids=[role.id])

    assert [assigned_role.id for assigned_role in roles] == [role.id]
    assert role.id in repository.get_user_role_ids(session=db, user_id=user.id)


def test_replace_user_roles_rejects_new_inactive_role(db: Session) -> None:
    user = _create_user(db)
    role = service.create_role(
        session=db,
        role_in=RoleCreate(
            code="new_inactive_role",
            name="New inactive role",
        ),
    )
    service.update_role(
        session=db, role_id=role.id, role_in=RoleUpdate(is_active=False)
    )

    with pytest.raises(ConflictError, match="Inactive roles cannot be assigned"):
        service.replace_user_roles(session=db, user_id=user.id, role_ids=[role.id])

    assert repository.get_user_role_ids(session=db, user_id=user.id) == set()


def test_replace_user_roles_rejects_the_system_actor_before_mutating_roles(
    db: Session,
) -> None:
    system_actor = ensure_system_actor(session=db)
    platform_role = repository.get_role_by_code(session=db, code=PLATFORM_ADMINISTRATOR)
    assert platform_role is not None
    assert platform_role.id is not None

    with pytest.raises(NotFoundError):
        service.replace_user_roles(
            session=db, user_id=system_actor.id, role_ids=[platform_role.id]
        )

    assert repository.get_user_role_ids(session=db, user_id=system_actor.id) == set()


def test_cannot_remove_last_active_platform_administrator(db: Session) -> None:
    first_superuser = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert first_superuser is not None
    platform_role = repository.get_role_by_code(session=db, code=PLATFORM_ADMINISTRATOR)
    assert platform_role is not None
    assert platform_role.id is not None

    with pytest.raises(ConflictError):
        service.replace_user_roles(session=db, user_id=first_superuser.id, role_ids=[])

    db.rollback()
    assert platform_role.id in repository.get_user_role_ids(
        session=db, user_id=first_superuser.id
    )


def test_concurrent_permission_replacements_are_serialized_by_role_lock(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = crud.get_user_by_email(session=db, email=settings.FIRST_SUPERUSER)
    assert actor is not None
    role = service.create_role(
        session=db,
        role_in=RoleCreate(
            code=f"serialized_permissions_{uuid.uuid4().hex[:12]}",
            name="Serialized permissions",
            permission_codes=["inventory.documents.read"],
        ),
    )
    db.commit()

    first_request_id = uuid.uuid4().hex
    second_request_id = uuid.uuid4().hex
    second_role_read_started = threading.Event()
    second_completed = threading.Event()
    second_errors: list[BaseException] = []
    original_get_role_by_id = repository.get_role_by_id

    def track_second_role_read(
        *, session: Session, role_id: int, lock: bool = False
    ) -> IamRole | None:
        if session is not first_session:
            second_role_read_started.set()
        if lock:
            return original_get_role_by_id(session=session, role_id=role_id, lock=True)
        return original_get_role_by_id(session=session, role_id=role_id)

    monkeypatch.setattr(repository, "get_role_by_id", track_second_role_read)

    with Session(engine) as first_session:
        locked_role = first_session.exec(
            select(IamRole).where(IamRole.id == role.id).with_for_update()
        ).one()
        assert locked_role.id == role.id
        service.replace_role_permissions(
            session=first_session,
            role_id=role.id,
            permission_codes=["inventory.ledger.read"],
            audit_actor_user_id=actor.id,
            audit_request_id=first_request_id,
        )

        def replace_permissions_in_second_session() -> None:
            try:
                with Session(engine) as second_session:
                    service.replace_role_permissions(
                        session=second_session,
                        role_id=role.id,
                        permission_codes=["inventory.balances.read"],
                        audit_actor_user_id=actor.id,
                        audit_request_id=second_request_id,
                    )
                    second_session.commit()
            except BaseException as error:
                second_errors.append(error)
            finally:
                second_completed.set()

        worker = threading.Thread(target=replace_permissions_in_second_session)
        worker.start()
        assert second_role_read_started.wait(timeout=1)
        assert not second_completed.wait(timeout=0.1)
        first_session.commit()

    worker.join(timeout=3)
    assert not worker.is_alive()
    assert second_errors == []

    db.expire_all()
    final_role = repository.get_role_by_id(session=db, role_id=role.id)
    assert final_role is not None
    assert repository.get_role_permission_codes(session=db, role_id=role.id) == [
        "inventory.balances.read"
    ]
    events = list(
        db.exec(
            select(AuditEvent)
            .where(AuditEvent.request_id.in_([first_request_id, second_request_id]))
            .order_by(AuditEvent.id)
        ).all()
    )
    assert [event.changes for event in events] == [
        {
            "permission_codes": {
                "before": ["inventory.documents.read"],
                "after": ["inventory.ledger.read"],
            }
        },
        {
            "permission_codes": {
                "before": ["inventory.ledger.read"],
                "after": ["inventory.balances.read"],
            }
        },
    ]

import pytest
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.core.exceptions import ConflictError, PermissionDeniedError
from app.models import User
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

    assert "inventory.documents.read" in service.get_effective_permissions(
        session=db, user_id=user.id
    ).permissions

    service.update_role(
        session=db, role_id=role.id, role_in=RoleUpdate(is_active=False)
    )

    assert service.get_effective_permissions(session=db, user_id=user.id).permissions == []


def test_cannot_remove_last_active_platform_administrator(db: Session) -> None:
    first_superuser = crud.get_user_by_email(
        session=db, email=settings.FIRST_SUPERUSER
    )
    assert first_superuser is not None
    platform_role = repository.get_role_by_code(
        session=db, code=PLATFORM_ADMINISTRATOR
    )
    assert platform_role is not None
    assert platform_role.id is not None

    with pytest.raises(ConflictError):
        service.replace_user_roles(
            session=db, user_id=first_superuser.id, role_ids=[]
        )

    assert platform_role.id in repository.get_user_role_ids(
        session=db, user_id=first_superuser.id
    )

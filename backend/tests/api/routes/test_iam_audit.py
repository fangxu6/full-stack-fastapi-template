import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.models import AuditEvent, IamRole, User
from app.schemas.user import UserCreate
from tests.utils.utils import random_email, random_lower_string

IAM_PATH = f"{settings.API_V1_STR}/iam"


def _role_payload(code: str) -> dict[str, object]:
    return {
        "code": code,
        "name": "Audit role",
        "permission_codes": ["inventory.documents.read"],
    }


def test_iam_mutations_append_one_semantic_event(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    request_id = uuid.uuid4().hex
    headers = {**superuser_token_headers, "X-Request-ID": request_id}
    role_code = f"audit_{uuid.uuid4().hex[:16]}"

    created = client.post(
        f"{IAM_PATH}/roles", headers=headers, json=_role_payload(role_code)
    )
    assert created.status_code == 200, created.json()
    assert created.headers["X-Request-ID"] == request_id
    role_id = created.json()["id"]

    assert (
        client.patch(
            f"{IAM_PATH}/roles/{role_id}",
            headers=headers,
            json={"name": "Renamed audit role"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"{IAM_PATH}/roles/{role_id}",
            headers=headers,
            json={"is_active": False, "description": "Not stored in the audit row"},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"{IAM_PATH}/roles/{role_id}",
            headers=headers,
            json={"is_active": True},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{IAM_PATH}/roles/{role_id}/permissions",
            headers=headers,
            json={"permission_codes": ["inventory.ledger.read"]},
        ).status_code
        == 200
    )

    target_user = crud.create_user(
        session=db,
        user_create=UserCreate(email=random_email(), password=random_lower_string()),
    )
    db.commit()
    assert (
        client.put(
            f"{IAM_PATH}/users/{target_user.id}/roles",
            headers=headers,
            json={"role_ids": [role_id]},
        ).status_code
        == 200
    )

    deletable_role = client.post(
        f"{IAM_PATH}/roles",
        headers=headers,
        json=_role_payload(f"audit_{uuid.uuid4().hex[:16]}"),
    )
    assert deletable_role.status_code == 200, deletable_role.json()
    deletable_role_id = deletable_role.json()["id"]
    assert (
        client.patch(
            f"{IAM_PATH}/roles/{deletable_role_id}",
            headers=headers,
            json={"is_active": False},
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"{IAM_PATH}/roles/{deletable_role_id}", headers=headers
        ).status_code
        == 200
    )

    db.expire_all()
    events = list(
        db.exec(
            select(AuditEvent)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.id)
        ).all()
    )
    actor = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()

    assert [event.action for event in events] == [
        "iam.role.created",
        "iam.role.updated",
        "iam.role.deactivated",
        "iam.role.activated",
        "iam.role.permissions_replaced",
        "iam.user.roles_replaced",
        "iam.role.created",
        "iam.role.deactivated",
        "iam.role.deleted",
    ]
    assert all(event.actor_user_id == actor.id for event in events)
    assert events[0].changes == {
        "code": role_code,
        "permission_codes": ["inventory.documents.read"],
    }
    assert events[1].changes == {"changed_fields": ["name"]}
    assert events[2].changes == {
        "is_active": {"before": True, "after": False},
        "changed_fields": ["description"],
    }
    assert events[3].changes == {"is_active": {"before": False, "after": True}}
    assert events[4].changes == {
        "permission_codes": {
            "before": ["inventory.documents.read"],
            "after": ["inventory.ledger.read"],
        }
    }
    assert events[5].changes == {"role_ids": {"before": [], "after": [role_id]}}
    assert events[-1].resource_id == str(deletable_role_id)
    assert events[-1].changes == {}


def test_failed_iam_mutation_does_not_append_an_event(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    code = f"audit_{uuid.uuid4().hex[:16]}"
    assert (
        client.post(
            f"{IAM_PATH}/roles",
            headers=superuser_token_headers,
            json=_role_payload(code),
        ).status_code
        == 200
    )
    db.expire_all()
    before = len(list(db.exec(select(AuditEvent)).all()))

    response = client.post(
        f"{IAM_PATH}/roles",
        headers=superuser_token_headers,
        json=_role_payload(code),
    )

    assert response.status_code == 409
    db.expire_all()
    assert len(list(db.exec(select(AuditEvent)).all())) == before


def test_empty_role_patch_is_rejected_without_audit_side_effect(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    role = client.post(
        f"{IAM_PATH}/roles",
        headers=superuser_token_headers,
        json=_role_payload(f"audit_{uuid.uuid4().hex[:16]}"),
    )
    assert role.status_code == 200, role.json()
    role_id = role.json()["id"]
    db.expire_all()
    role_before = db.get(IamRole, role_id)
    assert role_before is not None
    updated_at_before = role_before.updated_at
    event_count_before = len(list(db.exec(select(AuditEvent)).all()))
    request_id = uuid.uuid4().hex

    response = client.patch(
        f"{IAM_PATH}/roles/{role_id}",
        headers={**superuser_token_headers, "X-Request-ID": request_id},
        json={},
    )

    assert response.status_code == 422, response.json()
    assert response.headers["X-Request-ID"] == request_id
    assert response.json() == {
        "detail": "Role update does not change any fields",
        "request_id": request_id,
    }
    db.expire_all()
    role_after = db.get(IamRole, role_id)
    assert role_after is not None
    assert role_after.updated_at == updated_at_before
    assert len(list(db.exec(select(AuditEvent)).all())) == event_count_before


def test_same_value_role_patch_is_rejected_without_audit_side_effect(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    role = client.post(
        f"{IAM_PATH}/roles",
        headers=superuser_token_headers,
        json=_role_payload(f"audit_{uuid.uuid4().hex[:16]}"),
    )
    assert role.status_code == 200, role.json()
    role_id = role.json()["id"]
    db.expire_all()
    role_before = db.get(IamRole, role_id)
    assert role_before is not None
    updated_at_before = role_before.updated_at
    event_count_before = len(list(db.exec(select(AuditEvent)).all()))
    request_id = uuid.uuid4().hex

    response = client.patch(
        f"{IAM_PATH}/roles/{role_id}",
        headers={**superuser_token_headers, "X-Request-ID": request_id},
        json={"name": role_before.name},
    )

    assert response.status_code == 422, response.json()
    assert response.headers["X-Request-ID"] == request_id
    assert response.json() == {
        "detail": "Role update does not change any fields",
        "request_id": request_id,
    }
    db.expire_all()
    role_after = db.get(IamRole, role_id)
    assert role_after is not None
    assert role_after.updated_at == updated_at_before
    assert len(list(db.exec(select(AuditEvent)).all())) == event_count_before


def test_role_patch_audit_lists_only_actual_changed_fields(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    role = client.post(
        f"{IAM_PATH}/roles",
        headers=superuser_token_headers,
        json=_role_payload(f"audit_{uuid.uuid4().hex[:16]}"),
    )
    assert role.status_code == 200, role.json()
    request_id = uuid.uuid4().hex

    response = client.patch(
        f"{IAM_PATH}/roles/{role.json()['id']}",
        headers={**superuser_token_headers, "X-Request-ID": request_id},
        json={"is_active": True, "name": "Audit role renamed"},
    )

    assert response.status_code == 200, response.json()
    db.expire_all()
    event = db.exec(select(AuditEvent).where(AuditEvent.request_id == request_id)).one()
    assert event.action == "iam.role.updated"
    assert event.changes == {"changed_fields": ["name"]}

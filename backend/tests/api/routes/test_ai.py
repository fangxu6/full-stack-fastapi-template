import pytest
import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app import crud
from app.core.config import settings
from app.modules.ai.service import create_ai_run, issue_actor_grant
from app.schemas.user import UserCreate
from tests.utils.utils import random_email, random_lower_string


def test_inventory_ai_query_fails_closed_when_disabled(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/ai/inventory/query",
        headers=superuser_token_headers,
        json={"question": "查询原料库存余额"},
    )

    assert response.status_code == HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "detail": "AI inventory query is disabled",
        "request_id": response.headers["X-Request-ID"],
    }


def test_internal_balances_requires_credentials_then_uses_inventory_projection(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service_token = "internal-service-token-at-least-32-bytes"
    signing_key = "test-grant-signing-key-at-least-32-bytes"
    monkeypatch.setattr(settings, "AI_INTERNAL_SERVICE_TOKEN", service_token)
    monkeypatch.setattr(settings, "AI_ACTOR_GRANT_SIGNING_KEY", signing_key)
    actor = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            is_superuser=True,
        ),
    )
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-balances",
        question="Show finished inventory",
        allowed_scopes=["inventory:balances"],
        max_tool_calls=1,
    )
    actor_grant = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)

    response = client.post(
        "/api/v1/internal/ai/inventory/balances",
        headers={
            "X-AI-Service-Token": service_token,
            "X-AI-Actor-Grant": actor_grant,
        },
        json={
            "run_id": str(run.id),
            "actor_user_id": str(actor.id),
            "ledger_kind": "FINISHED",
            "skip": 0,
            "limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "tool_name": "balances",
        "source": "inventory:balances",
        "result": {"data": [], "count": 0},
    }


@pytest.mark.parametrize(
    ("path", "scope", "tool_name", "source"),
    [
        (
            "/api/v1/internal/ai/inventory/processing-units",
            "inventory:processing_units",
            "processing_units",
            "inventory:processing_units",
        ),
        (
            "/api/v1/internal/ai/inventory/receiving-units",
            "inventory:receiving_units",
            "receiving_units",
            "inventory:receiving_units",
        ),
    ],
)
def test_internal_units_use_their_scoped_inventory_projection(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    scope: str,
    tool_name: str,
    source: str,
) -> None:
    service_token = "internal-service-token-at-least-32-bytes"
    signing_key = "test-grant-signing-key-at-least-32-bytes"
    monkeypatch.setattr(settings, "AI_INTERNAL_SERVICE_TOKEN", service_token)
    monkeypatch.setattr(settings, "AI_ACTOR_GRANT_SIGNING_KEY", signing_key)
    actor = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            is_superuser=True,
        ),
    )
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id=f"request-ai-{tool_name}",
        question="List inventory units",
        allowed_scopes=[scope],
        max_tool_calls=1,
    )
    actor_grant = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)

    response = client.post(
        path,
        headers={
            "X-AI-Service-Token": service_token,
            "X-AI-Actor-Grant": actor_grant,
        },
        json={"run_id": str(run.id), "actor_user_id": str(actor.id)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tool_name": tool_name,
        "source": source,
        "result": {"data": [], "count": 0},
    }


def test_internal_documents_use_read_only_inventory_projection(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service_token = "internal-service-token-at-least-32-bytes"
    signing_key = "test-grant-signing-key-at-least-32-bytes"
    monkeypatch.setattr(settings, "AI_INTERNAL_SERVICE_TOKEN", service_token)
    monkeypatch.setattr(settings, "AI_ACTOR_GRANT_SIGNING_KEY", signing_key)
    actor = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            is_superuser=True,
        ),
    )
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-documents",
        question="List inventory documents",
        allowed_scopes=["inventory:documents"],
        max_tool_calls=1,
    )
    actor_grant = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)

    response = client.post(
        "/api/v1/internal/ai/inventory/documents",
        headers={
            "X-AI-Service-Token": service_token,
            "X-AI-Actor-Grant": actor_grant,
        },
        json={"run_id": str(run.id), "actor_user_id": str(actor.id)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tool_name": "documents",
        "source": "inventory:documents",
        "result": {"data": [], "count": 0},
    }


def test_internal_ledger_uses_a_scoped_exact_inventory_key(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service_token = "internal-service-token-at-least-32-bytes"
    signing_key = "test-grant-signing-key-at-least-32-bytes"
    monkeypatch.setattr(settings, "AI_INTERNAL_SERVICE_TOKEN", service_token)
    monkeypatch.setattr(settings, "AI_ACTOR_GRANT_SIGNING_KEY", signing_key)
    actor = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(), password=random_lower_string(), is_superuser=True
        ),
    )
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-ledger",
        question="Show ledger",
        allowed_scopes=["inventory:ledger"],
        max_tool_calls=1,
    )
    grant = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)
    response = client.post(
        "/api/v1/internal/ai/inventory/ledger",
        headers={"X-AI-Service-Token": service_token, "X-AI-Actor-Grant": grant},
        json={
            "run_id": str(run.id),
            "actor_user_id": str(actor.id),
            "ledger_kind": "FINISHED",
            "processing_unit_id": str(uuid.uuid4()),
            "item_name": "Item",
            "wool_content": "100%",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "tool_name": "ledger",
        "source": "inventory:ledger",
        "result": {"data": [], "count": 0},
    }

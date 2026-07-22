import hashlib
import uuid
from typing import cast

import httpx
import pytest
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError
from app.models.ai import AiRunStatus, AiToolCallStatus
from app.modules.ai.service import (
    AI_ORCHESTRATOR_TIMEOUT_SECONDS,
    authorize_internal_tool_call,
    call_inventory_sidecar,
    complete_tool_call,
    create_ai_run,
    fail_ai_run,
    issue_actor_grant,
    reserve_tool_call,
    validate_actor_grant,
    validate_internal_service_token,
)
from tests.utils.user import create_legacy_superuser


def test_reserving_a_tool_call_creates_auditable_run_bound_slot(db: Session) -> None:
    actor = create_legacy_superuser(db)
    question = "What is the finished inventory balance?"
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-123",
        question=question,
        allowed_scopes=["inventory:balances"],
        max_tool_calls=2,
    )

    tool_call = reserve_tool_call(
        session=db,
        run_id=run.id,
        actor_user_id=actor.id,
        tool_name="balances",
        input_summary={"ledger_kind": "FINISHED"},
    )

    db.refresh(run)
    assert run.status is AiRunStatus.PENDING
    assert run.question_hash == hashlib.sha256(question.encode()).hexdigest()
    assert run.used_tool_calls == 1
    assert run.created_by == actor.id
    assert run.updated_by == actor.id
    assert tool_call.run_id == run.id
    assert tool_call.sequence == 1
    assert tool_call.status is AiToolCallStatus.PENDING
    assert tool_call.created_by == actor.id
    assert tool_call.updated_by == actor.id


def test_actor_grant_is_bound_to_its_run_actor_and_scope(db: Session) -> None:
    actor = create_legacy_superuser(db)
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-grant",
        question="Show current finished inventory",
        allowed_scopes=["inventory:balances"],
        max_tool_calls=2,
    )

    signing_key = "test-grant-signing-key-at-least-32-bytes"
    token = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)

    claims = validate_actor_grant(
        token=token,
        signing_key=signing_key,
        run_id=run.id,
        actor_user_id=actor.id,
        required_scope="inventory:balances",
    )
    assert claims["run_id"] == str(run.id)
    assert claims["sub"] == str(actor.id)
    with pytest.raises(PermissionDeniedError):
        validate_actor_grant(
            token=token,
            signing_key=signing_key,
            run_id=run.id,
            actor_user_id=actor.id,
            required_scope="inventory:documents",
        )


def test_internal_service_token_uses_a_strict_server_side_match() -> None:
    expected_token = "internal-service-token-at-least-32-bytes"

    validate_internal_service_token(
        supplied_token=expected_token,
        expected_token=expected_token,
    )

    with pytest.raises(PermissionDeniedError):
        validate_internal_service_token(
            supplied_token="wrong-token",
            expected_token=expected_token,
        )


def test_inventory_sidecar_call_uses_the_ninety_second_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_ORCHESTRATOR_URL", "http://sidecar:3000")
    monkeypatch.setattr(settings, "AI_ORCHESTRATOR_SERVICE_TOKEN", "service-token")
    captured_timeout: float | None = None

    def fake_post(*_: object, **kwargs: object) -> httpx.Response:
        nonlocal captured_timeout
        captured_timeout = cast(float, kwargs["timeout"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", "http://sidecar:3000"),
            json={
                "status": "completed",
                "answer": "当前无成品库存余额。",
                "citations": [
                    {
                        "tool_name": "balances",
                        "source": "inventory:balances",
                        "summary": "已查询成品库存余额，共 0 条",
                    }
                ],
                "provider_metadata": {
                    "provider": "internal-gateway",
                    "model": "gpt-5.6-luna",
                    "provider_request_id": None,
                    "latency_ms": 1,
                    "input_tokens": None,
                    "output_tokens": None,
                },
            },
        )

    monkeypatch.setattr("app.modules.ai.service.httpx.post", fake_post)

    response = call_inventory_sidecar(
        run_id=uuid.uuid4(),
        question="查询成品库存",
        request_id="request-timeout-90",
        actor_grant="grant",
    )

    assert response.status == "completed"
    assert captured_timeout == AI_ORCHESTRATOR_TIMEOUT_SECONDS == 90.0


def test_completing_a_tool_call_records_only_its_source_summary(db: Session) -> None:
    actor = create_legacy_superuser(db)
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-complete",
        question="Show balance",
        allowed_scopes=["inventory:balances"],
        max_tool_calls=1,
    )
    tool_call = reserve_tool_call(
        session=db,
        run_id=run.id,
        actor_user_id=actor.id,
        tool_name="balances",
        input_summary={"ledger_kind": "FINISHED"},
    )

    completed = complete_tool_call(
        session=db,
        tool_call=tool_call,
        actor_user_id=actor.id,
        source_summary={"source": "inventory:balances", "count": 0},
    )

    assert completed.status is AiToolCallStatus.COMPLETED
    assert completed.source_summary == {"source": "inventory:balances", "count": 0}


def test_failing_a_run_records_only_its_error_category(db: Session) -> None:
    actor = create_legacy_superuser(db)
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-failed",
        question="Show balance",
        allowed_scopes=["inventory:balances"],
        max_tool_calls=1,
    )
    failed = fail_ai_run(
        session=db,
        run=run,
        actor_user_id=actor.id,
        error_category="orchestrator_unavailable",
    )
    assert failed.status is AiRunStatus.FAILED
    assert failed.error_category == "orchestrator_unavailable"
    assert failed.completed_at is not None


def test_internal_tool_authorization_validates_credentials_before_reserving_slot(
    db: Session,
) -> None:
    actor = create_legacy_superuser(db)
    run = create_ai_run(
        session=db,
        actor_user_id=actor.id,
        request_id="request-ai-internal",
        question="Show finished inventory",
        allowed_scopes=["inventory:balances"],
        max_tool_calls=1,
    )
    signing_key = "test-grant-signing-key-at-least-32-bytes"
    grant = issue_actor_grant(run=run, signing_key=signing_key, ttl_seconds=60)

    tool_call = authorize_internal_tool_call(
        session=db,
        service_token="internal-service-token-at-least-32-bytes",
        expected_service_token="internal-service-token-at-least-32-bytes",
        actor_grant=grant,
        grant_signing_key=signing_key,
        run_id=run.id,
        actor_user_id=actor.id,
        required_scope="inventory:balances",
        tool_name="balances",
        input_summary={"ledger_kind": "FINISHED"},
    )

    assert tool_call.sequence == 1
    with pytest.raises(PermissionDeniedError):
        authorize_internal_tool_call(
            session=db,
            service_token="wrong-token",
            expected_service_token="internal-service-token-at-least-32-bytes",
            actor_grant=grant,
            grant_signing_key=signing_key,
            run_id=run.id,
            actor_user_id=actor.id,
            required_scope="inventory:balances",
            tool_name="balances",
            input_summary={"ledger_kind": "FINISHED"},
        )

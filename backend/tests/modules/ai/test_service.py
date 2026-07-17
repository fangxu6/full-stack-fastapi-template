import hashlib

import pytest
from sqlmodel import Session

from app import crud
from app.core.exceptions import PermissionDeniedError
from app.models.ai import AiRunStatus, AiToolCallStatus
from app.modules.ai.service import (
    create_ai_run,
    issue_actor_grant,
    authorize_internal_tool_call,
    reserve_tool_call,
    validate_actor_grant,
    validate_internal_service_token,
)
from app.schemas.user import UserCreate
from tests.utils.utils import random_email, random_lower_string


def test_reserving_a_tool_call_creates_auditable_run_bound_slot(db: Session) -> None:
    actor = crud.create_user(
        session=db,
        user_create=UserCreate(
            email=random_email(),
            password=random_lower_string(),
            is_superuser=True,
        ),
    )
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


def test_internal_tool_authorization_validates_credentials_before_reserving_slot(
    db: Session,
) -> None:
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

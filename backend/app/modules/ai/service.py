import hashlib
import secrets
import uuid
from datetime import timedelta

import httpx
import jwt
from sqlalchemy import update
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError, ServiceUnavailableError
from app.models.ai import AiRun, AiRunStatus, AiToolCall, AiToolCallStatus
from app.models.base import get_datetime_utc
from app.schemas.ai import AiSidecarCompletedResponse

ACTOR_GRANT_ALGORITHM = "HS256"
ACTOR_GRANT_ISSUER = "full-stack-fastapi-template.ai"
ACTOR_GRANT_AUDIENCE = "ai-inventory-orchestrator"


def create_ai_run(
    *,
    session: Session,
    actor_user_id: uuid.UUID,
    request_id: str,
    question: str,
    allowed_scopes: list[str],
    max_tool_calls: int,
) -> AiRun:
    now = get_datetime_utc()
    run = AiRun(
        request_id=request_id,
        user_id=actor_user_id,
        status=AiRunStatus.PENDING,
        question_hash=hashlib.sha256(question.encode("utf-8")).hexdigest(),
        allowed_scopes=allowed_scopes,
        max_tool_calls=max_tool_calls,
        started_at=now,
        created_at=now,
        created_by=actor_user_id,
        updated_at=now,
        updated_by=actor_user_id,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def reserve_tool_call(
    *,
    session: Session,
    run_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    tool_name: str,
    input_summary: dict[str, object],
) -> AiToolCall:
    now = get_datetime_utc()
    run_table = AiRun.__table__  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
    statement = (
        update(run_table)
        .where(
            run_table.c.id == run_id,
            run_table.c.user_id == actor_user_id,
            run_table.c.status == AiRunStatus.PENDING,
            run_table.c.deleted_at.is_(None),
            run_table.c.used_tool_calls < run_table.c.max_tool_calls,
        )
        .values(
            used_tool_calls=run_table.c.used_tool_calls + 1,
            updated_at=now,
            updated_by=actor_user_id,
        )
        .returning(run_table.c.used_tool_calls)
    )
    row = session.exec(statement).one_or_none()
    if row is None:
        session.rollback()
        raise PermissionDeniedError("AI tool call is not authorized")
    sequence = row[0]

    tool_call = AiToolCall(
        run_id=run_id,
        sequence=sequence,
        tool_name=tool_name,
        status=AiToolCallStatus.PENDING,
        input_summary=input_summary,
        source_summary={},
        created_at=now,
        created_by=actor_user_id,
        updated_at=now,
        updated_by=actor_user_id,
    )
    try:
        session.add(tool_call)
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(tool_call)
    return tool_call


def complete_tool_call(
    *,
    session: Session,
    tool_call: AiToolCall,
    actor_user_id: uuid.UUID,
    source_summary: dict[str, object],
) -> AiToolCall:
    if tool_call.status is not AiToolCallStatus.PENDING:
        raise PermissionDeniedError("AI tool call is not authorized")
    tool_call.status = AiToolCallStatus.COMPLETED
    tool_call.source_summary = source_summary
    tool_call.updated_at = get_datetime_utc()
    tool_call.updated_by = actor_user_id
    session.add(tool_call)
    session.commit()
    session.refresh(tool_call)
    return tool_call


def fail_ai_run(
    *, session: Session, run: AiRun, actor_user_id: uuid.UUID, error_category: str
) -> AiRun:
    run.status = AiRunStatus.FAILED
    run.error_category = error_category
    run.completed_at = get_datetime_utc()
    run.updated_at = run.completed_at
    run.updated_by = actor_user_id
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def complete_ai_run(
    *,
    session: Session,
    run: AiRun,
    actor_user_id: uuid.UUID,
    provider: str,
    model: str,
) -> AiRun:
    run.status = AiRunStatus.COMPLETED
    run.provider = provider
    run.model = model
    run.completed_at = get_datetime_utc()
    run.updated_at = run.completed_at
    run.updated_by = actor_user_id
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def call_inventory_sidecar(
    *, run_id: uuid.UUID, question: str, request_id: str, actor_grant: str
) -> AiSidecarCompletedResponse:
    orchestrator_url = settings.AI_ORCHESTRATOR_URL
    service_token = settings.AI_ORCHESTRATOR_SERVICE_TOKEN
    if not orchestrator_url or not service_token:
        raise ServiceUnavailableError("AI inventory query is not configured")

    try:
        response = httpx.post(
            f"{str(orchestrator_url).rstrip('/')}/v1/inventory/query",
            headers={
                "X-AI-Orchestrator-Token": service_token,
                "X-AI-Actor-Grant": actor_grant,
                "X-Request-ID": request_id,
            },
            json={"run_id": str(run_id), "question": question},
            timeout=30.0,
        )
        response.raise_for_status()
        return AiSidecarCompletedResponse.model_validate(response.json())
    except (httpx.HTTPError, ValueError) as err:
        raise ServiceUnavailableError("AI inventory query is unavailable") from err


def issue_actor_grant(*, run: AiRun, signing_key: str, ttl_seconds: int) -> str:
    if run.status is not AiRunStatus.PENDING or ttl_seconds <= 0:
        raise PermissionDeniedError("AI actor grant is not authorized")
    now = get_datetime_utc()
    return jwt.encode(
        {
            "iss": ACTOR_GRANT_ISSUER,
            "aud": ACTOR_GRANT_AUDIENCE,
            "sub": str(run.user_id),
            "run_id": str(run.id),
            "scopes": run.allowed_scopes,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        },
        signing_key,
        algorithm=ACTOR_GRANT_ALGORITHM,
    )


def validate_actor_grant(
    *,
    token: str,
    signing_key: str,
    run_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    required_scope: str,
) -> dict[str, object]:
    try:
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=[ACTOR_GRANT_ALGORITHM],
            audience=ACTOR_GRANT_AUDIENCE,
            issuer=ACTOR_GRANT_ISSUER,
        )
    except jwt.InvalidTokenError as err:
        raise PermissionDeniedError("AI actor grant is not authorized") from err

    scopes = claims.get("scopes")
    if (
        claims.get("run_id") != str(run_id)
        or claims.get("sub") != str(actor_user_id)
        or not isinstance(scopes, list)
        or required_scope not in scopes
    ):
        raise PermissionDeniedError("AI actor grant is not authorized")
    return dict(claims)


def validate_internal_service_token(
    *, supplied_token: str | None, expected_token: str | None
) -> None:
    if (
        not supplied_token
        or not expected_token
        or not secrets.compare_digest(supplied_token, expected_token)
    ):
        raise PermissionDeniedError("AI internal service is not authorized")


def authorize_internal_tool_call(
    *,
    session: Session,
    service_token: str | None,
    expected_service_token: str | None,
    actor_grant: str,
    grant_signing_key: str,
    run_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    required_scope: str,
    tool_name: str,
    input_summary: dict[str, object],
) -> AiToolCall:
    validate_internal_service_token(
        supplied_token=service_token,
        expected_token=expected_service_token,
    )
    validate_actor_grant(
        token=actor_grant,
        signing_key=grant_signing_key,
        run_id=run_id,
        actor_user_id=actor_user_id,
        required_scope=required_scope,
    )
    return reserve_tool_call(
        session=session,
        run_id=run_id,
        actor_user_id=actor_user_id,
        tool_name=tool_name,
        input_summary=input_summary,
    )

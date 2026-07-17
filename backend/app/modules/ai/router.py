from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.api.deps import SessionDep, get_current_active_superuser
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.models import User
from app.models.inventory import InventoryLedgerKind
from app.modules.ai import service
from app.modules.inventory import service as inventory_service
from app.schemas.ai import (
    AiInternalBalancesRequest,
    AiInternalBalancesResponse,
    AiInternalDocumentsRequest,
    AiInternalDocumentsResponse,
    AiInternalLedgerRequest,
    AiInternalLedgerResponse,
    AiInternalUnitsRequest,
    AiInternalUnitsResponse,
    AiInventoryCitation,
    AiInventoryQueryRequest,
    AiInventoryQueryResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])
internal_router = APIRouter(
    prefix="/internal/ai/inventory", tags=["ai-internal"], include_in_schema=False
)


@router.post("/inventory/query", response_model=AiInventoryQueryResponse)
def query_inventory(
    query: AiInventoryQueryRequest,
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    session: SessionDep,
    request: Request,
) -> AiInventoryQueryResponse:
    if not settings.AI_ENABLED:
        raise ServiceUnavailableError("AI inventory query is disabled")
    run = service.create_ai_run(
        session=session,
        actor_user_id=current_user.id,
        request_id=request.state.request_id,
        question=query.question,
        allowed_scopes=[
            "inventory:balances",
            "inventory:documents",
            "inventory:ledger",
            "inventory:processing_units",
            "inventory:receiving_units",
        ],
        max_tool_calls=settings.AI_MAX_TOOL_CALLS,
    )
    actor_grant = service.issue_actor_grant(
        run=run,
        signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        ttl_seconds=settings.AI_ACTOR_GRANT_TTL_SECONDS,
    )
    try:
        sidecar_response = service.call_inventory_sidecar(
            run_id=run.id,
            question=query.question,
            request_id=request.state.request_id,
            actor_grant=actor_grant,
        )
    except ServiceUnavailableError:
        service.fail_ai_run(
            session=session,
            run=run,
            actor_user_id=current_user.id,
            error_category="orchestrator_unavailable",
        )
        raise
    service.complete_ai_run(
        session=session,
        run=run,
        actor_user_id=current_user.id,
        provider="openai",
        model=sidecar_response.provider_metadata.model,
    )
    return AiInventoryQueryResponse(
        run_id=run.id,
        answer=sidecar_response.answer,
        citations=[
            AiInventoryCitation.model_validate(citation)
            for citation in sidecar_response.citations
        ],
    )


@internal_router.post("/balances", response_model=AiInternalBalancesResponse)
def read_internal_balances(
    request: AiInternalBalancesRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalBalancesResponse:
    tool_call = service.authorize_internal_tool_call(
        session=session,
        service_token=service_token,
        expected_service_token=settings.AI_INTERNAL_SERVICE_TOKEN,
        actor_grant=actor_grant or "",
        grant_signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        run_id=request.run_id,
        actor_user_id=request.actor_user_id,
        required_scope="inventory:balances",
        tool_name="balances",
        input_summary={"ledger_kind": request.ledger_kind.value},
    )
    result = inventory_service.list_balances(
        session=session,
        ledger_kind=InventoryLedgerKind(request.ledger_kind),
        skip=request.skip,
        limit=request.limit,
        processing_unit_id=request.processing_unit_id,
        item_name=request.item_name,
    )
    service.complete_tool_call(
        session=session,
        tool_call=tool_call,
        actor_user_id=request.actor_user_id,
        source_summary={"source": "inventory:balances", "count": result.count},
    )
    return AiInternalBalancesResponse(
        tool_name="balances",
        source="inventory:balances",
        result=result,
    )


@internal_router.post("/processing-units", response_model=AiInternalUnitsResponse)
def read_internal_processing_units(
    request: AiInternalUnitsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalUnitsResponse:
    tool_call = service.authorize_internal_tool_call(
        session=session,
        service_token=service_token,
        expected_service_token=settings.AI_INTERNAL_SERVICE_TOKEN,
        actor_grant=actor_grant or "",
        grant_signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        run_id=request.run_id,
        actor_user_id=request.actor_user_id,
        required_scope="inventory:processing_units",
        tool_name="processing_units",
        input_summary={},
    )
    result = inventory_service.list_processing_units(
        session=session,
        name=request.name,
        is_active=request.is_active,
        skip=request.skip,
        limit=request.limit,
    )
    service.complete_tool_call(
        session=session,
        tool_call=tool_call,
        actor_user_id=request.actor_user_id,
        source_summary={"source": "inventory:processing_units", "count": result.count},
    )
    return AiInternalUnitsResponse(
        tool_name="processing_units",
        source="inventory:processing_units",
        result=result,
    )


@internal_router.post("/receiving-units", response_model=AiInternalUnitsResponse)
def read_internal_receiving_units(
    request: AiInternalUnitsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalUnitsResponse:
    tool_call = service.authorize_internal_tool_call(
        session=session,
        service_token=service_token,
        expected_service_token=settings.AI_INTERNAL_SERVICE_TOKEN,
        actor_grant=actor_grant or "",
        grant_signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        run_id=request.run_id,
        actor_user_id=request.actor_user_id,
        required_scope="inventory:receiving_units",
        tool_name="receiving_units",
        input_summary={},
    )
    result = inventory_service.list_receiving_units(
        session=session,
        name=request.name,
        is_active=request.is_active,
        skip=request.skip,
        limit=request.limit,
    )
    service.complete_tool_call(
        session=session,
        tool_call=tool_call,
        actor_user_id=request.actor_user_id,
        source_summary={"source": "inventory:receiving_units", "count": result.count},
    )
    return AiInternalUnitsResponse(
        tool_name="receiving_units",
        source="inventory:receiving_units",
        result=result,
    )


@internal_router.post("/documents", response_model=AiInternalDocumentsResponse)
def read_internal_documents(
    request: AiInternalDocumentsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalDocumentsResponse:
    tool_call = service.authorize_internal_tool_call(
        session=session,
        service_token=service_token,
        expected_service_token=settings.AI_INTERNAL_SERVICE_TOKEN,
        actor_grant=actor_grant or "",
        grant_signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        run_id=request.run_id,
        actor_user_id=request.actor_user_id,
        required_scope="inventory:documents",
        tool_name="documents",
        input_summary={},
    )
    result = inventory_service.list_documents(
        session=session,
        skip=request.skip,
        limit=request.limit,
        document_type=request.document_type,
        business_date_from=request.business_date_from,
        business_date_to=request.business_date_to,
        processing_unit_id=request.processing_unit_id,
        receiving_unit_id=request.receiving_unit_id,
        document_number=request.document_number,
        include_deleted=False,
    )
    service.complete_tool_call(
        session=session,
        tool_call=tool_call,
        actor_user_id=request.actor_user_id,
        source_summary={"source": "inventory:documents", "count": result.count},
    )
    return AiInternalDocumentsResponse(
        tool_name="documents",
        source="inventory:documents",
        result=result,
    )


@internal_router.post("/ledger", response_model=AiInternalLedgerResponse)
def read_internal_ledger(
    request: AiInternalLedgerRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalLedgerResponse:
    tool_call = service.authorize_internal_tool_call(
        session=session,
        service_token=service_token,
        expected_service_token=settings.AI_INTERNAL_SERVICE_TOKEN,
        actor_grant=actor_grant or "",
        grant_signing_key=settings.AI_ACTOR_GRANT_SIGNING_KEY or "",
        run_id=request.run_id,
        actor_user_id=request.actor_user_id,
        required_scope="inventory:ledger",
        tool_name="ledger",
        input_summary={"ledger_kind": request.ledger_kind.value},
    )
    result = inventory_service.list_ledger_entries(
        session=session,
        ledger_kind=request.ledger_kind,
        processing_unit_id=request.processing_unit_id,
        item_name=request.item_name,
        wool_content=request.wool_content,
        skip=request.skip,
        limit=request.limit,
        item_code=request.item_code,
        color_code=request.color_code,
        dye_lot_no=request.dye_lot_no,
    )
    service.complete_tool_call(
        session=session,
        tool_call=tool_call,
        actor_user_id=request.actor_user_id,
        source_summary={"source": "inventory:ledger", "count": result.count},
    )
    return AiInternalLedgerResponse(
        tool_name="ledger",
        source="inventory:ledger",
        result=result,
    )

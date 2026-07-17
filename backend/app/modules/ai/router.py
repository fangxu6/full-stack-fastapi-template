from typing import Annotated

from fastapi import APIRouter, Depends, Header

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
) -> AiInventoryQueryResponse:
    del query, current_user
    if not settings.AI_ENABLED:
        raise ServiceUnavailableError("AI inventory query is disabled")
    raise ServiceUnavailableError("AI inventory query is not configured")


@internal_router.post("/balances", response_model=AiInternalBalancesResponse)
def read_internal_balances(
    request: AiInternalBalancesRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalBalancesResponse:
    service.authorize_internal_tool_call(
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
    return AiInternalBalancesResponse(
        tool_name="balances",
        source="inventory:balances",
        result=inventory_service.list_balances(
            session=session,
            ledger_kind=InventoryLedgerKind(request.ledger_kind),
            skip=request.skip,
            limit=request.limit,
            processing_unit_id=request.processing_unit_id,
            item_name=request.item_name,
        ),
    )


@internal_router.post("/processing-units", response_model=AiInternalUnitsResponse)
def read_internal_processing_units(
    request: AiInternalUnitsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalUnitsResponse:
    service.authorize_internal_tool_call(
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
    return AiInternalUnitsResponse(
        tool_name="processing_units",
        source="inventory:processing_units",
        result=inventory_service.list_processing_units(
            session=session,
            name=request.name,
            is_active=request.is_active,
            skip=request.skip,
            limit=request.limit,
        ),
    )


@internal_router.post("/receiving-units", response_model=AiInternalUnitsResponse)
def read_internal_receiving_units(
    request: AiInternalUnitsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalUnitsResponse:
    service.authorize_internal_tool_call(
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
    return AiInternalUnitsResponse(
        tool_name="receiving_units",
        source="inventory:receiving_units",
        result=inventory_service.list_receiving_units(
            session=session,
            name=request.name,
            is_active=request.is_active,
            skip=request.skip,
            limit=request.limit,
        ),
    )


@internal_router.post("/documents", response_model=AiInternalDocumentsResponse)
def read_internal_documents(
    request: AiInternalDocumentsRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalDocumentsResponse:
    service.authorize_internal_tool_call(
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
    return AiInternalDocumentsResponse(
        tool_name="documents",
        source="inventory:documents",
        result=inventory_service.list_documents(
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
        ),
    )


@internal_router.post("/ledger", response_model=AiInternalLedgerResponse)
def read_internal_ledger(
    request: AiInternalLedgerRequest,
    session: SessionDep,
    service_token: Annotated[str | None, Header(alias="X-AI-Service-Token")] = None,
    actor_grant: Annotated[str | None, Header(alias="X-AI-Actor-Grant")] = None,
) -> AiInternalLedgerResponse:
    service.authorize_internal_tool_call(
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
    return AiInternalLedgerResponse(
        tool_name="ledger",
        source="inventory:ledger",
        result=inventory_service.list_ledger_entries(
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
        ),
    )

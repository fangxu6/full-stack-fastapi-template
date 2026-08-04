from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import AuditedWriteSessionDep, CurrentUser, SessionDep
from app.modules.iam.dependencies import permission_required
from app.modules.inventory import correction_service
from app.schemas.inventory_correction import (
    InventoryCorrectionRequestCreate,
    InventoryCorrectionRequestPublic,
    InventoryCorrectionRequestsPublic,
    InventoryCorrectionWorkItemPublic,
    InventoryCorrectionWorkItemsPublic,
)

router = APIRouter(prefix="/inventory", tags=["inventory corrections"])


@router.post(
    "/correction-requests",
    dependencies=[Depends(permission_required("inventory.corrections.request"))],
    response_model=InventoryCorrectionRequestPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_correction_request(
    request: Request,
    session: AuditedWriteSessionDep,
    current_user: CurrentUser,
    request_in: InventoryCorrectionRequestCreate,
) -> InventoryCorrectionRequestPublic:
    return correction_service.create_request(
        session=session,
        request_in=request_in,
        actor_user_id=current_user.id,
        audit_request_id=request.state.request_id,
    )


@router.get(
    "/correction-requests/mine",
    dependencies=[Depends(permission_required("inventory.corrections.request"))],
    response_model=InventoryCorrectionRequestsPublic,
)
def read_my_correction_requests(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> InventoryCorrectionRequestsPublic:
    return correction_service.list_mine(
        session=session,
        user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/correction-requests/review-queue",
    dependencies=[Depends(permission_required("inventory.corrections.review"))],
    response_model=InventoryCorrectionRequestsPublic,
)
def read_correction_review_queue(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> InventoryCorrectionRequestsPublic:
    del current_user
    return correction_service.list_review_queue(session=session, skip=skip, limit=limit)


@router.get(
    "/correction-requests/{correction_request_id}",
    response_model=InventoryCorrectionRequestPublic,
)
def read_correction_request(
    correction_request_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> InventoryCorrectionRequestPublic:
    return correction_service.get_request_detail(
        session=session,
        request_id=correction_request_id,
        user=current_user,
    )


@router.post(
    "/correction-requests/{correction_request_id}/approve",
    dependencies=[Depends(permission_required("inventory.corrections.review"))],
    response_model=InventoryCorrectionRequestPublic,
)
def approve_correction_request(
    correction_request_id: int,
    request: Request,
    session: AuditedWriteSessionDep,
    current_user: CurrentUser,
) -> InventoryCorrectionRequestPublic:
    return correction_service.approve_request(
        session=session,
        request_id=correction_request_id,
        reviewer_id=current_user.id,
        audit_request_id=request.state.request_id,
    )


@router.post(
    "/correction-requests/{correction_request_id}/reject",
    dependencies=[Depends(permission_required("inventory.corrections.review"))],
    response_model=InventoryCorrectionRequestPublic,
)
def reject_correction_request(
    correction_request_id: int,
    request: Request,
    session: AuditedWriteSessionDep,
    current_user: CurrentUser,
) -> InventoryCorrectionRequestPublic:
    return correction_service.reject_request(
        session=session,
        request_id=correction_request_id,
        reviewer_id=current_user.id,
        audit_request_id=request.state.request_id,
    )


@router.post(
    "/correction-requests/{correction_request_id}/withdraw",
    dependencies=[Depends(permission_required("inventory.corrections.request"))],
    response_model=InventoryCorrectionRequestPublic,
)
def withdraw_correction_request(
    correction_request_id: int,
    request: Request,
    session: AuditedWriteSessionDep,
    current_user: CurrentUser,
) -> InventoryCorrectionRequestPublic:
    return correction_service.withdraw_request(
        session=session,
        request_id=correction_request_id,
        actor_user_id=current_user.id,
        audit_request_id=request.state.request_id,
    )


@router.get(
    "/correction-work-items/recovery-queue",
    dependencies=[Depends(permission_required("inventory.corrections.recover"))],
    response_model=InventoryCorrectionWorkItemsPublic,
)
def read_correction_recovery_queue(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> InventoryCorrectionWorkItemsPublic:
    del current_user
    return correction_service.list_recovery_queue(
        session=session, skip=skip, limit=limit
    )


@router.post(
    "/correction-work-items/{work_item_id}/recover",
    dependencies=[Depends(permission_required("inventory.corrections.recover"))],
    response_model=InventoryCorrectionWorkItemPublic,
    status_code=status.HTTP_202_ACCEPTED,
)
def recover_correction_work_item(
    work_item_id: int,
    session: AuditedWriteSessionDep,
    current_user: CurrentUser,
) -> InventoryCorrectionWorkItemPublic:
    del current_user
    return correction_service.recover_work_item(
        session=session,
        work_item_id=work_item_id,
    )

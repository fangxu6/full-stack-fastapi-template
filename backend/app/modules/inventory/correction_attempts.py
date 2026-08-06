import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, col, select

from app.core.exceptions import BadRequestError, ConflictError
from app.models import (
    InventoryCorrectionAttempt,
    InventoryCorrectionRequest,
    InventoryCorrectionWorkItem,
    InventoryDocument,
)
from app.models.inventory import (
    InventoryCorrectionAttemptStatus,
    InventoryCorrectionFailureCategory,
    InventoryCorrectionOperation,
    InventoryCorrectionRequestStatus,
    InventoryCorrectionWorkItemStatus,
)
from app.modules.inventory import correction_workflow as workflow
from app.modules.inventory import documents
from app.schemas.inventory import InventoryDocumentCreate

MAX_PENDING_ATTEMPTS_PER_SCAN = 20


class CorrectionApplicationError(Exception):
    def __init__(self, category: InventoryCorrectionFailureCategory) -> None:
        self.category = category
        super().__init__(category.value)


def mark_expired_attempts_terminal(*, session: Session, now: datetime) -> int:
    work_items = list(
        session.exec(
            select(InventoryCorrectionWorkItem)
            .where(
                InventoryCorrectionWorkItem.status
                == InventoryCorrectionWorkItemStatus.RUNNING,
                col(InventoryCorrectionWorkItem.lease_expires_at).is_not(None),
                col(InventoryCorrectionWorkItem.lease_expires_at) <= now,
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    finalized = 0
    for work_item in work_items:
        if work_item.id is None or work_item.request_id is None:
            raise RuntimeError("Inventory correction work item must be persisted")
        attempt = session.exec(
            select(InventoryCorrectionAttempt)
            .where(
                InventoryCorrectionAttempt.work_item_id == work_item.id,
                InventoryCorrectionAttempt.sequence
                == work_item.current_attempt_sequence,
                InventoryCorrectionAttempt.status
                == InventoryCorrectionAttemptStatus.RUNNING,
            )
            .with_for_update()
        ).one_or_none()
        if attempt is None:
            continue
        request = workflow.require_request(
            session=session, request_id=work_item.request_id, lock=True
        )
        _set_terminal_failure(
            request=request,
            work_item=work_item,
            attempt=attempt,
            category=InventoryCorrectionFailureCategory.EXECUTION_LOST,
            now=now,
        )
        finalized += 1
    if finalized:
        session.flush()
    return finalized


def claim_pending_attempts(
    *,
    session: Session,
    scheduler_run_id: int,
    now: datetime,
    lease_duration: timedelta,
    limit: int = MAX_PENDING_ATTEMPTS_PER_SCAN,
) -> list[tuple[int, int]]:
    pending_attempts = list(
        session.exec(
            select(InventoryCorrectionAttempt)
            .where(
                InventoryCorrectionAttempt.status
                == InventoryCorrectionAttemptStatus.PENDING
            )
            .order_by(col(InventoryCorrectionAttempt.id))
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    claimed: list[tuple[int, int]] = []
    for attempt in pending_attempts:
        if attempt.id is None:
            raise RuntimeError("Inventory correction attempt must be persisted")
        work_item = workflow.require_work_item(
            session=session, work_item_id=attempt.work_item_id, lock=True
        )
        if (
            work_item.status
            is not InventoryCorrectionWorkItemStatus.APPROVED_PENDING_APPLY
            or work_item.current_attempt_sequence != attempt.sequence
        ):
            continue
        work_item.status = InventoryCorrectionWorkItemStatus.RUNNING
        work_item.lease_expires_at = now + lease_duration
        attempt.status = InventoryCorrectionAttemptStatus.RUNNING
        attempt.scheduler_run_id = scheduler_run_id
        attempt.started_at = now
        session.add(work_item)
        session.add(attempt)
        if work_item.id is None:
            raise RuntimeError("Inventory correction work item must be persisted")
        claimed.append((work_item.id, attempt.id))
    if claimed:
        session.flush()
    return claimed


def apply_claimed_attempt(
    *,
    session: Session,
    work_item_id: int,
    attempt_id: int,
    scheduler_run_id: int,
    actor_user_id: uuid.UUID,
    now: datetime,
) -> bool:
    work_item = workflow.require_work_item(
        session=session, work_item_id=work_item_id, lock=True
    )
    attempt = session.exec(
        select(InventoryCorrectionAttempt)
        .where(InventoryCorrectionAttempt.id == attempt_id)
        .with_for_update()
    ).one_or_none()
    if attempt is None or attempt.work_item_id != work_item_id:
        return False
    if (
        work_item.status is not InventoryCorrectionWorkItemStatus.RUNNING
        or attempt.status is not InventoryCorrectionAttemptStatus.RUNNING
        or attempt.scheduler_run_id != scheduler_run_id
    ):
        return False
    if work_item.request_id is None:
        raise CorrectionApplicationError(
            InventoryCorrectionFailureCategory.EXECUTION_FAILED
        )
    request = workflow.require_request(
        session=session, request_id=work_item.request_id, lock=True
    )
    document = session.exec(
        select(InventoryDocument)
        .where(InventoryDocument.id == work_item.document_id)
        .with_for_update()
    ).one_or_none()
    if document is None or document.is_legacy:
        raise CorrectionApplicationError(
            InventoryCorrectionFailureCategory.EXECUTION_FAILED
        )
    if (
        request.status is not InventoryCorrectionRequestStatus.APPROVED
        or request.proposal_hash != work_item.proposal_hash
        or workflow.normalize_timestamp(document.updated_at)
        != workflow.normalize_timestamp(work_item.expected_updated_at)
    ):
        raise CorrectionApplicationError(
            InventoryCorrectionFailureCategory.STALE_TARGET
        )
    document_in = None
    if request.operation is InventoryCorrectionOperation.UPDATE_DOCUMENT:
        try:
            document_in = InventoryDocumentCreate.model_validate(work_item.proposal)
        except ValueError as error:
            raise CorrectionApplicationError(
                InventoryCorrectionFailureCategory.EXECUTION_FAILED
            ) from error
    try:
        documents.apply_approved_correction(
            session=session,
            document=document,
            operation=request.operation,
            document_in=document_in,
        )
    except ConflictError as error:
        category = (
            InventoryCorrectionFailureCategory.NEGATIVE_BALANCE
            if error.detail == "Insufficient inventory"
            else InventoryCorrectionFailureCategory.EXECUTION_FAILED
        )
        raise CorrectionApplicationError(category) from error
    except BadRequestError as error:
        raise CorrectionApplicationError(
            InventoryCorrectionFailureCategory.EXECUTION_FAILED
        ) from error
    _set_application_succeeded(
        session=session,
        request=request,
        work_item=work_item,
        attempt=attempt,
        work_item_id=work_item_id,
        actor_user_id=actor_user_id,
        now=now,
    )
    session.flush()
    return True


def finalize_failed_attempt(
    *,
    session: Session,
    work_item_id: int,
    attempt_id: int,
    category: InventoryCorrectionFailureCategory,
    now: datetime,
) -> bool:
    work_item = workflow.require_work_item(
        session=session, work_item_id=work_item_id, lock=True
    )
    attempt = session.exec(
        select(InventoryCorrectionAttempt)
        .where(InventoryCorrectionAttempt.id == attempt_id)
        .with_for_update()
    ).one_or_none()
    if (
        attempt is None
        or attempt.work_item_id != work_item_id
        or work_item.status is not InventoryCorrectionWorkItemStatus.RUNNING
        or attempt.status is not InventoryCorrectionAttemptStatus.RUNNING
        or work_item.request_id is None
    ):
        return False
    request = workflow.require_request(
        session=session, request_id=work_item.request_id, lock=True
    )
    _set_terminal_failure(
        request=request,
        work_item=work_item,
        attempt=attempt,
        category=category,
        now=now,
    )
    session.flush()
    return True


def _set_terminal_failure(
    *,
    request: InventoryCorrectionRequest,
    work_item: InventoryCorrectionWorkItem,
    attempt: InventoryCorrectionAttempt,
    category: InventoryCorrectionFailureCategory,
    now: datetime,
) -> None:
    request.status = InventoryCorrectionRequestStatus.APPLICATION_FAILED
    work_item.status = InventoryCorrectionWorkItemStatus.TERMINAL_FAILED
    work_item.lease_expires_at = None
    work_item.terminal_failure_category = category
    attempt.status = InventoryCorrectionAttemptStatus.TERMINAL_FAILED
    attempt.finished_at = now
    attempt.failure_category = category


def _set_application_succeeded(
    *,
    session: Session,
    request: InventoryCorrectionRequest,
    work_item: InventoryCorrectionWorkItem,
    attempt: InventoryCorrectionAttempt,
    work_item_id: int,
    actor_user_id: uuid.UUID,
    now: datetime,
) -> None:
    request.status = InventoryCorrectionRequestStatus.APPLIED
    work_item.status = InventoryCorrectionWorkItemStatus.SUCCEEDED
    work_item.lease_expires_at = None
    work_item.terminal_failure_category = None
    attempt.status = InventoryCorrectionAttemptStatus.SUCCEEDED
    attempt.finished_at = now
    attempt.failure_category = None
    workflow.append_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        request_id=None,
        correction_request_id=request.id,
        action="inventory.correction.applied",
        changes={
            "operation": request.operation.value,
            "document_id": str(request.document_id),
            "proposal_hash": request.proposal_hash,
            "work_item_id": work_item_id,
            "attempt_sequence": attempt.sequence,
        },
    )

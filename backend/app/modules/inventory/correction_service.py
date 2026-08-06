import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import (
    InventoryCorrectionAttempt,
    InventoryCorrectionRequest,
    InventoryCorrectionWorkItem,
    InventoryDocument,
    User,
)
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryCorrectionAttemptOrigin,
    InventoryCorrectionAttemptStatus,
    InventoryCorrectionFailureCategory,
    InventoryCorrectionOperation,
    InventoryCorrectionRequestStatus,
    InventoryCorrectionWorkItemStatus,
)
from app.modules.audit import service as audit_service
from app.modules.iam import service as iam_service
from app.modules.inventory import documents
from app.schemas.inventory import InventoryDocumentCreate
from app.schemas.inventory_correction import (
    InventoryCorrectionAttemptPublic,
    InventoryCorrectionDocumentProposal,
    InventoryCorrectionRequestCreate,
    InventoryCorrectionRequestPublic,
    InventoryCorrectionRequestsPublic,
    InventoryCorrectionWorkItemPublic,
    InventoryCorrectionWorkItemsPublic,
)

ACTIVE_REQUEST_STATUSES = (
    InventoryCorrectionRequestStatus.PENDING_REVIEW,
    InventoryCorrectionRequestStatus.APPROVED,
)
CORRECTION_HANDLER_TYPE = "inventory.document_correction"
MAX_REASON_LENGTH = 500
MAX_PENDING_ATTEMPTS_PER_SCAN = 20


class CorrectionApplicationError(Exception):
    def __init__(self, category: InventoryCorrectionFailureCategory) -> None:
        self.category = category
        super().__init__(category.value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("correction timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _request_hash(
    *,
    document_id: uuid.UUID,
    operation: InventoryCorrectionOperation,
    expected_updated_at: datetime,
    proposal: InventoryCorrectionDocumentProposal | None,
    reason: str,
) -> tuple[dict[str, object] | None, str]:
    normalized_proposal = (
        cast(dict[str, object], proposal.model_dump(mode="json"))
        if proposal is not None
        else None
    )
    hash_input: dict[str, object] = {
        "document_id": str(document_id),
        "operation": operation.value,
        "expected_updated_at": _utc(expected_updated_at).isoformat(),
        "proposal": normalized_proposal,
        "reason": reason.strip(),
    }
    encoded = json.dumps(
        hash_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return normalized_proposal, hashlib.sha256(encoded).hexdigest()


def _request_by_id(
    *, session: Session, request_id: int, lock: bool = False
) -> InventoryCorrectionRequest:
    statement = select(InventoryCorrectionRequest).where(
        InventoryCorrectionRequest.id == request_id
    )
    if lock:
        statement = statement.with_for_update()
    request = session.exec(statement).one_or_none()
    if request is None:
        raise NotFoundError("Inventory correction request not found")
    return request


def _work_item_by_id(
    *, session: Session, work_item_id: int, lock: bool = False
) -> InventoryCorrectionWorkItem:
    statement = select(InventoryCorrectionWorkItem).where(
        InventoryCorrectionWorkItem.id == work_item_id
    )
    if lock:
        statement = statement.with_for_update()
    work_item = session.exec(statement).one_or_none()
    if work_item is None:
        raise NotFoundError("Inventory correction work item not found")
    return work_item


def _active_request_for_document(
    *, session: Session, document_id: uuid.UUID, exclude_request_id: int | None = None
) -> InventoryCorrectionRequest | None:
    statement = select(InventoryCorrectionRequest).where(
        InventoryCorrectionRequest.document_id == document_id,
        col(InventoryCorrectionRequest.status).in_(ACTIVE_REQUEST_STATUSES),
    )
    if exclude_request_id is not None:
        statement = statement.where(InventoryCorrectionRequest.id != exclude_request_id)
    return session.exec(statement).first()


def _require_correction_target(
    *, session: Session, document_id: uuid.UUID, lock: bool = False
) -> InventoryDocument:
    statement = select(InventoryDocument).where(InventoryDocument.id == document_id)
    if lock:
        statement = statement.with_for_update()
    document = session.exec(statement).one_or_none()
    if document is None:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be corrected")
    if not documents.document_has_ledger_effects(
        session=session, document_id=document_id
    ):
        raise ConflictError("INVENTORY_CORRECTION_NOT_REQUIRED")
    return document


def _validate_operation_target(
    *,
    document: InventoryDocument,
    operation: InventoryCorrectionOperation,
    proposal: InventoryCorrectionDocumentProposal | None,
) -> None:
    if operation is InventoryCorrectionOperation.UPDATE_DOCUMENT:
        if proposal is None:
            raise BadRequestError("UPDATE_DOCUMENT requires a proposal")
        if proposal.document_type != document.document_type:
            raise BadRequestError("Document type cannot be changed")
        if document.deleted_at is not None:
            raise BadRequestError("Deleted inventory documents must be restored first")
        return
    if proposal is not None:
        raise BadRequestError("Only UPDATE_DOCUMENT accepts a proposal")
    if operation is InventoryCorrectionOperation.DELETE_DOCUMENT:
        if document.deleted_at is not None:
            raise BadRequestError("Inventory document is already deleted")
        return
    if operation is InventoryCorrectionOperation.RESTORE_DOCUMENT:
        if document.deleted_at is None:
            raise BadRequestError("Inventory document is not deleted")
        return
    raise BadRequestError("Unsupported inventory correction operation")


def _append_audit_event(
    *,
    session: Session,
    actor_user_id: uuid.UUID,
    request_id: str | None,
    correction_request_id: int | None,
    action: str,
    changes: dict[str, object],
) -> None:
    allowed = {
        "inventory.correction.created": frozenset(
            {"operation", "document_id", "proposal_hash"}
        ),
        "inventory.correction.approved": frozenset(
            {
                "operation",
                "document_id",
                "proposal_hash",
                "work_item_id",
                "attempt_sequence",
            }
        ),
        "inventory.correction.rejected": frozenset(
            {"operation", "document_id", "proposal_hash"}
        ),
        "inventory.correction.withdrawn": frozenset(
            {"operation", "document_id", "proposal_hash"}
        ),
        "inventory.correction.applied": frozenset(
            {
                "operation",
                "document_id",
                "proposal_hash",
                "work_item_id",
                "attempt_sequence",
            }
        ),
    }
    if action not in allowed or set(changes) != allowed[action]:
        raise ValueError("Inventory correction audit event does not match its contract")
    if correction_request_id is None:
        raise RuntimeError("Inventory correction request must be persisted")
    audit_service.append_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        request_id=request_id,
        action=action,
        resource_type="inventory_correction_request",
        resource_id=str(correction_request_id),
        changes=changes,
    )


def create_request(
    *,
    session: Session,
    request_in: InventoryCorrectionRequestCreate,
    actor_user_id: uuid.UUID,
    audit_request_id: str | None,
) -> InventoryCorrectionRequestPublic:
    document = _require_correction_target(
        session=session, document_id=request_in.document_id, lock=True
    )
    expected_updated_at = _utc(request_in.expected_updated_at)
    if _utc(document.updated_at) != expected_updated_at:
        raise ConflictError("INVENTORY_CORRECTION_TARGET_CHANGED")
    _validate_operation_target(
        document=document,
        operation=request_in.operation,
        proposal=request_in.proposal,
    )
    reason = request_in.reason.strip()
    if not reason or len(reason) > MAX_REASON_LENGTH:
        raise BadRequestError(
            "Correction reason must be nonblank and at most 500 characters"
        )
    proposal, proposal_hash = _request_hash(
        document_id=request_in.document_id,
        operation=request_in.operation,
        expected_updated_at=expected_updated_at,
        proposal=request_in.proposal,
        reason=reason,
    )
    correction_request = InventoryCorrectionRequest(
        document_id=request_in.document_id,
        operation=request_in.operation,
        expected_updated_at=expected_updated_at,
        proposal=proposal,
        proposal_hash=proposal_hash,
        reason=reason,
    )
    try:
        with session.begin_nested():
            session.add(correction_request)
            session.flush()
    except IntegrityError as error:
        raise ConflictError("INVENTORY_CORRECTION_ACTIVE_REQUEST") from error
    _append_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        request_id=audit_request_id,
        correction_request_id=correction_request.id,
        action="inventory.correction.created",
        changes={
            "operation": request_in.operation.value,
            "document_id": str(request_in.document_id),
            "proposal_hash": proposal_hash,
        },
    )
    return _request_public(session=session, request=correction_request)


def _request_public(
    *,
    session: Session,
    request: InventoryCorrectionRequest,
    include_work_item: bool = False,
) -> InventoryCorrectionRequestPublic:
    if request.id is None:
        raise RuntimeError("Inventory correction request must be persisted")
    work_item_public: InventoryCorrectionWorkItemPublic | None = None
    if include_work_item:
        work_item = session.exec(
            select(InventoryCorrectionWorkItem).where(
                InventoryCorrectionWorkItem.request_id == request.id
            )
        ).one_or_none()
        if work_item is not None:
            work_item_public = _work_item_public(
                session=session, work_item=work_item, include_attempts=True
            )
    return InventoryCorrectionRequestPublic(
        id=request.id,
        document_id=request.document_id,
        operation=request.operation,
        expected_updated_at=request.expected_updated_at,
        proposal=request.proposal,
        proposal_hash=request.proposal_hash,
        reason=request.reason,
        status=request.status,
        reviewer_id=request.reviewer_id,
        decided_at=request.decided_at,
        work_item=work_item_public,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


def _attempt_public(
    attempt: InventoryCorrectionAttempt,
) -> InventoryCorrectionAttemptPublic:
    if attempt.id is None:
        raise RuntimeError("Inventory correction attempt must be persisted")
    return InventoryCorrectionAttemptPublic(
        id=attempt.id,
        sequence=attempt.sequence,
        origin=attempt.origin,
        status=attempt.status,
        scheduler_run_id=attempt.scheduler_run_id,
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        failure_category=attempt.failure_category,
    )


def _work_item_public(
    *,
    session: Session,
    work_item: InventoryCorrectionWorkItem,
    include_attempts: bool,
) -> InventoryCorrectionWorkItemPublic:
    if work_item.id is None or work_item.request_id is None:
        raise RuntimeError("Inventory correction work item must be persisted")
    attempts = []
    if include_attempts:
        attempts = [
            _attempt_public(attempt)
            for attempt in session.exec(
                select(InventoryCorrectionAttempt)
                .where(InventoryCorrectionAttempt.work_item_id == work_item.id)
                .order_by(col(InventoryCorrectionAttempt.sequence))
            ).all()
        ]
    return InventoryCorrectionWorkItemPublic(
        id=work_item.id,
        request_id=work_item.request_id,
        document_id=work_item.document_id,
        expected_updated_at=work_item.expected_updated_at,
        proposal_hash=work_item.proposal_hash,
        handler_type=work_item.handler_type,
        status=work_item.status,
        current_attempt_sequence=work_item.current_attempt_sequence,
        terminal_failure_category=work_item.terminal_failure_category,
        attempts=attempts,
        created_at=work_item.created_at,
        updated_at=work_item.updated_at,
    )


def _permission_set(*, session: Session, user: User) -> set[str]:
    return set(
        iam_service.get_effective_permissions(
            session=session, user_id=user.id
        ).permissions
    )


def _can(*, permissions: set[str], permission: str) -> bool:
    return permission in permissions


def list_mine(
    *,
    session: Session,
    user: User,
    skip: int,
    limit: int,
) -> InventoryCorrectionRequestsPublic:
    predicate = InventoryCorrectionRequest.created_by == user.id
    count = session.exec(
        select(func.count()).select_from(InventoryCorrectionRequest).where(predicate)
    ).one()
    requests = list(
        session.exec(
            select(InventoryCorrectionRequest)
            .where(predicate)
            .order_by(
                col(InventoryCorrectionRequest.created_at).desc(),
                col(InventoryCorrectionRequest.id).desc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return InventoryCorrectionRequestsPublic(
        data=[_request_public(session=session, request=item) for item in requests],
        count=count,
    )


def list_review_queue(
    *, session: Session, skip: int, limit: int
) -> InventoryCorrectionRequestsPublic:
    predicate = (
        InventoryCorrectionRequest.status
        == InventoryCorrectionRequestStatus.PENDING_REVIEW
    )
    count = session.exec(
        select(func.count()).select_from(InventoryCorrectionRequest).where(predicate)
    ).one()
    requests = list(
        session.exec(
            select(InventoryCorrectionRequest)
            .where(predicate)
            .order_by(
                col(InventoryCorrectionRequest.created_at).desc(),
                col(InventoryCorrectionRequest.id).desc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return InventoryCorrectionRequestsPublic(
        data=[_request_public(session=session, request=item) for item in requests],
        count=count,
    )


def list_recovery_queue(
    *, session: Session, skip: int, limit: int
) -> InventoryCorrectionWorkItemsPublic:
    predicate = (
        InventoryCorrectionWorkItem.status
        == InventoryCorrectionWorkItemStatus.TERMINAL_FAILED
    )
    count = session.exec(
        select(func.count()).select_from(InventoryCorrectionWorkItem).where(predicate)
    ).one()
    work_items = list(
        session.exec(
            select(InventoryCorrectionWorkItem)
            .where(predicate)
            .order_by(
                col(InventoryCorrectionWorkItem.created_at).desc(),
                col(InventoryCorrectionWorkItem.id).desc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return InventoryCorrectionWorkItemsPublic(
        data=[
            _work_item_public(session=session, work_item=item, include_attempts=False)
            for item in work_items
        ],
        count=count,
    )


def get_request_detail(
    *, session: Session, request_id: int, user: User
) -> InventoryCorrectionRequestPublic:
    request = _request_by_id(session=session, request_id=request_id)
    permissions = _permission_set(session=session, user=user)
    owns_request = request.created_by == user.id and _can(
        permissions=permissions, permission="inventory.corrections.request"
    )
    can_review = (
        request.status is InventoryCorrectionRequestStatus.PENDING_REVIEW
        and _can(permissions=permissions, permission="inventory.corrections.review")
    )
    work_item = session.exec(
        select(InventoryCorrectionWorkItem).where(
            InventoryCorrectionWorkItem.request_id == request.id
        )
    ).one_or_none()
    can_recover = (
        work_item is not None
        and work_item.status is InventoryCorrectionWorkItemStatus.TERMINAL_FAILED
        and _can(permissions=permissions, permission="inventory.corrections.recover")
    )
    if not owns_request and not can_review and not can_recover:
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError("The user cannot view this correction request")
    return _request_public(session=session, request=request, include_work_item=True)


def approve_request(
    *,
    session: Session,
    request_id: int,
    reviewer_id: uuid.UUID,
    audit_request_id: str | None,
) -> InventoryCorrectionRequestPublic:
    request = _request_by_id(session=session, request_id=request_id, lock=True)
    if request.status is not InventoryCorrectionRequestStatus.PENDING_REVIEW:
        raise ConflictError("Inventory correction request is not pending review")
    document = _require_correction_target(
        session=session, document_id=request.document_id, lock=True
    )
    now = get_datetime_utc()
    if _utc(document.updated_at) != _utc(request.expected_updated_at):
        request.status = InventoryCorrectionRequestStatus.STALE
        request.reviewer_id = reviewer_id
        request.decided_at = now
        session.add(request)
        session.flush()
        return _request_public(session=session, request=request)
    existing_work_item = session.exec(
        select(InventoryCorrectionWorkItem).where(
            InventoryCorrectionWorkItem.request_id == request.id
        )
    ).one_or_none()
    if existing_work_item is not None:
        raise ConflictError("Inventory correction work item already exists")
    if request.id is None:
        raise RuntimeError("Inventory correction request must be persisted")
    work_item = InventoryCorrectionWorkItem(
        request_id=request.id,
        document_id=request.document_id,
        expected_updated_at=request.expected_updated_at,
        proposal=request.proposal,
        proposal_hash=request.proposal_hash,
        handler_type=CORRECTION_HANDLER_TYPE,
        status=InventoryCorrectionWorkItemStatus.APPROVED_PENDING_APPLY,
        current_attempt_sequence=1,
    )
    attempt = InventoryCorrectionAttempt(
        work_item_id=0,
        sequence=1,
        origin=InventoryCorrectionAttemptOrigin.INITIAL,
        status=InventoryCorrectionAttemptStatus.PENDING,
    )
    request.status = InventoryCorrectionRequestStatus.APPROVED
    request.reviewer_id = reviewer_id
    request.decided_at = now
    session.add(request)
    session.add(work_item)
    session.flush()
    if work_item.id is None:
        raise RuntimeError(
            "Inventory correction work item did not receive an identifier"
        )
    attempt.work_item_id = work_item.id
    session.add(attempt)
    session.flush()
    _append_audit_event(
        session=session,
        actor_user_id=reviewer_id,
        request_id=audit_request_id,
        correction_request_id=request.id,
        action="inventory.correction.approved",
        changes={
            "operation": request.operation.value,
            "document_id": str(request.document_id),
            "proposal_hash": request.proposal_hash,
            "work_item_id": work_item.id,
            "attempt_sequence": 1,
        },
    )
    return _request_public(session=session, request=request, include_work_item=True)


def reject_request(
    *,
    session: Session,
    request_id: int,
    reviewer_id: uuid.UUID,
    audit_request_id: str | None,
) -> InventoryCorrectionRequestPublic:
    request = _request_by_id(session=session, request_id=request_id, lock=True)
    if request.status is not InventoryCorrectionRequestStatus.PENDING_REVIEW:
        raise ConflictError("Inventory correction request is not pending review")
    request.status = InventoryCorrectionRequestStatus.REJECTED
    request.reviewer_id = reviewer_id
    request.decided_at = get_datetime_utc()
    session.add(request)
    session.flush()
    _append_audit_event(
        session=session,
        actor_user_id=reviewer_id,
        request_id=audit_request_id,
        correction_request_id=request.id,
        action="inventory.correction.rejected",
        changes={
            "operation": request.operation.value,
            "document_id": str(request.document_id),
            "proposal_hash": request.proposal_hash,
        },
    )
    return _request_public(session=session, request=request)


def withdraw_request(
    *,
    session: Session,
    request_id: int,
    actor_user_id: uuid.UUID,
    audit_request_id: str | None,
) -> InventoryCorrectionRequestPublic:
    request = _request_by_id(session=session, request_id=request_id, lock=True)
    if request.created_by != actor_user_id:
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError("Only the request creator can withdraw it")
    if request.status is not InventoryCorrectionRequestStatus.PENDING_REVIEW:
        raise ConflictError("Only pending correction requests can be withdrawn")
    request.status = InventoryCorrectionRequestStatus.WITHDRAWN
    request.decided_at = get_datetime_utc()
    session.add(request)
    session.flush()
    _append_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        request_id=audit_request_id,
        correction_request_id=request.id,
        action="inventory.correction.withdrawn",
        changes={
            "operation": request.operation.value,
            "document_id": str(request.document_id),
            "proposal_hash": request.proposal_hash,
        },
    )
    return _request_public(session=session, request=request)


def recover_work_item(
    *,
    session: Session,
    work_item_id: int,
) -> InventoryCorrectionWorkItemPublic:
    work_item = _work_item_by_id(session=session, work_item_id=work_item_id, lock=True)
    if work_item.status is not InventoryCorrectionWorkItemStatus.TERMINAL_FAILED:
        raise ConflictError("Only terminal correction work items can be recovered")
    if work_item.request_id is None:
        raise RuntimeError("Correction work item request is missing")
    request = _request_by_id(
        session=session, request_id=work_item.request_id, lock=True
    )
    document = _require_correction_target(
        session=session, document_id=work_item.document_id, lock=True
    )
    if _utc(document.updated_at) != _utc(work_item.expected_updated_at):
        raise ConflictError("INVENTORY_CORRECTION_TARGET_CHANGED")
    if work_item.proposal_hash != request.proposal_hash:
        raise ConflictError("INVENTORY_CORRECTION_PROPOSAL_CHANGED")
    if (
        _active_request_for_document(
            session=session,
            document_id=work_item.document_id,
            exclude_request_id=request.id,
        )
        is not None
    ):
        raise ConflictError("INVENTORY_CORRECTION_ACTIVE_REQUEST")
    next_sequence = work_item.current_attempt_sequence + 1
    request.status = InventoryCorrectionRequestStatus.APPROVED
    work_item.status = InventoryCorrectionWorkItemStatus.APPROVED_PENDING_APPLY
    work_item.current_attempt_sequence = next_sequence
    work_item.lease_expires_at = None
    work_item.terminal_failure_category = None
    session.add(request)
    session.add(work_item)
    session.flush()
    if work_item.id is None:
        raise RuntimeError("Inventory correction work item must be persisted")
    attempt = InventoryCorrectionAttempt(
        work_item_id=work_item.id,
        sequence=next_sequence,
        origin=InventoryCorrectionAttemptOrigin.RECOVERY,
        status=InventoryCorrectionAttemptStatus.PENDING,
    )
    session.add(attempt)
    session.flush()
    return _work_item_public(
        session=session, work_item=work_item, include_attempts=True
    )


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
        request = _request_by_id(
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
        work_item = _work_item_by_id(
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
    work_item = _work_item_by_id(session=session, work_item_id=work_item_id, lock=True)
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
    request = _request_by_id(
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
        or _utc(document.updated_at) != _utc(work_item.expected_updated_at)
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
    work_item = _work_item_by_id(session=session, work_item_id=work_item_id, lock=True)
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
    request = _request_by_id(
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
    _append_audit_event(
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

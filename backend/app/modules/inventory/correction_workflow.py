import uuid
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.exceptions import NotFoundError
from app.models import (
    InventoryCorrectionRequest,
    InventoryCorrectionWorkItem,
)
from app.modules.audit import service as audit_service


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("correction timestamps must be timezone-aware")
    return value.astimezone(UTC)


def require_request(
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


def require_work_item(
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


def append_audit_event(
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

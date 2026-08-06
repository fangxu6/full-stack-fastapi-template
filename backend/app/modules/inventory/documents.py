# SQLModel's type surface exposes ORM columns as their value types. Query
# expressions below are SQLAlchemy descriptors at runtime, which mypy cannot
# represent without a plugin; preserve checking for all other error families.
# mypy: disable-error-code="arg-type,attr-defined,call-overload,return-value,union-attr"

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import InventoryDocument, InventoryDocumentLine, InventoryLedgerEntry
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryCorrectionOperation,
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
)
from app.modules.inventory.units import require_active_units
from app.schemas.inventory import (
    InventoryDocumentCreate,
    InventoryDocumentPublic,
    InventoryLinePublic,
)

LEGACY_PLACEHOLDERS = {"未填写品号", "未填写含毛量", "未分缸"}


def _movement(
    document_type: InventoryDocumentType,
) -> tuple[InventoryLedgerKind, InventoryMovementType, Decimal]:
    mapping = {
        InventoryDocumentType.RAW_RECEIPT: (
            InventoryLedgerKind.RAW,
            InventoryMovementType.RAW_RECEIPT,
            Decimal("1"),
        ),
        InventoryDocumentType.RAW_RETURN: (
            InventoryLedgerKind.RAW,
            InventoryMovementType.RAW_RETURN,
            Decimal("-1"),
        ),
        InventoryDocumentType.FINISHED_SHIPMENT: (
            InventoryLedgerKind.FINISHED,
            InventoryMovementType.FINISHED_SHIPMENT,
            Decimal("-1"),
        ),
    }
    try:
        return mapping[document_type]
    except KeyError as err:
        raise BadRequestError("This document type cannot be created manually") from err


def _validate_line_for_type(document_type: InventoryDocumentType, line: object) -> None:
    values = (line.item_code, line.wool_content, line.color_code, line.dye_lot_no)  # ty:ignore[unresolved-attribute]
    if any(value in LEGACY_PLACEHOLDERS for value in values):
        raise BadRequestError(
            "Legacy placeholder values cannot be used in new documents"
        )
    if document_type in {
        InventoryDocumentType.RAW_RECEIPT,
        InventoryDocumentType.RAW_RETURN,
    }:
        if (
            not line.item_code  # ty:ignore[unresolved-attribute]
            or line.color_code  # ty:ignore[unresolved-attribute]
            or line.dye_lot_no  # ty:ignore[unresolved-attribute]
            or line.quantity_meters is not None  # ty:ignore[unresolved-attribute]
        ):
            raise BadRequestError(
                "Raw inventory lines require item code and rolls only"
            )
    elif not line.color_code or not line.dye_lot_no or line.quantity_meters is None:  # ty:ignore[unresolved-attribute]
        raise BadRequestError(
            "Finished shipment lines require color, lot, rolls, and meters"
        )


def _add_lines_and_ledgers(
    *,
    session: Session,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
) -> None:
    ledger_kind, movement_type, direction = _movement(document_in.document_type)
    for line_no, line_in in enumerate(document_in.lines, start=1):
        _validate_line_for_type(document_in.document_type, line_in)
        line = InventoryDocumentLine(
            document_id=document.id,
            line_no=line_no,
            **line_in.model_dump(),
        )
        session.add(line)
        session.flush()
        session.add(
            InventoryLedgerEntry(
                ledger_kind=ledger_kind,
                movement_type=movement_type,
                business_date=document.business_date,
                processing_unit_id=document.processing_unit_id,
                document_line_id=line.id,
                item_name=line.item_name,
                item_code=line.item_code,
                wool_content=line.wool_content,
                color_code=line.color_code,
                dye_lot_no=line.dye_lot_no,
                rolls_delta=direction * line.quantity_rolls,
                meters_delta=direction * (line.quantity_meters or Decimal("0")),
            )
        )


def _apply_document_values(
    *,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
) -> None:
    number = document_in.document_number.strip()
    if not number:
        raise BadRequestError("Document number cannot be blank")
    document.business_date = document_in.business_date
    document.processing_unit_id = document_in.processing_unit_id
    document.receiving_unit_id = document_in.receiving_unit_id
    document.document_number = number
    document.remarks = document_in.remarks


def create_document(
    *, session: Session, document_in: InventoryDocumentCreate
) -> InventoryDocumentPublic:
    try:
        require_active_units(session=session, document_in=document_in)
        _movement(document_in.document_type)
        document = InventoryDocument(
            document_type=document_in.document_type,
            business_date=document_in.business_date,
            processing_unit_id=document_in.processing_unit_id,
            receiving_unit_id=document_in.receiving_unit_id,
            document_number=document_in.document_number.strip(),
            remarks=document_in.remarks,
        )
        session.add(document)
        session.flush()
        _add_lines_and_ledgers(
            session=session,
            document=document,
            document_in=document_in,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.flush()
    except BadRequestError, ConflictError:
        raise
    except IntegrityError as err:
        raise ConflictError("Document number already exists") from err
    return document_public(session=session, document=document)


def update_document(
    *,
    session: Session,
    document_id: uuid.UUID,
    document_in: InventoryDocumentCreate,
) -> InventoryDocumentPublic:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be edited")
    _ensure_direct_write_allowed(session=session, document=document)
    if document.deleted_at:
        raise BadRequestError("Deleted inventory documents must be restored first")
    return _update_document_impl(
        session=session,
        document=document,
        document_in=document_in,
    )


def _update_document_impl(
    *,
    session: Session,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
) -> InventoryDocumentPublic:
    if document.document_type != document_in.document_type:
        raise BadRequestError("Document type cannot be changed")
    original_processing_unit_id = document.processing_unit_id
    try:
        require_active_units(session=session, document_in=document_in)
        _replace_document_lines(session=session, document=document)
        _apply_document_values(document=document, document_in=document_in)
        session.add(document)
        _add_lines_and_ledgers(
            session=session,
            document=document,
            document_in=document_in,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=original_processing_unit_id
        )
        if document.processing_unit_id != original_processing_unit_id:
            _reject_negative_balances(
                session=session, processing_unit_id=document.processing_unit_id
            )
        session.flush()
    except BadRequestError, ConflictError:
        raise
    except IntegrityError as err:
        raise ConflictError("Document number already exists") from err
    return document_public(session=session, document=document)


def delete_document(*, session: Session, document_id: uuid.UUID) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be deleted")
    _ensure_direct_write_allowed(session=session, document=document)
    if document.deleted_at:
        return
    _delete_document_impl(session=session, document=document)


def _delete_document_impl(*, session: Session, document: InventoryDocument) -> None:
    now = get_datetime_utc()
    document.deleted_at = now
    session.add(document)
    _set_document_ledger_deleted(session=session, document=document, deleted_at=now)
    session.flush()


def restore_document(*, session: Session, document_id: uuid.UUID) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be restored")
    _ensure_direct_write_allowed(session=session, document=document)
    _restore_document_impl(session=session, document=document)


def _restore_document_impl(*, session: Session, document: InventoryDocument) -> None:
    try:
        document.deleted_at = None
        _set_document_ledger_deleted(
            session=session,
            document=document,
            deleted_at=None,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.add(document)
        session.flush()
    except ConflictError:
        raise


def apply_approved_correction(
    *,
    session: Session,
    document: InventoryDocument,
    operation: InventoryCorrectionOperation,
    document_in: InventoryDocumentCreate | None,
) -> InventoryDocumentPublic | None:
    if operation is InventoryCorrectionOperation.UPDATE_DOCUMENT:
        if document_in is None:
            raise BadRequestError("UPDATE_DOCUMENT requires a proposal")
        return _update_document_impl(
            session=session,
            document=document,
            document_in=document_in,
        )
    if document_in is not None:
        raise BadRequestError("Only UPDATE_DOCUMENT accepts a proposal")
    if operation is InventoryCorrectionOperation.DELETE_DOCUMENT:
        _delete_document_impl(session=session, document=document)
        return None
    if operation is InventoryCorrectionOperation.RESTORE_DOCUMENT:
        _restore_document_impl(session=session, document=document)
        return None
    raise BadRequestError("Unsupported inventory correction operation")


def document_has_ledger_effects(*, session: Session, document_id: uuid.UUID) -> bool:
    statement = (
        select(InventoryLedgerEntry.id)
        .join(
            InventoryDocumentLine,
            InventoryDocumentLine.id == InventoryLedgerEntry.document_line_id,  # ty:ignore[invalid-argument-type]
        )
        .where(InventoryDocumentLine.document_id == document_id)
        .limit(1)
    )
    return session.exec(statement).first() is not None


def _ensure_direct_write_allowed(
    *, session: Session, document: InventoryDocument
) -> None:
    if document_has_ledger_effects(session=session, document_id=document.id):
        raise ConflictError("INVENTORY_CORRECTION_REQUIRED")


def _replace_document_lines(*, session: Session, document: InventoryDocument) -> None:
    lines = list(
        session.exec(
            select(InventoryDocumentLine).where(
                InventoryDocumentLine.document_id == document.id,
            )
        ).all()
    )
    if not lines:
        return
    line_ids = [line.id for line in lines]
    ledgers = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id.in_(line_ids)  # ty:ignore[unresolved-attribute]
        )
    ).all()
    for ledger in ledgers:
        session.delete(ledger)
    session.flush()
    for line in lines:
        session.delete(line)
    session.flush()


def _set_document_ledger_deleted(
    *,
    session: Session,
    document: InventoryDocument,
    deleted_at: datetime | None,
) -> None:
    line_ids = session.exec(
        select(InventoryDocumentLine.id).where(
            InventoryDocumentLine.document_id == document.id
        )
    ).all()
    if not line_ids:
        return
    ledgers = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id.in_(line_ids)  # ty:ignore[unresolved-attribute]
        )
    ).all()
    for ledger in ledgers:
        ledger.deleted_at = deleted_at
        session.add(ledger)


def document_public(
    *, session: Session, document: InventoryDocument
) -> InventoryDocumentPublic:
    lines = list(
        session.exec(
            select(InventoryDocumentLine)
            .where(
                InventoryDocumentLine.document_id == document.id,
                InventoryDocumentLine.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
            )
            .order_by(InventoryDocumentLine.line_no)  # ty:ignore[invalid-argument-type]
        ).all()
    )
    return InventoryDocumentPublic(
        id=document.id,
        document_type=document.document_type,
        business_date=document.business_date,
        processing_unit_id=document.processing_unit_id,
        receiving_unit_id=document.receiving_unit_id,
        document_number=document.document_number,
        remarks=document.remarks,
        updated_at=document.updated_at,
        deleted_at=document.deleted_at,
        lines=[
            InventoryLinePublic(
                id=line.id,
                line_no=line.line_no,
                item_name=line.item_name,
                item_code=line.item_code,
                wool_content=line.wool_content,
                color_code=line.color_code,
                dye_lot_no=line.dye_lot_no,
                quantity_rolls=line.quantity_rolls,
                quantity_meters=line.quantity_meters,
            )
            for line in lines
        ],
    )


def _reject_negative_balances(
    *, session: Session, processing_unit_id: uuid.UUID
) -> None:
    entries = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.processing_unit_id == processing_unit_id,
            InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
        )
    ).all()
    balances: dict[tuple[object, ...], tuple[Decimal, Decimal]] = {}
    for entry in entries:
        key = (
            entry.ledger_kind,
            entry.item_name,
            entry.item_code,
            entry.wool_content,
            entry.color_code,
            entry.dye_lot_no,
        )
        rolls, meters = balances.get(key, (Decimal("0"), Decimal("0")))
        balances[key] = (rolls + entry.rolls_delta, meters + entry.meters_delta)
    if any(rolls < 0 or meters < 0 for rolls, meters in balances.values()):
        raise ConflictError("Insufficient inventory")

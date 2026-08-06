# SQLModel's type surface exposes ORM columns as their value types, while
# runtime queries use SQLAlchemy descriptors.
# mypy: disable-error-code="arg-type,attr-defined,call-overload,return-value,union-attr"

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError
from app.models import InventoryLedgerEntry
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
)


@dataclass(frozen=True)
class LedgerBalanceKey:
    ledger_kind: InventoryLedgerKind
    processing_unit_id: uuid.UUID
    item_name: str
    item_code: str | None
    wool_content: str
    color_code: str | None
    dye_lot_no: str | None


@dataclass(frozen=True)
class LedgerMovement:
    ledger_kind: InventoryLedgerKind
    movement_type: InventoryMovementType
    business_date: date
    processing_unit_id: uuid.UUID
    item_name: str
    item_code: str | None
    wool_content: str
    color_code: str | None
    dye_lot_no: str | None
    rolls_delta: Decimal
    meters_delta: Decimal
    document_line_id: uuid.UUID | None = None
    legacy_import_row_id: uuid.UUID | None = None
    import_batch_id: uuid.UUID | None = None
    reason: str | None = None


LedgerBalances = dict[LedgerBalanceKey, tuple[Decimal, Decimal]]


def movement_for_document_type(
    document_type: InventoryDocumentType,
    *,
    allow_finished_receipt: bool = False,
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
        InventoryDocumentType.FINISHED_RECEIPT: (
            InventoryLedgerKind.FINISHED,
            InventoryMovementType.FINISHED_RECEIPT,
            Decimal("1"),
        ),
    }
    if (
        document_type is InventoryDocumentType.FINISHED_RECEIPT
        and not allow_finished_receipt
    ):
        raise BadRequestError("This document type cannot be created manually")
    try:
        return mapping[document_type]
    except KeyError as error:
        raise BadRequestError(
            "This document type cannot be created manually"
        ) from error


def append_movement(
    *, session: Session, movement: LedgerMovement
) -> InventoryLedgerEntry:
    if movement.movement_type is InventoryMovementType.MIGRATION_RECONCILIATION_OPENING:
        if movement.document_line_id is not None or movement.import_batch_id is None:
            raise ValueError("Ledger opening movement must belong to an import batch")
    elif movement.document_line_id is None:
        raise ValueError("Ledger movement must belong to a document line")

    entry = InventoryLedgerEntry(
        ledger_kind=movement.ledger_kind,
        movement_type=movement.movement_type,
        business_date=movement.business_date,
        processing_unit_id=movement.processing_unit_id,
        document_line_id=movement.document_line_id,
        legacy_import_row_id=movement.legacy_import_row_id,
        import_batch_id=movement.import_batch_id,
        item_name=movement.item_name,
        item_code=movement.item_code,
        wool_content=movement.wool_content,
        color_code=movement.color_code,
        dye_lot_no=movement.dye_lot_no,
        rolls_delta=movement.rolls_delta,
        meters_delta=movement.meters_delta,
        reason=movement.reason,
    )
    session.add(entry)
    return entry


def balance_key(movement: LedgerMovement) -> LedgerBalanceKey:
    return LedgerBalanceKey(
        ledger_kind=movement.ledger_kind,
        processing_unit_id=movement.processing_unit_id,
        item_name=movement.item_name,
        item_code=movement.item_code,
        wool_content=movement.wool_content,
        color_code=movement.color_code,
        dye_lot_no=movement.dye_lot_no,
    )


def apply_balance(
    *, balances: LedgerBalances, movement: LedgerMovement
) -> tuple[Decimal, Decimal]:
    key = balance_key(movement)
    rolls, meters = balances.get(key, (Decimal("0"), Decimal("0")))
    result = (rolls + movement.rolls_delta, meters + movement.meters_delta)
    balances[key] = result
    return result


def reject_negative_balances(
    *, session: Session, processing_unit_id: uuid.UUID
) -> None:
    entries = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.processing_unit_id == processing_unit_id,
            InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
        )
    ).all()
    balances: LedgerBalances = {}
    for entry in entries:
        movement = LedgerMovement(
            ledger_kind=entry.ledger_kind,
            movement_type=entry.movement_type,
            business_date=entry.business_date,
            processing_unit_id=entry.processing_unit_id,
            item_name=entry.item_name,
            item_code=entry.item_code,
            wool_content=entry.wool_content,
            color_code=entry.color_code,
            dye_lot_no=entry.dye_lot_no,
            rolls_delta=entry.rolls_delta,
            meters_delta=entry.meters_delta,
        )
        apply_balance(balances=balances, movement=movement)
    if any(rolls < 0 or meters < 0 for rolls, meters in balances.values()):
        raise ConflictError("Insufficient inventory")

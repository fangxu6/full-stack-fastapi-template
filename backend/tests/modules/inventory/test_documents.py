import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.core.audit import bind_audit_actor
from app.core.exceptions import ConflictError
from app.models import InventoryDocument, InventoryDocumentLine, InventoryLedgerEntry
from app.models.inventory import InventoryCorrectionOperation, InventoryDocumentType
from app.modules.inventory.documents import (
    apply_approved_correction,
    create_document,
)
from app.modules.inventory.units import create_processing_unit
from app.schemas.inventory import InventoryDocumentCreate, MasterUnitCreate
from tests.utils.user import create_random_user


def _document_input(
    *, unit_id: uuid.UUID, number: str, quantity_rolls: Decimal
) -> InventoryDocumentCreate:
    return InventoryDocumentCreate(
        document_type=InventoryDocumentType.RAW_RECEIPT,
        business_date=date(2026, 8, 6),
        processing_unit_id=unit_id,
        document_number=number,
        lines=[
            {
                "item_name": "Raw fabric",
                "item_code": "RAW-001",
                "wool_content": "100% wool",
                "quantity_rolls": quantity_rolls,
            }
        ],
    )


def test_create_document_writes_ledger_and_rejects_negative_balance(
    db: Session,
) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    unit = create_processing_unit(
        session=db, unit_in=MasterUnitCreate(name="Document unit")
    )
    db.commit()

    created = create_document(
        session=db,
        document_in=_document_input(
            unit_id=unit.id,
            number="RAW-RECEIPT-1",
            quantity_rolls=Decimal("0.50"),
        ),
    )
    db.commit()

    assert created.lines[0].quantity_rolls == Decimal("0.50")
    with pytest.raises(ConflictError, match="Insufficient inventory"):
        create_document(
            session=db,
            document_in=InventoryDocumentCreate(
                document_type=InventoryDocumentType.RAW_RETURN,
                business_date=date(2026, 8, 6),
                processing_unit_id=unit.id,
                document_number="RAW-RETURN-1",
                lines=[
                    {
                        "item_name": "Raw fabric",
                        "item_code": "RAW-001",
                        "wool_content": "100% wool",
                        "quantity_rolls": Decimal("0.60"),
                    }
                ],
            ),
        )
    db.rollback()

    assert db.get(InventoryDocument, uuid.UUID(str(created.id))) is not None
    assert len(db.exec(select(InventoryLedgerEntry)).all()) == 1


def test_apply_approved_correction_replaces_document_ledger_effects(
    db: Session,
) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    unit = create_processing_unit(
        session=db, unit_in=MasterUnitCreate(name="Correction unit")
    )
    db.commit()
    created = create_document(
        session=db,
        document_in=_document_input(
            unit_id=unit.id,
            number="CORRECTION-1",
            quantity_rolls=Decimal("5"),
        ),
    )
    db.commit()
    document = db.get(InventoryDocument, uuid.UUID(str(created.id)))
    assert document is not None

    updated = apply_approved_correction(
        session=db,
        document=document,
        operation=InventoryCorrectionOperation.UPDATE_DOCUMENT,
        document_in=_document_input(
            unit_id=unit.id,
            number="CORRECTION-2",
            quantity_rolls=Decimal("3"),
        ),
    )
    db.commit()

    assert updated is not None
    assert updated.document_number == "CORRECTION-2"
    assert updated.lines[0].quantity_rolls == Decimal("3.00")
    lines = db.exec(
        select(InventoryDocumentLine).where(
            InventoryDocumentLine.document_id == document.id
        )
    ).all()
    ledgers = db.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id == lines[0].id
        )
    ).all()
    assert len(lines) == 1
    assert len(ledgers) == 1
    assert ledgers[0].rolls_delta == Decimal("3.00")


def test_apply_approved_correction_delete_and_restore_updates_ledger_state(
    db: Session,
) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    unit = create_processing_unit(
        session=db, unit_in=MasterUnitCreate(name="Delete restore unit")
    )
    db.commit()
    created = create_document(
        session=db,
        document_in=_document_input(
            unit_id=unit.id,
            number="DELETE-RESTORE-1",
            quantity_rolls=Decimal("1"),
        ),
    )
    db.commit()
    document = db.get(InventoryDocument, uuid.UUID(str(created.id)))
    assert document is not None

    apply_approved_correction(
        session=db,
        document=document,
        operation=InventoryCorrectionOperation.DELETE_DOCUMENT,
        document_in=None,
    )
    db.commit()
    line = db.exec(
        select(InventoryDocumentLine).where(
            InventoryDocumentLine.document_id == document.id
        )
    ).one()
    ledger = db.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id == line.id
        )
    ).one()
    assert document.deleted_at is not None
    assert ledger.deleted_at is not None

    apply_approved_correction(
        session=db,
        document=document,
        operation=InventoryCorrectionOperation.RESTORE_DOCUMENT,
        document_in=None,
    )
    db.commit()
    db.refresh(document)
    db.refresh(ledger)
    assert document.deleted_at is None
    assert ledger.deleted_at is None

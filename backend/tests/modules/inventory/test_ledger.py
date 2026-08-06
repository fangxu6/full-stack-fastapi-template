from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.exceptions import BadRequestError
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
)
from app.modules.inventory import ledger


def _movement(
    *,
    item_name: str = "Fabric",
    item_code: str | None = "FAB-001",
    rolls_delta: str = "1",
) -> ledger.LedgerMovement:
    return ledger.LedgerMovement(
        ledger_kind=InventoryLedgerKind.RAW,
        movement_type=InventoryMovementType.RAW_RECEIPT,
        business_date=date(2026, 8, 7),
        processing_unit_id=UUID("00000000-0000-0000-0000-000000000001"),
        item_name=item_name,
        item_code=item_code,
        wool_content="100%",
        color_code=None,
        dye_lot_no=None,
        rolls_delta=Decimal(rolls_delta),
        meters_delta=Decimal("0"),
    )


def test_document_movement_policy_is_shared_by_import_and_manual_paths() -> None:
    assert ledger.movement_for_document_type(InventoryDocumentType.RAW_RETURN) == (
        InventoryLedgerKind.RAW,
        InventoryMovementType.RAW_RETURN,
        Decimal("-1"),
    )
    with pytest.raises(BadRequestError):
        ledger.movement_for_document_type(InventoryDocumentType.FINISHED_RECEIPT)
    assert (
        ledger.movement_for_document_type(
            InventoryDocumentType.FINISHED_RECEIPT,
            allow_finished_receipt=True,
        )[1]
        is InventoryMovementType.FINISHED_RECEIPT
    )


def test_balance_key_and_application_keep_inventory_dimensions_local() -> None:
    balances: ledger.LedgerBalances = {}
    first = _movement(rolls_delta="2")
    second = _movement(item_name="Different fabric", rolls_delta="3")

    ledger.apply_balance(balances=balances, movement=first)
    ledger.apply_balance(balances=balances, movement=second)

    assert balances[ledger.balance_key(first)] == (Decimal("2"), Decimal("0"))
    assert balances[ledger.balance_key(second)] == (Decimal("3"), Decimal("0"))

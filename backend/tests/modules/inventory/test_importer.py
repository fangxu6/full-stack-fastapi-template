from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError
from app.models import (
    InventoryDocumentLine,
    InventoryImportBatch,
    InventoryLedgerEntry,
    LegacyImportRow,
    ProcessingUnit,
    ReceivingUnit,
    User,
)
from app.models.inventory import InventoryDocumentType, InventoryMovementType
from app.modules.inventory.importer import (
    _date,
    _movement_definitions,
    _row_values,
    _source_balance_snapshot,
    import_workbooks,
)

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize(
    ("filename", "expected_row", "expected_values"),
    [
        (
            "2026年坯布入库明细.xlsx",
            3,
            {
                "品名": "驼坯",
                "品号": "2270-LTS-5",
                "库存": 5,
            },
        ),
        (
            "2026年成品进出明细.xlsx",
            4,
            {
                "品名": "染色双顺",
                "库存匹数": 12,
                "库存米数": 642.3,
            },
        ),
    ],
)
def test_row_values_recognizes_the_real_legacy_workbook_layouts(
    filename: str, expected_row: int, expected_values: dict[str, object]
) -> None:
    workbook_path = WORKSPACE_ROOT / "hongxia" / filename
    if not workbook_path.exists():
        pytest.skip(f"Legacy workbook fixture is unavailable: {workbook_path}")
    workbook = load_workbook(
        workbook_path,
        data_only=True,
        read_only=True,
    )

    source_row, cells = next(iter(_row_values(workbook["三泰"])))

    assert source_row == expected_row
    for field, expected_value in expected_values.items():
        assert cells[field] == expected_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (46090, date(2026, 3, 9)),
        ("46090", date(2026, 3, 9)),
        ("2026/3/9", date(2026, 3, 9)),
        ("2026-03-09 00:00:00", date(2026, 3, 9)),
        (datetime(2026, 3, 9), date(2026, 3, 9)),
        ("2025年结存", date(2025, 12, 31)),
    ],
)
def test_date_parser_preserves_legacy_workbook_dates(
    value: object, expected: date
) -> None:
    assert _date(value, epoch=CALENDAR_WINDOWS_1900) == expected


def test_date_parser_rejects_unrecognized_values() -> None:
    with pytest.raises(BadRequestError, match="Invalid inventory date"):
        _date(None, epoch=CALENDAR_WINDOWS_1900)


def test_raw_return_row_uses_its_base_processing_unit() -> None:
    movements, processing_unit_name = _movement_definitions(
        cells={"加工单位": "天双退走", "入库": 2},
        kind="RAW",
        worksheet_name="天双",
    )

    assert processing_unit_name == "天双"
    assert movements == [(InventoryDocumentType.RAW_RETURN, 2, None)]


def test_finished_row_keeps_roll_and_meter_snapshots() -> None:
    cells = {
        "入库匹数": 3,
        "入库米数": 120.5,
        "出库匹数": 1,
        "出库米数": 38.2,
        "库存匹数": 12,
        "库存米数": 642.3,
    }

    movements, _ = _movement_definitions(
        cells=cells,
        kind="FINISHED",
        worksheet_name="三泰",
    )

    assert movements == [
        (
            InventoryDocumentType.FINISHED_RECEIPT,
            Decimal("3"),
            Decimal("120.5"),
        ),
        (
            InventoryDocumentType.FINISHED_SHIPMENT,
            Decimal("1"),
            Decimal("38.2"),
        ),
    ]
    assert _source_balance_snapshot(cells, "FINISHED") == {
        "rolls": 12,
        "meters": 642.3,
    }


def test_finished_row_preserves_decimal_rolls() -> None:
    movements, _ = _movement_definitions(
        cells={"出库匹数": 0.5, "出库米数": 20},
        kind="FINISHED",
        worksheet_name="三泰",
    )

    assert movements == [
        (
            InventoryDocumentType.FINISHED_SHIPMENT,
            Decimal("0.5"),
            Decimal("20"),
        )
    ]


def test_negative_finished_quantity_is_normalized_as_a_shipment() -> None:
    movements, _ = _movement_definitions(
        cells={"入库匹数": -1, "入库米数": -35.5},
        kind="FINISHED",
        worksheet_name="三泰",
    )

    assert movements == [
        (
            InventoryDocumentType.FINISHED_SHIPMENT,
            Decimal("1"),
            Decimal("35.5"),
        )
    ]


def test_meter_only_finished_history_is_preserved() -> None:
    movements, _ = _movement_definitions(
        cells={"入库匹数": 0, "入库米数": 20},
        kind="FINISHED",
        worksheet_name="三泰",
    )

    assert movements == [
        (
            InventoryDocumentType.FINISHED_RECEIPT,
            Decimal("0"),
            Decimal("20"),
        )
    ]


def _write_raw_workbook(path: Path, quantity: object) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["日期", "加工单位", "品名", "品号", "含毛量", "入库"])
    sheet.append(["2026-07-14", "回滚加工厂", "回滚坯布", "RB-001", "100%", quantity])
    workbook.save(path)


def test_import_rolls_back_batch_when_a_workbook_row_is_invalid(
    db: Session, tmp_path: Path
) -> None:
    actor = db.exec(select(User)).first()
    assert actor is not None
    raw_workbook = tmp_path / "raw-invalid.xlsx"
    finished_workbook = tmp_path / "finished-empty.xlsx"
    _write_raw_workbook(raw_workbook, "not-a-quantity")
    _write_raw_workbook(finished_workbook, 0)
    tracked_models = (
        InventoryDocumentLine,
        InventoryImportBatch,
        InventoryLedgerEntry,
        LegacyImportRow,
        ProcessingUnit,
        ReceivingUnit,
    )
    counts_before = {
        model: db.exec(select(func.count()).select_from(model)).one()
        for model in tracked_models
    }

    with pytest.raises(BadRequestError, match="Invalid inventory quantity"):
        import_workbooks(
            session=db,
            actor_user_id=actor.id,
            raw_workbook=raw_workbook,
            finished_workbook=finished_workbook,
        )

    assert {
        model: db.exec(select(func.count()).select_from(model)).one()
        for model in tracked_models
    } == counts_before
    assert (
        db.exec(
            select(ProcessingUnit).where(ProcessingUnit.normalized_name == "回滚加工厂")
        ).first()
        is None
    )


def test_import_rejects_an_inactive_human_without_creating_a_batch(
    db: Session, tmp_path: Path
) -> None:
    actor = User(
        email="inactive-importer@example.com",
        hashed_password="not-used",
        is_active=False,
    )
    db.add(actor)
    db.commit()
    batch_count_before = db.exec(
        select(func.count()).select_from(InventoryImportBatch)
    ).one()

    with pytest.raises(BadRequestError, match="must be active"):
        import_workbooks(
            session=db,
            actor_user_id=actor.id,
            raw_workbook=tmp_path / "not-read-raw.xlsx",
            finished_workbook=tmp_path / "not-read-finished.xlsx",
        )

    assert (
        db.exec(select(func.count()).select_from(InventoryImportBatch)).one()
        == batch_count_before
    )
    db.delete(actor)
    db.commit()


def test_import_accepts_a_preprovisioned_system_actor(
    db: Session, tmp_path: Path
) -> None:
    from app.core.audit import provision_system_actor

    actor = provision_system_actor(
        session=db,
        actor_key="inventory-test-import",
        email="inventory-test-import@system.invalid",
    )
    db.commit()
    raw_workbook = tmp_path / "raw-system-actor.xlsx"
    finished_workbook = tmp_path / "finished-system-actor.xlsx"
    _write_raw_workbook(raw_workbook, 0)
    Workbook().save(finished_workbook)

    import_workbooks(
        session=db,
        actor_user_id=actor.id,
        raw_workbook=raw_workbook,
        finished_workbook=finished_workbook,
    )

    batch = db.exec(
        select(InventoryImportBatch).order_by(InventoryImportBatch.imported_at.desc())
    ).first()
    assert batch is not None
    assert batch.created_by == actor.id
    assert batch.updated_by == actor.id


def test_import_reconciliation_opening_is_traceable_and_balances_by_key(
    db: Session, tmp_path: Path
) -> None:
    actor = db.exec(select(User)).first()
    assert actor is not None
    raw_workbook = tmp_path / "raw-return.xlsx"
    finished_workbook = tmp_path / "finished-empty.xlsx"
    _write_raw_workbook(raw_workbook, -2)
    _write_raw_workbook(finished_workbook, 0)

    report = import_workbooks(
        session=db,
        actor_user_id=actor.id,
        raw_workbook=raw_workbook,
        finished_workbook=finished_workbook,
    )

    batch = db.exec(
        select(InventoryImportBatch).order_by(InventoryImportBatch.imported_at.desc())
    ).first()
    assert batch is not None
    assert batch.reconciliation_report == report
    assert report["reconciliation_openings"] == 1

    entries = db.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.import_batch_id == batch.id,
            InventoryLedgerEntry.item_name == "回滚坯布",
        )
    ).all()
    opening = next(
        entry
        for entry in entries
        if entry.movement_type is InventoryMovementType.MIGRATION_RECONCILIATION_OPENING
    )
    movement = next(
        entry
        for entry in entries
        if entry.movement_type is InventoryMovementType.RAW_RETURN
    )
    assert opening.document_line_id is None
    assert opening.legacy_import_row_id is not None
    assert opening.import_batch_id == batch.id
    assert opening.rolls_delta == Decimal("2")
    assert opening.reason == "历史迁移对账期初"
    assert movement.rolls_delta == Decimal("-2")
    assert sum(entry.rolls_delta for entry in entries) == Decimal("0")

    source = db.get(LegacyImportRow, opening.legacy_import_row_id)
    assert source is not None
    assert source.import_batch_id == batch.id
    assert source.requires_cleanup is False


def _write_finished_workbook(path: Path, rolls: float = 2) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "日期",
            "加工单位",
            "品名",
            "含毛量",
            "颜色+色号",
            "缸号",
            "入库匹数",
            "入库米数",
            "库存匹数",
            "库存米数",
        ]
    )
    sheet.append(
        [
            "2026-07-14",
            "颜色加工厂",
            "颜色成品",
            "70%",
            "焦糖",
            "LOT-001",
            rolls,
            30,
            2,
            30,
        ]
    )
    workbook.save(path)


def test_import_preserves_the_compound_color_column(
    db: Session, tmp_path: Path
) -> None:
    actor = db.exec(select(User)).first()
    assert actor is not None
    raw_workbook = tmp_path / "raw-empty.xlsx"
    finished_workbook = tmp_path / "finished-color.xlsx"
    _write_raw_workbook(raw_workbook, 0)
    _write_finished_workbook(finished_workbook)
    existing_import_batch_ids = set(db.exec(select(InventoryImportBatch.id)).all())

    import_workbooks(
        session=db,
        actor_user_id=actor.id,
        raw_workbook=raw_workbook,
        finished_workbook=finished_workbook,
    )

    new_import_batch_ids = set(db.exec(select(InventoryImportBatch.id)).all())
    new_import_batch_ids -= existing_import_batch_ids
    assert len(new_import_batch_ids) == 1
    import_batch_id = new_import_batch_ids.pop()
    ledger = db.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.color_code == "焦糖",
            InventoryLedgerEntry.import_batch_id == import_batch_id,
        )
    ).one()
    assert ledger is not None
    assert ledger.color_code == "焦糖"


def test_import_preserves_decimal_rolls(db: Session, tmp_path: Path) -> None:
    actor = db.exec(select(User)).first()
    assert actor is not None
    raw_workbook = tmp_path / "raw-empty.xlsx"
    finished_workbook = tmp_path / "finished-decimal-rolls.xlsx"
    _write_raw_workbook(raw_workbook, 0)
    _write_finished_workbook(finished_workbook, rolls=0.5)

    import_workbooks(
        session=db,
        actor_user_id=actor.id,
        raw_workbook=raw_workbook,
        finished_workbook=finished_workbook,
    )

    line = db.exec(
        select(InventoryDocumentLine).where(
            InventoryDocumentLine.quantity_rolls == Decimal("0.5")
        )
    ).one()
    ledger = db.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id == line.id
        )
    ).one()
    assert line.quantity_rolls == Decimal("0.5")
    assert ledger.rolls_delta == Decimal("0.5")

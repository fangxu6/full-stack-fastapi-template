from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.models.inventory import InventoryDocumentType
from app.modules.inventory.importer import (
    _movement_definitions,
    _row_values,
    _source_balance_snapshot,
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
    workbook = load_workbook(
        WORKSPACE_ROOT / "hongxia" / filename,
        data_only=True,
        read_only=True,
    )

    source_row, cells = next(iter(_row_values(workbook["三泰"])))

    assert source_row == expected_row
    for field, expected_value in expected_values.items():
        assert cells[field] == expected_value


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

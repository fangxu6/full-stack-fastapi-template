from datetime import date
from io import BytesIO

from openpyxl import Workbook

from app.models.inventory import InventoryDocumentType
from app.modules.inventory.document_import_adapter import read_document_workbook


def _workbook_bytes(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "单据导入"
    worksheet.append(
        [
            "单据类型",
            "日期",
            "单据号",
            "加工单位",
            "收货单位",
            "备注",
            "品名",
            "货号",
            "含毛量",
            "颜色",
            "缸号",
            "匹数",
            "米数",
        ]
    )
    for row in rows:
        worksheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_document_adapter_groups_rows_without_database_access() -> None:
    content = _workbook_bytes(
        [
            [
                InventoryDocumentType.RAW_RECEIPT,
                date(2026, 8, 7),
                "RAW-001",
                "加工厂",
                None,
                None,
                "坯布",
                "RAW-1",
                "100%",
                None,
                None,
                2,
                None,
            ],
            [
                InventoryDocumentType.RAW_RECEIPT,
                date(2026, 8, 7),
                "RAW-001",
                "加工厂",
                None,
                None,
                "坯布2",
                "RAW-2",
                "100%",
                None,
                None,
                1,
                None,
            ],
        ]
    )

    groups, issues = read_document_workbook(content)

    assert issues == []
    assert len(groups) == 1
    assert groups[0].document_number == "RAW-001"
    assert len(groups[0].rows) == 2


def test_document_adapter_reports_inconsistent_document_fields() -> None:
    content = _workbook_bytes(
        [
            [
                InventoryDocumentType.RAW_RECEIPT,
                date(2026, 8, 7),
                "RAW-002",
                "加工厂",
                None,
                None,
                "坯布",
                "RAW-1",
                "100%",
                None,
                None,
                2,
                None,
            ],
            [
                InventoryDocumentType.RAW_RETURN,
                date(2026, 8, 7),
                "RAW-002",
                "加工厂",
                None,
                None,
                "坯布2",
                "RAW-2",
                "100%",
                None,
                None,
                1,
                None,
            ],
        ]
    )

    groups, issues = read_document_workbook(content)

    assert groups == []
    assert len(issues) == 1
    assert issues[0].field == "document_type"
    assert issues[0].message == "Document fields must match within a document number"

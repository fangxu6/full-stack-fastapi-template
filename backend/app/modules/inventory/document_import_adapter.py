from collections.abc import Collection
from dataclasses import dataclass
from typing import cast

from app.core.excel import ExcelIssue, ExcelRow, read_xlsx_rows
from app.models.inventory import InventoryDocumentType
from app.schemas.inventory import InventoryDocumentExcelRow

DOCUMENT_WORKSHEET_NAME = "单据导入"


@dataclass(frozen=True)
class DocumentWorkbookGroup:
    document_number: str
    rows: tuple[ExcelRow, ...]


def document_issue(row: ExcelRow, *, field_name: str, message: str) -> ExcelIssue:
    field = InventoryDocumentExcelRow.model_fields[field_name]
    return ExcelIssue(
        worksheet=row.worksheet,
        row=row.row,
        column=field.alias or field_name,
        field=field_name,
        message=message,
    )


def read_document_workbook(
    content: bytes,
    *,
    allowed_document_types: Collection[InventoryDocumentType] | None = None,
) -> tuple[list[DocumentWorkbookGroup], list[ExcelIssue]]:
    result = read_xlsx_rows(
        content,
        model_type=InventoryDocumentExcelRow,
        worksheet_name=DOCUMENT_WORKSHEET_NAME,
    )
    if result.issues:
        return [], result.issues

    issues: list[ExcelIssue] = []
    groups: dict[str, list[ExcelRow]] = {}
    for row in result.rows:
        value = cast(InventoryDocumentExcelRow, row.value)
        if (
            allowed_document_types is not None
            and value.document_type not in allowed_document_types
        ):
            issues.append(
                document_issue(
                    row,
                    field_name="document_type",
                    message="Document type is not allowed for this import",
                )
            )
            continue
        groups.setdefault(value.document_number, []).append(row)

    if issues:
        return [], issues

    document_fields = (
        "document_type",
        "business_date",
        "processing_unit_name",
        "receiving_unit_name",
        "remarks",
    )
    for group in groups.values():
        first = cast(InventoryDocumentExcelRow, group[0].value)
        for row in group[1:]:
            value = cast(InventoryDocumentExcelRow, row.value)
            for field_name in document_fields:
                if getattr(value, field_name) != getattr(first, field_name):
                    issues.append(
                        document_issue(
                            row,
                            field_name=field_name,
                            message="Document fields must match within a document number",
                        )
                    )

    if issues:
        return [], issues
    return [
        DocumentWorkbookGroup(document_number=number, rows=tuple(rows))
        for number, rows in groups.items()
    ], []

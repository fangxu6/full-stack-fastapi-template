import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError
from app.models import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryImportBatch,
    InventoryLedgerEntry,
    LegacyImportRow,
    ProcessingUnit,
    ReceivingUnit,
    User,
)
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
    LegacyWorkbookKind,
)

IMPORTER_VERSION = "inventory-xlsx-v1"
MISSING_ITEM_CODE = "未填写品号"
MISSING_WOOL_CONTENT = "未填写含毛量"
MISSING_DYE_LOT = "未分缸"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: object, placeholder: str | None = None) -> str | None:
    if value is None or not str(value).strip():
        return placeholder
    return str(value).strip()


def _number(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0).replace(",", ""))
    except Exception as err:
        raise BadRequestError(f"Invalid inventory quantity: {value}") from err


def _date(value: object) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return date.today()


def _header_key(value: object) -> str:
    return "".join(str(value or "").strip().lower().split())


def _row_values(sheet: object) -> list[tuple[int, dict[str, object]]]:
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_header_key(cell) for cell in rows[0]]
    return [
        (number, {headers[index]: cell for index, cell in enumerate(row) if headers[index]})
        for number, row in enumerate(rows[1:], start=2)
        if any(cell is not None for cell in row)
    ]


def _value(cells: dict[str, object], *names: str) -> object:
    for name in names:
        if name in cells:
            return cells[name]
    return None


def import_workbooks(
    *, session: Session, actor_user_id: uuid.UUID, raw_workbook: Path, finished_workbook: Path, dry_run: bool = False
) -> dict[str, object]:
    actor = session.get(User, actor_user_id)
    if not actor:
        raise BadRequestError("Import actor does not exist")
    raw_hash, finished_hash = _sha256(raw_workbook), _sha256(finished_workbook)
    fingerprint = hashlib.sha256(f"{raw_hash}:{finished_hash}:{IMPORTER_VERSION}".encode()).hexdigest()
    if session.exec(select(InventoryImportBatch).where(InventoryImportBatch.source_fingerprint == fingerprint)).first():
        raise ConflictError("These workbooks were already imported")
    audit = {"created_by": actor.id, "updated_by": actor.id}
    batch = InventoryImportBatch(source_fingerprint=fingerprint, raw_workbook_sha256=raw_hash, finished_workbook_sha256=finished_hash, importer_version=IMPORTER_VERSION, reconciliation_report={}, **audit)
    session.add(batch)
    session.flush()
    report = {"source_rows": 0, "ledger_entries": 0, "requires_cleanup": 0, "reconciliation_openings": 0}
    try:
        _import_book(session, batch, actor, raw_workbook, LegacyWorkbookKind.RAW, report)
        _import_book(session, batch, actor, finished_workbook, LegacyWorkbookKind.FINISHED, report)
        batch.reconciliation_report = report
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    return report


def _import_book(session: Session, batch: InventoryImportBatch, actor: User, path: Path, kind: LegacyWorkbookKind, report: dict[str, int]) -> None:
    workbook = load_workbook(path, read_only=True, data_only=True)
    for sheet in workbook.worksheets:
        unit = _find_or_create_unit(session, ProcessingUnit, sheet.title, actor)
        for source_row, cells in _row_values(sheet):
            item_name = _text(_value(cells, "品名", "名称"))
            if not item_name:
                continue
            report["source_rows"] += 1
            item_code = _text(_value(cells, "品号", "货号"), MISSING_ITEM_CODE)
            wool = _text(_value(cells, "含毛量", "含毛"), MISSING_WOOL_CONTENT)
            color = _text(_value(cells, "颜色", "色号"))
            lot = _text(_value(cells, "缸号"), MISSING_DYE_LOT if kind is LegacyWorkbookKind.FINISHED else None)
            cleanup = item_code == MISSING_ITEM_CODE or wool == MISSING_WOOL_CONTENT or lot == MISSING_DYE_LOT
            source = LegacyImportRow(import_batch_id=batch.id, workbook_kind=kind, workbook_name=path.name, worksheet_name=sheet.title, source_row_number=source_row, raw_cells=json.loads(json.dumps(cells, default=str)), source_balance_snapshot={}, requires_cleanup=cleanup, created_by=actor.id, updated_by=actor.id)
            session.add(source)
            session.flush()
            if cleanup:
                report["requires_cleanup"] += 1
            inbound = _number(_value(cells, "入库", "入库匹数", "入库数量"))
            outbound = _number(_value(cells, "出库", "出库匹数", "出库数量"))
            if kind is LegacyWorkbookKind.RAW and inbound < 0:
                outbound, inbound = -inbound, Decimal("0")
            for document_type, quantity, direction in ((InventoryDocumentType.RAW_RECEIPT if kind is LegacyWorkbookKind.RAW else InventoryDocumentType.FINISHED_RECEIPT, inbound, 1), (InventoryDocumentType.RAW_RETURN if kind is LegacyWorkbookKind.RAW else InventoryDocumentType.FINISHED_SHIPMENT, outbound, -1)):
                if quantity > 0:
                    _write_legacy_movement(session, batch, source, actor, unit, document_type, item_name, item_code, wool, color, lot, quantity, direction, _date(_value(cells, "日期", "时间")), _text(_value(cells, "单号", "出库单号")), report)


def _find_or_create_unit(session: Session, model: type[ProcessingUnit] | type[ReceivingUnit], name: str, actor: User) -> ProcessingUnit | ReceivingUnit:
    normalized = " ".join(name.split())
    unit = session.exec(select(model).where(model.normalized_name == normalized)).first()
    if unit:
        return unit
    unit = model(name=normalized, normalized_name=normalized, created_by=actor.id, updated_by=actor.id)
    session.add(unit)
    session.flush()
    return unit


def _write_legacy_movement(session: Session, batch: InventoryImportBatch, source: LegacyImportRow, actor: User, unit: ProcessingUnit, document_type: InventoryDocumentType, item_name: str, item_code: str | None, wool: str, color: str | None, lot: str | None, quantity: Decimal, direction: int, business_date: date, number: str | None, report: dict[str, int]) -> None:
    receiving = _find_or_create_unit(session, ReceivingUnit, "历史未填写收货单位", actor) if document_type is InventoryDocumentType.FINISHED_SHIPMENT else None
    document = InventoryDocument(document_type=document_type, business_date=business_date, processing_unit_id=unit.id, receiving_unit_id=receiving.id if receiving else None, document_number=number, is_legacy=True, created_by=actor.id, updated_by=actor.id)
    session.add(document)
    session.flush()
    meters = Decimal("0")
    line = InventoryDocumentLine(document_id=document.id, line_no=1, item_name=item_name, item_code=item_code, wool_content=wool, color_code=color, dye_lot_no=lot, quantity_rolls=int(quantity), quantity_meters=None, created_by=actor.id, updated_by=actor.id)
    session.add(line)
    session.flush()
    kind = InventoryLedgerKind.RAW if document_type in {InventoryDocumentType.RAW_RECEIPT, InventoryDocumentType.RAW_RETURN} else InventoryLedgerKind.FINISHED
    session.add(InventoryLedgerEntry(ledger_kind=kind, movement_type=InventoryMovementType(document_type), business_date=business_date, processing_unit_id=unit.id, document_line_id=line.id, legacy_import_row_id=source.id, import_batch_id=batch.id, item_name=item_name, item_code=item_code, wool_content=wool, color_code=color, dye_lot_no=lot, rolls_delta=direction * int(quantity), meters_delta=meters, created_by=actor.id, updated_by=actor.id))
    report["ledger_entries"] += 1

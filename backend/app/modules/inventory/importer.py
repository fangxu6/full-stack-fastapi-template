import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

from openpyxl import load_workbook  # type: ignore[import-untyped]
from openpyxl.worksheet.worksheet import Worksheet  # type: ignore[import-untyped]
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


def _row_values(sheet: Worksheet) -> list[tuple[int, dict[str, object]]]:
    rows = list(sheet.iter_rows(values_only=True))
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if any(_header_key(cell) == "日期" for cell in row)
        ),
        None,
    )
    if header_index is None:
        return []

    header_row = rows[header_index]
    next_row = rows[header_index + 1] if header_index + 1 < len(rows) else ()
    has_quantity_subheaders = any(
        _header_key(cell) in {"匹数", "米数"} for cell in next_row
    )
    headers: list[str] = []
    quantity_group: str | None = None
    for index, cell in enumerate(header_row):
        header = _header_key(cell)
        if header in {"入库", "出库", "库存"}:
            quantity_group = header
        elif header:
            quantity_group = None
        subheader = _header_key(next_row[index]) if has_quantity_subheaders else ""
        headers.append(
            f"{quantity_group}{subheader}"
            if quantity_group and subheader in {"匹数", "米数"}
            else header
        )
    data_start = header_index + 2 if has_quantity_subheaders else header_index + 1
    return [
        (
            number,
            {headers[index]: cell for index, cell in enumerate(row) if headers[index]},
        )
        for number, row in enumerate(rows[data_start:], start=data_start + 1)
        if any(cell is not None for cell in row)
    ]


def _value(cells: dict[str, object], *names: str) -> object:
    for name in names:
        if name in cells:
            return cells[name]
    return None


def _source_balance_snapshot(
    cells: dict[str, object], kind: LegacyWorkbookKind | str
) -> dict[str, object]:
    if LegacyWorkbookKind(kind) is LegacyWorkbookKind.RAW:
        return {"rolls": _value(cells, "库存")}
    return {
        "rolls": _value(cells, "库存匹数"),
        "meters": _value(cells, "库存米数"),
    }


def _movement_definitions(
    *,
    cells: dict[str, object],
    kind: LegacyWorkbookKind | str,
    worksheet_name: str,
) -> tuple[list[tuple[InventoryDocumentType, Decimal, Decimal | None]], str]:
    workbook_kind = LegacyWorkbookKind(kind)
    source_unit = _text(_value(cells, "加工单位"), worksheet_name) or worksheet_name
    if workbook_kind is LegacyWorkbookKind.RAW:
        rolls = _number(_value(cells, "入库", "入库匹数", "入库数量"))
        is_return = source_unit.endswith("退走") or rolls < 0
        processing_unit_name = (
            source_unit.removesuffix("退走") if is_return else source_unit
        )
        return (
            [
                (
                    InventoryDocumentType.RAW_RETURN
                    if is_return
                    else InventoryDocumentType.RAW_RECEIPT,
                    abs(rolls),
                    None,
                )
            ]
            if rolls
            else [],
            processing_unit_name,
        )

    movements: list[tuple[InventoryDocumentType, Decimal, Decimal | None]] = []
    for document_type, rolls_name, meters_name in (
        (InventoryDocumentType.FINISHED_RECEIPT, "入库匹数", "入库米数"),
        (InventoryDocumentType.FINISHED_SHIPMENT, "出库匹数", "出库米数"),
    ):
        rolls = _number(_value(cells, rolls_name))
        meters = _number(_value(cells, meters_name))
        if rolls or meters:
            normalized_type = document_type
            if rolls < 0:
                normalized_type = (
                    InventoryDocumentType.FINISHED_SHIPMENT
                    if document_type is InventoryDocumentType.FINISHED_RECEIPT
                    else InventoryDocumentType.FINISHED_RECEIPT
                )
            movements.append((normalized_type, abs(rolls), abs(meters)))
    return movements, source_unit


def import_workbooks(
    *,
    session: Session,
    actor_user_id: uuid.UUID,
    raw_workbook: Path,
    finished_workbook: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    actor = session.get(User, actor_user_id)
    if not actor:
        raise BadRequestError("Import actor does not exist")
    raw_hash, finished_hash = _sha256(raw_workbook), _sha256(finished_workbook)
    fingerprint = hashlib.sha256(
        f"{raw_hash}:{finished_hash}:{IMPORTER_VERSION}".encode()
    ).hexdigest()
    if session.exec(
        select(InventoryImportBatch).where(
            InventoryImportBatch.source_fingerprint == fingerprint
        )
    ).first():
        raise ConflictError("These workbooks were already imported")
    batch = InventoryImportBatch(
        source_fingerprint=fingerprint,
        raw_workbook_sha256=raw_hash,
        finished_workbook_sha256=finished_hash,
        importer_version=IMPORTER_VERSION,
        reconciliation_report={},
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(batch)
    session.flush()
    report: dict[str, int] = {
        "source_rows": 0,
        "ledger_entries": 0,
        "requires_cleanup": 0,
        "reconciliation_openings": 0,
    }
    balances: dict[tuple[object, ...], tuple[Decimal, Decimal]] = {}
    try:
        _import_book(
            session,
            batch,
            actor,
            raw_workbook,
            LegacyWorkbookKind.RAW,
            report,
            balances,
        )
        _import_book(
            session,
            batch,
            actor,
            finished_workbook,
            LegacyWorkbookKind.FINISHED,
            report,
            balances,
        )
        batch.reconciliation_report = cast(dict[str, object], report)
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    return report


def _import_book(
    session: Session,
    batch: InventoryImportBatch,
    actor: User,
    path: Path,
    kind: LegacyWorkbookKind,
    report: dict[str, int],
    balances: dict[tuple[object, ...], tuple[Decimal, Decimal]],
) -> None:
    workbook = load_workbook(path, read_only=True, data_only=True)
    for sheet in workbook.worksheets:
        for source_row, cells in _row_values(sheet):
            item_name = _text(_value(cells, "品名", "名称"))
            if not item_name:
                continue
            movements, processing_unit_name = _movement_definitions(
                cells=cells, kind=kind, worksheet_name=sheet.title
            )
            unit = cast(
                ProcessingUnit,
                _find_or_create_unit(
                    session, ProcessingUnit, processing_unit_name, actor
                ),
            )
            report["source_rows"] += 1
            item_code = _text(_value(cells, "品号", "货号"), MISSING_ITEM_CODE)
            wool = (
                _text(_value(cells, "含毛量", "含毛"), MISSING_WOOL_CONTENT)
                or MISSING_WOOL_CONTENT
            )
            color = _text(_value(cells, "颜色", "色号"))
            lot = _text(
                _value(cells, "缸号"),
                MISSING_DYE_LOT if kind is LegacyWorkbookKind.FINISHED else None,
            )
            cleanup = (
                item_code == MISSING_ITEM_CODE
                or wool == MISSING_WOOL_CONTENT
                or lot == MISSING_DYE_LOT
            )
            source = LegacyImportRow(
                import_batch_id=batch.id,
                workbook_kind=kind,
                workbook_name=path.name,
                worksheet_name=sheet.title,
                source_row_number=source_row,
                raw_cells=json.loads(json.dumps(cells, default=str)),
                source_balance_snapshot=_source_balance_snapshot(cells, kind),
                requires_cleanup=cleanup,
                created_by=actor.id,
                updated_by=actor.id,
            )
            session.add(source)
            session.flush()
            if cleanup:
                report["requires_cleanup"] += 1
            for document_type, rolls, meters in movements:
                _write_legacy_movement(
                    session=session,
                    batch=batch,
                    source=source,
                    actor=actor,
                    unit=unit,
                    document_type=document_type,
                    item_name=item_name,
                    item_code=item_code,
                    wool=wool,
                    color=color,
                    lot=lot,
                    rolls=rolls,
                    meters=meters,
                    business_date=_date(_value(cells, "日期", "时间")),
                    number=_text(_value(cells, "单号", "出库单号")),
                    receiving_name=_text(_value(cells, "收货单位")),
                    report=report,
                    balances=balances,
                )


def _find_or_create_unit(
    session: Session,
    model: type[ProcessingUnit] | type[ReceivingUnit],
    name: str,
    actor: User,
) -> ProcessingUnit | ReceivingUnit:
    normalized = " ".join(name.split())
    unit = session.exec(
        select(model).where(model.normalized_name == normalized)
    ).first()
    if unit:
        return cast(ProcessingUnit | ReceivingUnit, unit)
    unit = model(
        name=normalized,
        normalized_name=normalized,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(unit)
    session.flush()
    return unit


def _write_legacy_movement(
    *,
    session: Session,
    batch: InventoryImportBatch,
    source: LegacyImportRow,
    actor: User,
    unit: ProcessingUnit,
    document_type: InventoryDocumentType,
    item_name: str,
    item_code: str | None,
    wool: str,
    color: str | None,
    lot: str | None,
    rolls: Decimal,
    meters: Decimal | None,
    business_date: date,
    number: str | None,
    receiving_name: str | None,
    report: dict[str, int],
    balances: dict[tuple[object, ...], tuple[Decimal, Decimal]],
) -> None:
    is_finished = document_type in {
        InventoryDocumentType.FINISHED_RECEIPT,
        InventoryDocumentType.FINISHED_SHIPMENT,
    }
    direction = (
        -1
        if document_type
        in {
            InventoryDocumentType.RAW_RETURN,
            InventoryDocumentType.FINISHED_SHIPMENT,
        }
        else 1
    )
    receiving = (
        _find_or_create_unit(
            session,
            ReceivingUnit,
            receiving_name or "历史未填写收货单位",
            actor,
        )
        if document_type is InventoryDocumentType.FINISHED_SHIPMENT
        else None
    )
    document = InventoryDocument(
        document_type=document_type,
        business_date=business_date,
        processing_unit_id=unit.id,
        receiving_unit_id=receiving.id if receiving else None,
        document_number=number,
        is_legacy=True,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(document)
    session.flush()
    line = InventoryDocumentLine(
        document_id=document.id,
        line_no=1,
        item_name=item_name,
        item_code=item_code if not is_finished else None,
        wool_content=wool,
        color_code=color if is_finished else None,
        dye_lot_no=lot if is_finished else None,
        quantity_rolls=int(rolls),
        quantity_meters=meters if is_finished and meters else None,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(line)
    session.flush()
    ledger_kind = (
        InventoryLedgerKind.FINISHED if is_finished else InventoryLedgerKind.RAW
    )
    ledger_item_code = item_code if not is_finished else None
    ledger_color = color if is_finished else None
    ledger_lot = lot if is_finished else None
    meter_delta = direction * (meters or Decimal("0"))
    rolls_delta = direction * int(rolls)
    balance_key = (
        ledger_kind,
        unit.id,
        item_name,
        ledger_item_code,
        wool,
        ledger_color,
        ledger_lot,
    )
    balance_rolls, balance_meters = balances.get(
        balance_key, (Decimal("0"), Decimal("0"))
    )
    opening_rolls = max(Decimal("0"), -(balance_rolls + rolls_delta))
    opening_meters = max(Decimal("0"), -(balance_meters + meter_delta))
    if opening_rolls or opening_meters:
        session.add(
            InventoryLedgerEntry(
                ledger_kind=ledger_kind,
                movement_type=InventoryMovementType.MIGRATION_RECONCILIATION_OPENING,
                business_date=business_date,
                processing_unit_id=unit.id,
                legacy_import_row_id=source.id,
                import_batch_id=batch.id,
                item_name=item_name,
                item_code=ledger_item_code,
                wool_content=wool,
                color_code=ledger_color,
                dye_lot_no=ledger_lot,
                rolls_delta=int(opening_rolls),
                meters_delta=opening_meters,
                reason="历史迁移对账期初",
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
        report["ledger_entries"] += 1
        report["reconciliation_openings"] += 1
        balance_rolls += opening_rolls
        balance_meters += opening_meters
    session.add(
        InventoryLedgerEntry(
            ledger_kind=ledger_kind,
            movement_type=InventoryMovementType(document_type),
            business_date=business_date,
            processing_unit_id=unit.id,
            document_line_id=line.id,
            legacy_import_row_id=source.id,
            import_batch_id=batch.id,
            item_name=item_name,
            item_code=ledger_item_code,
            wool_content=wool,
            color_code=ledger_color,
            dye_lot_no=ledger_lot,
            rolls_delta=rolls_delta,
            meters_delta=meter_delta,
            created_by=actor.id,
            updated_by=actor.id,
        )
    )
    balances[balance_key] = (balance_rolls + rolls_delta, balance_meters + meter_delta)
    report["ledger_entries"] += 1

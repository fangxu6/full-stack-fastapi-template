import hashlib
import uuid
from collections.abc import Collection
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

from pydantic import ValidationError
from sqlmodel import Session, select

from app.core.audit import (
    AUDIT_ACTOR_SESSION_KEY,
    bind_audit_actor,
    clear_audit_actor,
)
from app.core.excel import (
    ExcelIssue,
    ExcelValidationError,
)
from app.core.exceptions import BadRequestError, ConflictError
from app.models import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryImportBatch,
    LegacyImportRow,
    ProcessingUnit,
    ReceivingUnit,
    User,
)
from app.models.inventory import (
    InventoryDocumentType,
    InventoryMovementType,
)
from app.modules.inventory import documents, ledger, units
from app.modules.inventory.document_import_adapter import (
    DOCUMENT_WORKSHEET_NAME as _DOCUMENT_WORKSHEET_NAME,
)
from app.modules.inventory.document_import_adapter import (
    document_issue,
    read_document_workbook,
)
from app.modules.inventory.legacy_import_adapter import (
    LegacyImportRecord,
    read_legacy_workbooks,
)
from app.schemas.inventory import (
    InventoryDocumentCreate,
    InventoryDocumentExcelRow,
    InventoryExcelImportPublic,
    InventoryLineCreate,
    LegacyInventoryExcelImportPublic,
)

IMPORTER_VERSION = "inventory-xlsx-v2"
DOCUMENT_WORKSHEET_NAME = _DOCUMENT_WORKSHEET_NAME


def import_document_workbook(
    *,
    session: Session,
    content: bytes,
    allowed_document_types: Collection[InventoryDocumentType] | None = None,
) -> InventoryExcelImportPublic:
    groups, issues = read_document_workbook(
        content,
        allowed_document_types=allowed_document_types,
    )
    if issues:
        raise ExcelValidationError(issues)

    created_numbers: list[str] = []
    for group in groups:
        number = group.document_number
        first = cast(InventoryDocumentExcelRow, group.rows[0].value)
        try:
            processing_unit_id = units.resolve_active_unit_name(
                session=session,
                model=ProcessingUnit,
                name=first.processing_unit_name,
            )
        except BadRequestError as error:
            issues.append(
                document_issue(
                    group.rows[0], field_name="processing_unit_name", message=str(error)
                )
            )
            continue
        receiving_unit_id = None
        if first.receiving_unit_name:
            try:
                receiving_unit_id = units.resolve_active_unit_name(
                    session=session,
                    model=ReceivingUnit,
                    name=first.receiving_unit_name,
                )
            except BadRequestError as error:
                issues.append(
                    document_issue(
                        group.rows[0],
                        field_name="receiving_unit_name",
                        message=str(error),
                    )
                )
                continue
        try:
            document_in = InventoryDocumentCreate(
                document_type=first.document_type,
                business_date=first.business_date,
                processing_unit_id=processing_unit_id,
                receiving_unit_id=receiving_unit_id,
                document_number=number,
                remarks=first.remarks,
                lines=[
                    InventoryLineCreate(
                        item_name=value.item_name,
                        item_code=value.item_code,
                        wool_content=value.wool_content,
                        color_code=value.color_code,
                        dye_lot_no=value.dye_lot_no,
                        quantity_rolls=value.quantity_rolls,
                        quantity_meters=value.quantity_meters,
                    )
                    for row in group.rows
                    for value in [cast(InventoryDocumentExcelRow, row.value)]
                ],
            )
        except ValidationError as error:
            issues.append(
                document_issue(
                    group.rows[0], field_name="document_number", message=str(error)
                )
            )
            continue
        try:
            with session.begin_nested():
                documents.create_document(session=session, document_in=document_in)
        except (BadRequestError, ConflictError) as error:
            issues.append(
                document_issue(
                    group.rows[0], field_name="document_number", message=str(error)
                )
            )
            continue
        created_numbers.append(number)
    if issues:
        raise ExcelValidationError(issues)
    return InventoryExcelImportPublic(
        created_documents=len(created_numbers), document_numbers=created_numbers
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def import_legacy_workbooks(
    *,
    session: Session,
    raw_content: bytes,
    raw_filename: str,
    finished_content: bytes,
    finished_filename: str,
) -> LegacyInventoryExcelImportPublic:
    raw_hash, finished_hash = _sha256(raw_content), _sha256(finished_content)
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
    )
    session.add(batch)
    session.flush()
    report: dict[str, int] = {
        "source_rows": 0,
        "ledger_entries": 0,
        "requires_cleanup": 0,
        "reconciliation_openings": 0,
    }
    balances: ledger.LedgerBalances = {}
    records, issues = read_legacy_workbooks(
        raw_content=raw_content,
        raw_filename=raw_filename,
        finished_content=finished_content,
        finished_filename=finished_filename,
    )
    if issues:
        raise ExcelValidationError(issues)
    for record in records:
        report_before = report.copy()
        balances_before = balances.copy()
        try:
            with session.begin_nested():
                _persist_legacy_record(
                    session=session,
                    batch=batch,
                    record=record,
                    report=report,
                    balances=balances,
                )
        except BadRequestError as error:
            report.clear()
            report.update(report_before)
            balances.clear()
            balances.update(balances_before)
            issues.append(
                ExcelIssue(
                    worksheet=record.worksheet_name,
                    row=record.source_row_number,
                    column=None,
                    field=None,
                    message=str(error),
                )
            )
    if issues:
        raise ExcelValidationError(issues)
    batch.reconciliation_report = cast(dict[str, object], report)
    session.add(batch)
    session.flush()
    return LegacyInventoryExcelImportPublic(import_batch_id=batch.id, report=report)


def import_workbooks(
    *,
    session: Session,
    actor_user_id: uuid.UUID,
    raw_workbook: Path,
    finished_workbook: Path,
    dry_run: bool = False,
) -> dict[str, int]:
    actor = session.get(User, actor_user_id)
    if actor is None:
        raise BadRequestError("Import actor does not exist")
    if not actor.is_system_actor and not actor.is_active:
        raise BadRequestError(
            "Import actor must be active or a provisioned System Actor"
        )
    previous_actor_id = session.info.get(AUDIT_ACTOR_SESSION_KEY)
    bind_audit_actor(session=session, actor_id=actor_user_id)
    try:
        result = import_legacy_workbooks(
            session=session,
            raw_content=raw_workbook.read_bytes(),
            raw_filename=raw_workbook.name,
            finished_content=finished_workbook.read_bytes(),
            finished_filename=finished_workbook.name,
        )
        if dry_run:
            session.rollback()
        else:
            session.commit()
        return result.report
    except ExcelValidationError as error:
        session.rollback()
        raise BadRequestError(error.issues[0].message) from error
    except Exception:
        session.rollback()
        raise
    finally:
        if isinstance(previous_actor_id, uuid.UUID):
            bind_audit_actor(session=session, actor_id=previous_actor_id)
        else:
            clear_audit_actor(session=session)


def _persist_legacy_record(
    *,
    session: Session,
    batch: InventoryImportBatch,
    record: LegacyImportRecord,
    report: dict[str, int],
    balances: ledger.LedgerBalances,
) -> None:
    unit = cast(
        ProcessingUnit,
        _find_or_create_unit(session, ProcessingUnit, record.processing_unit_name),
    )
    source = LegacyImportRow(
        import_batch_id=batch.id,
        workbook_kind=record.workbook_kind,
        workbook_name=record.workbook_name,
        worksheet_name=record.worksheet_name,
        source_row_number=record.source_row_number,
        raw_cells=record.raw_cells,
        source_balance_snapshot=record.source_balance_snapshot,
        requires_cleanup=record.requires_cleanup,
    )
    session.add(source)
    session.flush()
    if record.requires_cleanup:
        report["requires_cleanup"] += 1
    for movement in record.movements:
        _write_legacy_movement(
            session=session,
            batch=batch,
            source=source,
            unit=unit,
            document_type=movement.document_type,
            item_name=record.item_name,
            item_code=record.item_code,
            wool=record.wool_content,
            color=record.color_code,
            lot=record.dye_lot_no,
            rolls=movement.rolls,
            meters=movement.meters,
            business_date=movement.business_date,
            number=movement.document_number,
            receiving_name=movement.receiving_unit_name,
            report=report,
            balances=balances,
        )
    report["source_rows"] += 1


def _find_or_create_unit(
    session: Session,
    model: type[ProcessingUnit] | type[ReceivingUnit],
    name: str,
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
    )
    session.add(unit)
    session.flush()
    return unit


def _write_legacy_movement(
    *,
    session: Session,
    batch: InventoryImportBatch,
    source: LegacyImportRow,
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
    balances: ledger.LedgerBalances,
) -> None:
    is_finished = document_type in {
        InventoryDocumentType.FINISHED_RECEIPT,
        InventoryDocumentType.FINISHED_SHIPMENT,
    }
    ledger_kind, movement_type, direction = ledger.movement_for_document_type(
        document_type, allow_finished_receipt=True
    )
    receiving = (
        _find_or_create_unit(
            session,
            ReceivingUnit,
            receiving_name or "历史未填写收货单位",
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
        quantity_rolls=rolls,
        quantity_meters=meters if is_finished and meters else None,
    )
    session.add(line)
    session.flush()
    ledger_item_code = item_code if not is_finished else None
    ledger_color = color if is_finished else None
    ledger_lot = lot if is_finished else None
    movement = ledger.LedgerMovement(
        ledger_kind=ledger_kind,
        movement_type=movement_type,
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
        rolls_delta=direction * rolls,
        meters_delta=direction * (meters or Decimal("0")),
    )
    balance_key = ledger.balance_key(movement)
    balance_rolls, balance_meters = balances.get(
        balance_key, (Decimal("0"), Decimal("0"))
    )
    opening_rolls = max(Decimal("0"), -(balance_rolls + movement.rolls_delta))
    opening_meters = max(Decimal("0"), -(balance_meters + movement.meters_delta))
    if opening_rolls or opening_meters:
        opening = ledger.LedgerMovement(
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
            rolls_delta=opening_rolls,
            meters_delta=opening_meters,
            reason="历史迁移对账期初",
        )
        ledger.append_movement(session=session, movement=opening)
        ledger.apply_balance(balances=balances, movement=opening)
        report["ledger_entries"] += 1
        report["reconciliation_openings"] += 1
    ledger.append_movement(session=session, movement=movement)
    ledger.apply_balance(balances=balances, movement=movement)
    report["ledger_entries"] += 1

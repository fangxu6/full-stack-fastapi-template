# SQLModel's type surface exposes ORM columns as their value types. Query
# expressions below are SQLAlchemy descriptors at runtime, which mypy cannot
# represent without a plugin; preserve checking for all other error families.
# mypy: disable-error-code="arg-type,attr-defined,call-overload,return-value,union-attr"

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy import desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryLedgerEntry,
    LegacyImportRow,
)
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
    ProcessingUnit,
    ReceivingUnit,
)
from app.schemas.inventory import (
    InventoryBalancePublic,
    InventoryBalancesPublic,
    InventoryDocumentCreate,
    InventoryDocumentPublic,
    InventoryDocumentsPublic,
    InventoryLedgerEntriesPublic,
    InventoryLedgerEntryPublic,
    InventoryLedgerExcelRow,
    InventoryLinePublic,
    InventorySuggestionsPublic,
    MasterUnitCreate,
    MasterUnitPublic,
    MasterUnitsPublic,
    MasterUnitUpdate,
)

UnitModel = ProcessingUnit | ReceivingUnit
LEGACY_PLACEHOLDERS = {"未填写品号", "未填写含毛量", "未分缸"}


def _normalized_name(name: str) -> str:
    return " ".join(name.split())


def _list_units(
    *,
    session: Session,
    model: type[ProcessingUnit] | type[ReceivingUnit],
    name: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> MasterUnitsPublic:
    filters = [model.deleted_at.is_(None)]  # ty:ignore[unresolved-attribute]
    normalized_name = _normalized_name(name) if name else ""
    if normalized_name:
        filters.append(
            model.normalized_name.ilike(f"%{normalized_name}%")  # ty:ignore[unresolved-attribute]
        )
    if is_active is not None:
        filters.append(model.is_active == is_active)
    count = session.exec(select(func.count()).select_from(model).where(*filters)).one()
    statement = (
        select(model)
        .where(*filters)
        .order_by(model.created_at.desc(), model.id.desc())  # ty:ignore[unresolved-attribute]
        .offset(skip)
        .limit(limit)
    )
    units = list(session.exec(statement).all())
    data = [MasterUnitPublic.model_validate(unit) for unit in units]
    return MasterUnitsPublic(data=data, count=count)


def list_processing_units(
    *,
    session: Session,
    name: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> MasterUnitsPublic:
    return _list_units(
        session=session,
        model=ProcessingUnit,
        name=name,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


def list_receiving_units(
    *,
    session: Session,
    name: str | None,
    is_active: bool | None,
    skip: int,
    limit: int,
) -> MasterUnitsPublic:
    return _list_units(
        session=session,
        model=ReceivingUnit,
        name=name,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


def _create_unit(
    *,
    session: Session,
    unit_in: MasterUnitCreate,
    model: type[ProcessingUnit] | type[ReceivingUnit],
) -> UnitModel:
    name = _normalized_name(unit_in.name)
    if not name:
        raise BadRequestError("Unit name cannot be blank")
    unit = model(name=name, normalized_name=name)
    session.add(unit)
    try:
        session.flush()
    except IntegrityError as err:
        raise ConflictError("Unit name already exists") from err
    session.refresh(unit)
    return unit


def create_processing_unit(
    *, session: Session, unit_in: MasterUnitCreate
) -> ProcessingUnit:
    return _create_unit(
        session=session,
        unit_in=unit_in,
        model=ProcessingUnit,
    )  # ty:ignore[invalid-return-type]


def create_receiving_unit(
    *, session: Session, unit_in: MasterUnitCreate
) -> ReceivingUnit:
    return _create_unit(
        session=session,
        unit_in=unit_in,
        model=ReceivingUnit,
    )  # ty:ignore[invalid-return-type]


def _update_unit(
    *,
    session: Session,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
    model: type[ProcessingUnit] | type[ReceivingUnit],
) -> UnitModel:
    unit = session.get(model, unit_id)
    if not unit or unit.deleted_at:
        raise NotFoundError("Unit not found")
    if unit_in.name is not None:
        name = _normalized_name(unit_in.name)
        if not name:
            raise BadRequestError("Unit name cannot be blank")
        unit.name = name
        unit.normalized_name = name
    if unit_in.is_active is not None:
        unit.is_active = unit_in.is_active
    session.add(unit)
    try:
        session.flush()
    except IntegrityError as err:
        raise ConflictError("Unit name already exists") from err
    session.refresh(unit)
    return unit


def update_processing_unit(
    *,
    session: Session,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> ProcessingUnit:
    return _update_unit(
        session=session,
        unit_id=unit_id,
        unit_in=unit_in,
        model=ProcessingUnit,
    )  # ty:ignore[invalid-return-type]


def update_receiving_unit(
    *,
    session: Session,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> ReceivingUnit:
    return _update_unit(
        session=session,
        unit_id=unit_id,
        unit_in=unit_in,
        model=ReceivingUnit,
    )  # ty:ignore[invalid-return-type]


def _require_active_units(
    *, session: Session, document_in: InventoryDocumentCreate
) -> None:
    processing = session.get(ProcessingUnit, document_in.processing_unit_id)
    if not processing or processing.deleted_at or not processing.is_active:
        raise BadRequestError("Processing unit is not active")
    if document_in.receiving_unit_id:
        receiving = session.get(ReceivingUnit, document_in.receiving_unit_id)
        if not receiving or receiving.deleted_at or not receiving.is_active:
            raise BadRequestError("Receiving unit is not active")


def resolve_active_unit_name(
    *,
    session: Session,
    model: type[ProcessingUnit] | type[ReceivingUnit],
    name: str,
) -> uuid.UUID:
    normalized_name = _normalized_name(name)
    unit = session.exec(
        select(model).where(
            model.normalized_name == normalized_name,
            model.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
            model.is_active.is_(True),  # ty:ignore[unresolved-attribute]
        )
    ).first()
    if not unit:
        raise BadRequestError("Unit does not exist or is not active")
    return cast(uuid.UUID, unit.id)


def _movement(
    document_type: InventoryDocumentType,
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
    }
    try:
        return mapping[document_type]
    except KeyError as err:
        raise BadRequestError("This document type cannot be created manually") from err


def _validate_line_for_type(document_type: InventoryDocumentType, line: object) -> None:
    values = (line.item_code, line.wool_content, line.color_code, line.dye_lot_no)  # ty:ignore[unresolved-attribute]
    if any(value in LEGACY_PLACEHOLDERS for value in values):
        raise BadRequestError(
            "Legacy placeholder values cannot be used in new documents"
        )
    if document_type in {
        InventoryDocumentType.RAW_RECEIPT,
        InventoryDocumentType.RAW_RETURN,
    }:
        if (
            not line.item_code  # ty:ignore[unresolved-attribute]
            or line.color_code  # ty:ignore[unresolved-attribute]
            or line.dye_lot_no  # ty:ignore[unresolved-attribute]
            or line.quantity_meters is not None  # ty:ignore[unresolved-attribute]
        ):
            raise BadRequestError(
                "Raw inventory lines require item code and rolls only"
            )
    elif not line.color_code or not line.dye_lot_no or line.quantity_meters is None:  # ty:ignore[unresolved-attribute]
        raise BadRequestError(
            "Finished shipment lines require color, lot, rolls, and meters"
        )


def _add_lines_and_ledgers(
    *,
    session: Session,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
) -> None:
    ledger_kind, movement_type, direction = _movement(document_in.document_type)
    for line_no, line_in in enumerate(document_in.lines, start=1):
        _validate_line_for_type(document_in.document_type, line_in)
        line = InventoryDocumentLine(
            document_id=document.id,
            line_no=line_no,
            **line_in.model_dump(),
        )
        session.add(line)
        session.flush()
        session.add(
            InventoryLedgerEntry(
                ledger_kind=ledger_kind,
                movement_type=movement_type,
                business_date=document.business_date,
                processing_unit_id=document.processing_unit_id,
                document_line_id=line.id,
                item_name=line.item_name,
                item_code=line.item_code,
                wool_content=line.wool_content,
                color_code=line.color_code,
                dye_lot_no=line.dye_lot_no,
                rolls_delta=direction * line.quantity_rolls,
                meters_delta=direction * (line.quantity_meters or Decimal("0")),
            )
        )


def _apply_document_values(
    *,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
) -> None:
    number = document_in.document_number.strip()
    if not number:
        raise BadRequestError("Document number cannot be blank")
    document.business_date = document_in.business_date
    document.processing_unit_id = document_in.processing_unit_id
    document.receiving_unit_id = document_in.receiving_unit_id
    document.document_number = number
    document.remarks = document_in.remarks


def create_document(
    *, session: Session, document_in: InventoryDocumentCreate
) -> InventoryDocumentPublic:
    try:
        _require_active_units(session=session, document_in=document_in)
        _movement(document_in.document_type)
        document = InventoryDocument(
            document_type=document_in.document_type,
            business_date=document_in.business_date,
            processing_unit_id=document_in.processing_unit_id,
            receiving_unit_id=document_in.receiving_unit_id,
            document_number=document_in.document_number.strip(),
            remarks=document_in.remarks,
        )
        session.add(document)
        session.flush()
        _add_lines_and_ledgers(
            session=session,
            document=document,
            document_in=document_in,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.flush()
    except BadRequestError, ConflictError:
        raise
    except IntegrityError as err:
        raise ConflictError("Document number already exists") from err
    return _document_public(session=session, document=document)


def get_document(
    *, session: Session, document_id: uuid.UUID
) -> InventoryDocumentPublic:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    return _document_public(session=session, document=document)


def list_documents(
    *,
    session: Session,
    skip: int,
    limit: int,
    document_type: InventoryDocumentType | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
    processing_unit_id: uuid.UUID | None = None,
    receiving_unit_id: uuid.UUID | None = None,
    document_number: str | None = None,
    include_deleted: bool = False,
) -> InventoryDocumentsPublic:
    filters: list[Any] = []
    if document_type:
        filters.append(InventoryDocument.document_type == document_type)
    if business_date_from:
        filters.append(InventoryDocument.business_date >= business_date_from)
    if business_date_to:
        filters.append(InventoryDocument.business_date <= business_date_to)
    if processing_unit_id:
        filters.append(InventoryDocument.processing_unit_id == processing_unit_id)
    if receiving_unit_id:
        filters.append(InventoryDocument.receiving_unit_id == receiving_unit_id)
    if document_number:
        filters.append(
            InventoryDocument.document_number.ilike(f"%{document_number.strip()}%")  # ty:ignore[unresolved-attribute]
        )
    if not include_deleted:
        filters.append(InventoryDocument.deleted_at.is_(None))  # ty:ignore[unresolved-attribute]
    count = session.exec(
        select(func.count()).select_from(InventoryDocument).where(*filters)
    ).one()
    documents = list(
        session.exec(
            select(InventoryDocument)
            .where(*filters)
            .order_by(
                desc(InventoryDocument.business_date),  # ty:ignore[invalid-argument-type]
                desc(InventoryDocument.id),  # ty:ignore[invalid-argument-type]
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    data = [
        _document_public(session=session, document=document) for document in documents
    ]
    return InventoryDocumentsPublic(data=data, count=count)


def update_document(
    *,
    session: Session,
    document_id: uuid.UUID,
    document_in: InventoryDocumentCreate,
) -> InventoryDocumentPublic:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.deleted_at:
        raise BadRequestError("Deleted inventory documents must be restored first")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be edited")
    if document.document_type != document_in.document_type:
        raise BadRequestError("Document type cannot be changed")
    original_processing_unit_id = document.processing_unit_id
    try:
        _require_active_units(session=session, document_in=document_in)
        _replace_document_lines(session=session, document=document)
        _apply_document_values(document=document, document_in=document_in)
        session.add(document)
        _add_lines_and_ledgers(
            session=session,
            document=document,
            document_in=document_in,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=original_processing_unit_id
        )
        if document.processing_unit_id != original_processing_unit_id:
            _reject_negative_balances(
                session=session, processing_unit_id=document.processing_unit_id
            )
        session.flush()
    except BadRequestError, ConflictError:
        raise
    except IntegrityError as err:
        raise ConflictError("Document number already exists") from err
    return _document_public(session=session, document=document)


def delete_document(*, session: Session, document_id: uuid.UUID) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be deleted")
    if document.deleted_at:
        return
    now = get_datetime_utc()
    document.deleted_at = now
    session.add(document)
    _set_document_ledger_deleted(session=session, document=document, deleted_at=now)
    session.flush()


def restore_document(*, session: Session, document_id: uuid.UUID) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be restored")
    try:
        document.deleted_at = None
        _set_document_ledger_deleted(
            session=session,
            document=document,
            deleted_at=None,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.add(document)
        session.flush()
    except ConflictError:
        raise


def _replace_document_lines(*, session: Session, document: InventoryDocument) -> None:
    lines = list(
        session.exec(
            select(InventoryDocumentLine).where(
                InventoryDocumentLine.document_id == document.id,
            )
        ).all()
    )
    if not lines:
        return
    line_ids = [line.id for line in lines]
    ledgers = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id.in_(line_ids)  # ty:ignore[unresolved-attribute]
        )
    ).all()
    for ledger in ledgers:
        session.delete(ledger)
    session.flush()
    for line in lines:
        session.delete(line)
    session.flush()


def _set_document_ledger_deleted(
    *,
    session: Session,
    document: InventoryDocument,
    deleted_at: datetime | None,
) -> None:
    line_ids = session.exec(
        select(InventoryDocumentLine.id).where(
            InventoryDocumentLine.document_id == document.id
        )
    ).all()
    if not line_ids:
        return
    ledgers = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.document_line_id.in_(line_ids)  # ty:ignore[unresolved-attribute]
        )
    ).all()
    for ledger in ledgers:
        ledger.deleted_at = deleted_at
        session.add(ledger)


def _document_public(
    *, session: Session, document: InventoryDocument
) -> InventoryDocumentPublic:
    lines = list(
        session.exec(
            select(InventoryDocumentLine)
            .where(
                InventoryDocumentLine.document_id == document.id,
                InventoryDocumentLine.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
            )
            .order_by(InventoryDocumentLine.line_no)  # ty:ignore[invalid-argument-type]
        ).all()
    )
    return InventoryDocumentPublic(
        id=document.id,
        document_type=document.document_type,
        business_date=document.business_date,
        processing_unit_id=document.processing_unit_id,
        receiving_unit_id=document.receiving_unit_id,
        document_number=document.document_number,
        remarks=document.remarks,
        deleted_at=document.deleted_at,
        lines=[
            InventoryLinePublic(
                id=line.id,
                line_no=line.line_no,
                item_name=line.item_name,
                item_code=line.item_code,
                wool_content=line.wool_content,
                color_code=line.color_code,
                dye_lot_no=line.dye_lot_no,
                quantity_rolls=line.quantity_rolls,
                quantity_meters=line.quantity_meters,
            )
            for line in lines
        ],
    )


def _reject_negative_balances(
    *, session: Session, processing_unit_id: uuid.UUID
) -> None:
    entries = session.exec(
        select(InventoryLedgerEntry).where(
            InventoryLedgerEntry.processing_unit_id == processing_unit_id,
            InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
        )
    ).all()
    balances: dict[tuple[object, ...], tuple[Decimal, Decimal]] = {}
    for entry in entries:
        key = (
            entry.ledger_kind,
            entry.item_name,
            entry.item_code,
            entry.wool_content,
            entry.color_code,
            entry.dye_lot_no,
        )
        rolls, meters = balances.get(key, (Decimal("0"), Decimal("0")))
        balances[key] = (rolls + entry.rolls_delta, meters + entry.meters_delta)
    if any(rolls < 0 or meters < 0 for rolls, meters in balances.values()):
        raise ConflictError("Insufficient inventory")


def list_balances(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    skip: int,
    limit: int | None,
    processing_unit_id: uuid.UUID | None = None,
    item_name: str | None = None,
    business_date_to: date | None = None,
) -> InventoryBalancesPublic:
    filters: list[Any] = [
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    ]
    if processing_unit_id:
        filters.append(InventoryLedgerEntry.processing_unit_id == processing_unit_id)
    if item_name:
        filters.append(
            InventoryLedgerEntry.item_name.ilike(f"%{item_name}%")  # ty:ignore[unresolved-attribute]
        )
    if business_date_to:
        filters.append(InventoryLedgerEntry.business_date <= business_date_to)
    balance_columns = (
        InventoryLedgerEntry.processing_unit_id,
        InventoryLedgerEntry.item_name,
        InventoryLedgerEntry.item_code,
        InventoryLedgerEntry.wool_content,
        InventoryLedgerEntry.color_code,
        InventoryLedgerEntry.dye_lot_no,
    )
    rolls_balance = func.sum(InventoryLedgerEntry.rolls_delta).label("rolls_balance")
    meters_balance = func.sum(InventoryLedgerEntry.meters_delta).label("meters_balance")
    aggregate = (
        select(  # ty:ignore[no-matching-overload]
            InventoryLedgerEntry.processing_unit_id,
            InventoryLedgerEntry.item_name,
            InventoryLedgerEntry.item_code,
            InventoryLedgerEntry.wool_content,
            InventoryLedgerEntry.color_code,
            InventoryLedgerEntry.dye_lot_no,
            rolls_balance,
            meters_balance,
        )
        .where(*filters)
        .group_by(*balance_columns)
        .having(
            or_(
                func.sum(InventoryLedgerEntry.rolls_delta) != 0,
                func.sum(InventoryLedgerEntry.meters_delta) != 0,
            )
        )
    )
    count = session.exec(select(func.count()).select_from(aggregate.subquery())).one()
    statement = aggregate.order_by(*balance_columns)
    if limit is not None:
        statement = statement.offset(skip).limit(limit)
    rows = list(session.exec(statement).all())
    return InventoryBalancesPublic(
        data=[
            InventoryBalancePublic(
                processing_unit_id=row[0],
                item_name=row[1],
                item_code=row[2],
                wool_content=row[3],
                color_code=row[4],
                dye_lot_no=row[5],
                rolls_balance=row[6],
                meters_balance=row[7],
            )
            for row in rows
        ],
        count=count,
    )


def list_balances_as_of(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID,
    business_date: date,
) -> list[InventoryBalancePublic]:
    return list_balances(
        session=session,
        ledger_kind=ledger_kind,
        skip=0,
        limit=None,
        processing_unit_id=processing_unit_id,
        business_date_to=business_date,
    ).data


def list_ledger_entries(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID,
    item_name: str,
    wool_content: str,
    skip: int,
    limit: int,
    item_code: str | None = None,
    color_code: str | None = None,
    dye_lot_no: str | None = None,
) -> InventoryLedgerEntriesPublic:
    filters: list[Any] = [
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.processing_unit_id == processing_unit_id,
        InventoryLedgerEntry.item_name == item_name,
        InventoryLedgerEntry.wool_content == wool_content,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    ]
    for column, value in (
        (InventoryLedgerEntry.item_code, item_code),
        (InventoryLedgerEntry.color_code, color_code),
        (InventoryLedgerEntry.dye_lot_no, dye_lot_no),
    ):
        filters.append(
            column.is_(None) if value is None else column == value  # ty:ignore[unresolved-attribute]
        )
    count = session.exec(
        select(func.count()).select_from(InventoryLedgerEntry).where(*filters)
    ).one()
    entries = list(
        session.exec(
            select(InventoryLedgerEntry)
            .where(*filters)
            .order_by(InventoryLedgerEntry.business_date, InventoryLedgerEntry.id)  # ty:ignore[invalid-argument-type]
            .offset(skip)
            .limit(limit)
        ).all()
    )
    data = [
        InventoryLedgerEntryPublic(
            id=entry.id,
            ledger_kind=entry.ledger_kind,
            movement_type=entry.movement_type,
            business_date=entry.business_date,
            processing_unit_id=entry.processing_unit_id,
            document_line_id=entry.document_line_id,
            item_name=entry.item_name,
            item_code=entry.item_code,
            wool_content=entry.wool_content,
            color_code=entry.color_code,
            dye_lot_no=entry.dye_lot_no,
            rolls_delta=entry.rolls_delta,
            meters_delta=entry.meters_delta,
            reason=entry.reason,
        )
        for entry in entries
    ]
    return InventoryLedgerEntriesPublic(data=data, count=count)


def list_ledger_excel_rows(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
) -> list[InventoryLedgerExcelRow]:
    filters: list[Any] = [
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    ]
    if processing_unit_id:
        filters.append(InventoryLedgerEntry.processing_unit_id == processing_unit_id)
    if business_date_from:
        filters.append(InventoryLedgerEntry.business_date >= business_date_from)
    if business_date_to:
        filters.append(InventoryLedgerEntry.business_date <= business_date_to)
    statement = (
        select(
            InventoryLedgerEntry,
            InventoryDocument,
            ProcessingUnit,
            LegacyImportRow,
        )
        .join(
            ProcessingUnit,
            ProcessingUnit.id == InventoryLedgerEntry.processing_unit_id,  # ty:ignore[invalid-argument-type]
        )
        .outerjoin(
            InventoryDocumentLine,
            InventoryDocumentLine.id == InventoryLedgerEntry.document_line_id,  # ty:ignore[invalid-argument-type]
        )
        .outerjoin(
            InventoryDocument,
            InventoryDocument.id == InventoryDocumentLine.document_id,  # ty:ignore[invalid-argument-type]
        )
        .outerjoin(
            LegacyImportRow,
            LegacyImportRow.id == InventoryLedgerEntry.legacy_import_row_id,  # ty:ignore[invalid-argument-type]
        )
        .where(*filters)
        .order_by(
            InventoryLedgerEntry.business_date,  # ty:ignore[invalid-argument-type]
            InventoryLedgerEntry.id,  # ty:ignore[invalid-argument-type]
        )
    )
    movement_labels = {
        InventoryMovementType.RAW_RECEIPT: "入库",
        InventoryMovementType.FINISHED_RECEIPT: "入库",
        InventoryMovementType.RAW_RETURN: "出库",
        InventoryMovementType.FINISHED_SHIPMENT: "出库",
        InventoryMovementType.MIGRATION_RECONCILIATION_OPENING: "期初调整",
    }
    return [
        InventoryLedgerExcelRow.model_validate(
            {
                "business_date": entry.business_date,
                "movement_type": movement_labels[entry.movement_type],
                "document_number": document.document_number if document else None,
                "unit_name": unit.name,
                "item_name": entry.item_name,
                "item_code": entry.item_code,
                "wool_content": entry.wool_content,
                "color_code": entry.color_code,
                "dye_lot_no": entry.dye_lot_no,
                "rolls_delta": entry.rolls_delta,
                "meters_delta": entry.meters_delta,
                "remarks": "；".join(
                    part
                    for part in (
                        document.remarks if document else None,
                        entry.reason,
                        (
                            f"历史来源：{source.workbook_name}/{source.worksheet_name}"
                            f" 第{source.source_row_number}行"
                            if source
                            else None
                        ),
                    )
                    if part
                )
                or None,
            }
        )
        for entry, document, unit, source in session.exec(statement).all()
    ]


def list_suggestions(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    field: str,
    query: str | None = None,
) -> InventorySuggestionsPublic:
    columns = {
        "item_name": InventoryLedgerEntry.item_name,
        "item_code": InventoryLedgerEntry.item_code,
        "wool_content": InventoryLedgerEntry.wool_content,
        "color_code": InventoryLedgerEntry.color_code,
        "dye_lot_no": InventoryLedgerEntry.dye_lot_no,
    }
    column = columns.get(field)
    if column is None:
        raise BadRequestError("Unsupported suggestion field")
    statement = select(column).where(
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
        column.is_not(None),  # ty:ignore[unresolved-attribute]
    )
    if query:
        statement = statement.where(column.ilike(f"%{query.strip()}%"))  # ty:ignore[unresolved-attribute]
    values = sorted({value for value in session.exec(statement).all() if value})
    return InventorySuggestionsPublic(data=values[:50])

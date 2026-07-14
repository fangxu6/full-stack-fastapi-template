# SQLModel's type surface exposes ORM columns as their value types. Query
# expressions below are SQLAlchemy descriptors at runtime, which mypy cannot
# represent without a plugin; preserve checking for all other error families.
# mypy: disable-error-code="arg-type,attr-defined,return-value,union-attr"

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models import InventoryDocument, InventoryDocumentLine, InventoryLedgerEntry
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
    ProcessingUnit,
    ReceivingUnit,
)
from app.models.user import User
from app.schemas.inventory import (
    InventoryBalancePublic,
    InventoryBalancesPublic,
    InventoryDocumentCreate,
    InventoryDocumentPublic,
    InventoryDocumentsPublic,
    InventoryLedgerEntriesPublic,
    InventoryLedgerEntryPublic,
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


def _audit(current_user: User) -> dict[str, object]:
    return {"created_by": current_user.id, "updated_by": current_user.id}


def _list_units(
    *, session: Session, model: type[ProcessingUnit] | type[ReceivingUnit]
) -> MasterUnitsPublic:
    units = list(session.exec(select(model).where(model.deleted_at.is_(None))).all())  # ty:ignore[unresolved-attribute]
    data = [MasterUnitPublic.model_validate(unit) for unit in units]
    return MasterUnitsPublic(data=data, count=len(data))


def list_processing_units(*, session: Session) -> MasterUnitsPublic:
    return _list_units(session=session, model=ProcessingUnit)


def list_receiving_units(*, session: Session) -> MasterUnitsPublic:
    return _list_units(session=session, model=ReceivingUnit)


def _create_unit(
    *,
    session: Session,
    current_user: User,
    unit_in: MasterUnitCreate,
    model: type[ProcessingUnit] | type[ReceivingUnit],
) -> UnitModel:
    name = _normalized_name(unit_in.name)
    if not name:
        raise BadRequestError("Unit name cannot be blank")
    unit = model(name=name, normalized_name=name, **_audit(current_user))  # ty:ignore[invalid-argument-type]
    session.add(unit)
    try:
        session.commit()
    except IntegrityError as err:
        session.rollback()
        raise ConflictError("Unit name already exists") from err
    session.refresh(unit)
    return unit


def create_processing_unit(
    *, session: Session, current_user: User, unit_in: MasterUnitCreate
) -> ProcessingUnit:
    return _create_unit(
        session=session,
        current_user=current_user,
        unit_in=unit_in,
        model=ProcessingUnit,
    )  # ty:ignore[invalid-return-type]


def create_receiving_unit(
    *, session: Session, current_user: User, unit_in: MasterUnitCreate
) -> ReceivingUnit:
    return _create_unit(
        session=session,
        current_user=current_user,
        unit_in=unit_in,
        model=ReceivingUnit,
    )  # ty:ignore[invalid-return-type]


def _update_unit(
    *,
    session: Session,
    current_user: User,
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
    unit.updated_at = get_datetime_utc()
    unit.updated_by = current_user.id
    session.add(unit)
    try:
        session.commit()
    except IntegrityError as err:
        session.rollback()
        raise ConflictError("Unit name already exists") from err
    session.refresh(unit)
    return unit


def update_processing_unit(
    *,
    session: Session,
    current_user: User,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> ProcessingUnit:
    return _update_unit(
        session=session,
        current_user=current_user,
        unit_id=unit_id,
        unit_in=unit_in,
        model=ProcessingUnit,
    )  # ty:ignore[invalid-return-type]


def update_receiving_unit(
    *,
    session: Session,
    current_user: User,
    unit_id: uuid.UUID,
    unit_in: MasterUnitUpdate,
) -> ReceivingUnit:
    return _update_unit(
        session=session,
        current_user=current_user,
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


def _movement(
    document_type: InventoryDocumentType,
) -> tuple[InventoryLedgerKind, InventoryMovementType, int]:
    mapping = {
        InventoryDocumentType.RAW_RECEIPT: (
            InventoryLedgerKind.RAW,
            InventoryMovementType.RAW_RECEIPT,
            1,
        ),
        InventoryDocumentType.RAW_RETURN: (
            InventoryLedgerKind.RAW,
            InventoryMovementType.RAW_RETURN,
            -1,
        ),
        InventoryDocumentType.FINISHED_SHIPMENT: (
            InventoryLedgerKind.FINISHED,
            InventoryMovementType.FINISHED_SHIPMENT,
            -1,
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
    current_user: User,
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
            **_audit(current_user),
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
                **_audit(current_user),  # ty:ignore[invalid-argument-type]
            )
        )


def _apply_document_values(
    *,
    document: InventoryDocument,
    document_in: InventoryDocumentCreate,
    current_user: User,
) -> None:
    number = document_in.document_number.strip()
    if not number:
        raise BadRequestError("Document number cannot be blank")
    document.business_date = document_in.business_date
    document.processing_unit_id = document_in.processing_unit_id
    document.receiving_unit_id = document_in.receiving_unit_id
    document.document_number = number
    document.remarks = document_in.remarks
    document.updated_at = get_datetime_utc()
    document.updated_by = current_user.id


def create_document(
    *, session: Session, current_user: User, document_in: InventoryDocumentCreate
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
            **_audit(current_user),  # ty:ignore[invalid-argument-type]
        )
        session.add(document)
        session.flush()
        _add_lines_and_ledgers(
            session=session,
            current_user=current_user,
            document=document,
            document_in=document_in,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.commit()
    except BadRequestError, ConflictError:
        session.rollback()
        raise
    except IntegrityError as err:
        session.rollback()
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
    document_type: InventoryDocumentType | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
    processing_unit_id: uuid.UUID | None = None,
    receiving_unit_id: uuid.UUID | None = None,
    document_number: str | None = None,
    include_deleted: bool = False,
) -> InventoryDocumentsPublic:
    statement = select(InventoryDocument)
    if document_type:
        statement = statement.where(InventoryDocument.document_type == document_type)
    if business_date_from:
        statement = statement.where(
            InventoryDocument.business_date >= business_date_from
        )
    if business_date_to:
        statement = statement.where(InventoryDocument.business_date <= business_date_to)
    if processing_unit_id:
        statement = statement.where(
            InventoryDocument.processing_unit_id == processing_unit_id
        )
    if receiving_unit_id:
        statement = statement.where(
            InventoryDocument.receiving_unit_id == receiving_unit_id
        )
    if document_number:
        statement = statement.where(
            InventoryDocument.document_number.ilike(f"%{document_number.strip()}%")  # ty:ignore[unresolved-attribute]
        )
    if not include_deleted:
        statement = statement.where(InventoryDocument.deleted_at.is_(None))  # ty:ignore[unresolved-attribute]
    documents = list(
        session.exec(statement.order_by(InventoryDocument.business_date.desc())).all()  # ty:ignore[unresolved-attribute]
    )
    data = [
        _document_public(session=session, document=document) for document in documents
    ]
    return InventoryDocumentsPublic(data=data, count=len(data))


def update_document(
    *,
    session: Session,
    current_user: User,
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
        _apply_document_values(
            document=document, document_in=document_in, current_user=current_user
        )
        session.add(document)
        _add_lines_and_ledgers(
            session=session,
            current_user=current_user,
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
        session.commit()
    except BadRequestError, ConflictError:
        session.rollback()
        raise
    except IntegrityError as err:
        session.rollback()
        raise ConflictError("Document number already exists") from err
    return _document_public(session=session, document=document)


def delete_document(
    *, session: Session, current_user: User, document_id: uuid.UUID
) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be deleted")
    if document.deleted_at:
        return
    now = get_datetime_utc()
    document.deleted_at = now
    document.updated_at = now
    document.updated_by = current_user.id
    session.add(document)
    _set_document_ledger_deleted(
        session=session, document=document, deleted_at=now, current_user=current_user
    )
    session.commit()


def restore_document(
    *, session: Session, current_user: User, document_id: uuid.UUID
) -> None:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    if document.is_legacy:
        raise BadRequestError("Legacy inventory documents cannot be restored")
    try:
        now = get_datetime_utc()
        document.deleted_at = None
        document.updated_at = now
        document.updated_by = current_user.id
        _set_document_ledger_deleted(
            session=session,
            document=document,
            deleted_at=None,
            current_user=current_user,
        )
        _reject_negative_balances(
            session=session, processing_unit_id=document.processing_unit_id
        )
        session.add(document)
        session.commit()
    except ConflictError:
        session.rollback()
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
    current_user: User,
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
    now = get_datetime_utc()
    for ledger in ledgers:
        ledger.deleted_at = deleted_at
        ledger.updated_at = now
        ledger.updated_by = current_user.id
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
    balances: dict[tuple[object, ...], tuple[int, Decimal]] = {}
    for entry in entries:
        key = (
            entry.ledger_kind,
            entry.item_name,
            entry.item_code,
            entry.wool_content,
            entry.color_code,
            entry.dye_lot_no,
        )
        rolls, meters = balances.get(key, (0, Decimal("0")))
        balances[key] = (rolls + entry.rolls_delta, meters + entry.meters_delta)
    if any(rolls < 0 or meters < 0 for rolls, meters in balances.values()):
        raise ConflictError("Insufficient inventory")


def list_balances(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID | None = None,
    item_name: str | None = None,
) -> InventoryBalancesPublic:
    statement = select(InventoryLedgerEntry).where(
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    )
    if processing_unit_id:
        statement = statement.where(
            InventoryLedgerEntry.processing_unit_id == processing_unit_id
        )
    if item_name:
        statement = statement.where(
            InventoryLedgerEntry.item_name.ilike(f"%{item_name}%")  # ty:ignore[unresolved-attribute]
        )
    entries = session.exec(statement).all()
    balances: dict[tuple[object, ...], tuple[int, Decimal]] = {}
    for entry in entries:
        key = (
            entry.processing_unit_id,
            entry.item_name,
            entry.item_code,
            entry.wool_content,
            entry.color_code,
            entry.dye_lot_no,
        )
        rolls, meters = balances.get(key, (0, Decimal("0")))
        balances[key] = (rolls + entry.rolls_delta, meters + entry.meters_delta)
    return InventoryBalancesPublic(
        data=[
            InventoryBalancePublic(
                processing_unit_id=key[0],  # ty:ignore[invalid-argument-type]
                item_name=key[1],  # ty:ignore[invalid-argument-type]
                item_code=key[2],  # ty:ignore[invalid-argument-type]
                wool_content=key[3],  # ty:ignore[invalid-argument-type]
                color_code=key[4],  # ty:ignore[invalid-argument-type]
                dye_lot_no=key[5],  # ty:ignore[invalid-argument-type]
                rolls_balance=value[0],
                meters_balance=value[1],
            )
            for key, value in balances.items()
            if value[0] or value[1]
        ]
    )


def list_ledger_entries(
    *,
    session: Session,
    ledger_kind: InventoryLedgerKind,
    processing_unit_id: uuid.UUID,
    item_name: str,
    wool_content: str,
    item_code: str | None = None,
    color_code: str | None = None,
    dye_lot_no: str | None = None,
) -> InventoryLedgerEntriesPublic:
    statement = select(InventoryLedgerEntry).where(
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.processing_unit_id == processing_unit_id,
        InventoryLedgerEntry.item_name == item_name,
        InventoryLedgerEntry.wool_content == wool_content,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    )
    for column, value in (
        (InventoryLedgerEntry.item_code, item_code),
        (InventoryLedgerEntry.color_code, color_code),
        (InventoryLedgerEntry.dye_lot_no, dye_lot_no),
    ):
        statement = statement.where(
            column.is_(None) if value is None else column == value  # ty:ignore[unresolved-attribute]
        )
    entries = list(
        session.exec(
            statement.order_by(InventoryLedgerEntry.business_date)  # ty:ignore[invalid-argument-type]
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
    return InventoryLedgerEntriesPublic(data=data, count=len(data))


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

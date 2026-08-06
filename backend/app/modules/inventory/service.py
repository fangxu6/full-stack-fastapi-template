# SQLModel's type surface exposes ORM columns as their value types. Query
# expressions below are SQLAlchemy descriptors at runtime, which mypy cannot
# represent without a plugin; preserve checking for all other error families.
# mypy: disable-error-code="arg-type,attr-defined,call-overload,return-value,union-attr"

import uuid
from datetime import date
from typing import Any

from sqlalchemy import desc, func, or_
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, NotFoundError
from app.models import (
    InventoryDocument,
    InventoryDocumentLine,
    InventoryLedgerEntry,
    LegacyImportRow,
)
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
    ProcessingUnit,
)
from app.modules.inventory.documents import document_public
from app.schemas.inventory import (
    InventoryBalancePublic,
    InventoryBalancesPublic,
    InventoryDocumentPublic,
    InventoryDocumentsPublic,
    InventoryLedgerEntriesPublic,
    InventoryLedgerEntryPublic,
    InventoryLedgerExcelRow,
    InventorySuggestionsPublic,
)


def get_document(
    *, session: Session, document_id: uuid.UUID
) -> InventoryDocumentPublic:
    document = session.get(InventoryDocument, document_id)
    if not document:
        raise NotFoundError("Inventory document not found")
    return document_public(session=session, document=document)


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
        document_public(session=session, document=document) for document in documents
    ]
    return InventoryDocumentsPublic(data=data, count=count)


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
    receiving_unit_id: uuid.UUID | None = None,
    document_number: str | None = None,
    business_date_from: date | None = None,
    business_date_to: date | None = None,
) -> list[InventoryLedgerExcelRow]:
    filters: list[Any] = [
        InventoryLedgerEntry.ledger_kind == ledger_kind,
        InventoryLedgerEntry.deleted_at.is_(None),  # ty:ignore[unresolved-attribute]
    ]
    if processing_unit_id:
        filters.append(InventoryLedgerEntry.processing_unit_id == processing_unit_id)
    if receiving_unit_id:
        filters.append(InventoryDocument.receiving_unit_id == receiving_unit_id)
    if document_number:
        filters.append(
            InventoryDocument.document_number.ilike(f"%{document_number.strip()}%")  # ty:ignore[unresolved-attribute]
        )
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

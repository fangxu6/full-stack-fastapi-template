# SQLModel's type surface exposes ORM columns as their value types. Query
# expressions below are SQLAlchemy descriptors at runtime, which mypy cannot
# represent without a plugin; preserve checking for all other error families.
# mypy: disable-error-code="arg-type,attr-defined,call-overload,return-value,union-attr"

import uuid
from typing import cast

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.inventory import ProcessingUnit, ReceivingUnit
from app.schemas.inventory import (
    InventoryDocumentCreate,
    MasterUnitCreate,
    MasterUnitPublic,
    MasterUnitsPublic,
    MasterUnitUpdate,
)

UnitModel = ProcessingUnit | ReceivingUnit


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


def require_active_units(
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

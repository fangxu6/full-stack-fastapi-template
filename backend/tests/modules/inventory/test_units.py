from datetime import date

import pytest
from sqlmodel import Session

from app.core.audit import bind_audit_actor
from app.core.exceptions import BadRequestError
from app.models.inventory import InventoryDocumentType, ProcessingUnit
from app.modules.inventory.units import (
    create_processing_unit,
    list_processing_units,
    require_active_units,
    resolve_active_unit_name,
    update_processing_unit,
)
from app.schemas.inventory import (
    InventoryDocumentCreate,
    MasterUnitCreate,
    MasterUnitUpdate,
)
from tests.utils.user import create_random_user


def test_units_normalize_list_update_and_resolve_active_names(db: Session) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)

    unit = create_processing_unit(
        session=db, unit_in=MasterUnitCreate(name="  Unit   Alpha  ")
    )
    db.commit()

    assert unit.name == "Unit Alpha"
    assert (
        resolve_active_unit_name(
            session=db,
            model=ProcessingUnit,
            name=" Unit   Alpha ",
        )
        == unit.id
    )

    updated = update_processing_unit(
        session=db,
        unit_id=unit.id,
        unit_in=MasterUnitUpdate(name="Unit Beta", is_active=False),
    )
    db.commit()

    listed = list_processing_units(
        session=db,
        name="unit beta",
        is_active=False,
        skip=0,
        limit=20,
    )
    assert updated.name == "Unit Beta"
    assert listed.count == 1
    assert listed.data[0].id == unit.id

    with pytest.raises(BadRequestError, match="does not exist or is not active"):
        resolve_active_unit_name(
            session=db,
            model=ProcessingUnit,
            name="unit beta",
        )


def test_require_active_units_rejects_inactive_processing_unit(db: Session) -> None:
    actor = create_random_user(db)
    bind_audit_actor(session=db, actor_id=actor.id)
    unit = create_processing_unit(
        session=db, unit_in=MasterUnitCreate(name="Inactive unit")
    )
    db.commit()
    update_processing_unit(
        session=db,
        unit_id=unit.id,
        unit_in=MasterUnitUpdate(is_active=False),
    )
    db.commit()

    document_in = InventoryDocumentCreate(
        document_type=InventoryDocumentType.RAW_RECEIPT,
        business_date=date(2026, 8, 6),
        processing_unit_id=unit.id,
        document_number="INACTIVE-UNIT",
        lines=[
            {
                "item_name": "Raw fabric",
                "item_code": "RAW-001",
                "wool_content": "100% wool",
                "quantity_rolls": 1,
            }
        ],
    )

    with pytest.raises(BadRequestError, match="Processing unit is not active"):
        require_active_units(session=db, document_in=document_in)

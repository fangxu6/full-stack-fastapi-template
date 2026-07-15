import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from app import crud, services
from app.core.db import engine
from app.models import Item
from app.schemas.item import ItemCreate, ItemUpdate
from tests.utils.item import create_random_item
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_create_item_requires_explicit_commit(db: Session) -> None:
    user = create_random_user(db)
    assert user.id is not None

    item_in = ItemCreate(
        title=random_lower_string(),
        description=random_lower_string(),
    )
    item = crud.create_item(session=db, item_in=item_in, owner_id=user.id)

    assert item.title == item_in.title
    assert item.description == item_in.description
    assert item.owner_id == user.id

    with Session(engine) as verification_session:
        assert (
            crud.get_item_by_id(session=verification_session, item_id=item.id) is None
        )

    db.commit()

    with Session(engine) as verification_session:
        assert (
            crud.get_item_by_id(session=verification_session, item_id=item.id)
            is not None
        )


def test_module_service_create_item_commits(db: Session) -> None:
    user = create_random_user(db)
    assert user.id is not None

    item_in = ItemCreate(
        title=random_lower_string(),
        description=random_lower_string(),
    )

    item = services.item.create_item(session=db, current_user=user, item_in=item_in)

    with Session(engine) as verification_session:
        db_item = crud.get_item_by_id(session=verification_session, item_id=item.id)
        assert db_item is not None
        assert db_item.title == item_in.title


def test_get_item_by_id(db: Session) -> None:
    item = create_random_item(db)

    db_item = crud.get_item_by_id(session=db, item_id=item.id)

    assert db_item is not None
    assert db_item.id == item.id
    assert db_item.owner_id == item.owner_id


def test_get_items_by_owner(db: Session) -> None:
    owned_item = create_random_item(db)
    other_item = create_random_item(db)

    items = crud.get_items(session=db, owner_id=owned_item.owner_id)
    item_ids = {item.id for item in items}

    assert owned_item.id in item_ids
    assert other_item.id not in item_ids
    assert crud.count_items(session=db, owner_id=owned_item.owner_id) == len(items)


def test_get_items_uses_id_as_stable_created_at_tie_breaker(db: Session) -> None:
    user = create_random_user(db)
    assert user.id is not None

    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    lower_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    higher_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    db.add_all(
        [
            Item(
                id=lower_id,
                title="lower-id",
                owner_id=user.id,
                created_at=created_at,
            ),
            Item(
                id=higher_id,
                title="higher-id",
                owner_id=user.id,
                created_at=created_at,
            ),
        ]
    )
    db.commit()

    items = crud.get_items(session=db, owner_id=user.id)

    assert [item.id for item in items] == [higher_id, lower_id]


def test_update_item(db: Session) -> None:
    item = create_random_item(db)
    item_in = ItemUpdate(
        title="updated-title",
        description="updated-description",
    )

    updated_item = crud.update_item(session=db, db_item=item, item_in=item_in)

    assert updated_item.title == item_in.title
    assert updated_item.description == item_in.description

    with Session(engine) as verification_session:
        db_item = crud.get_item_by_id(session=verification_session, item_id=item.id)
        assert db_item is not None
        assert db_item.title != item_in.title

    db.commit()

    with Session(engine) as verification_session:
        db_item = crud.get_item_by_id(session=verification_session, item_id=item.id)
        assert db_item is not None
        assert db_item.title == item_in.title


def test_delete_item_requires_explicit_commit(db: Session) -> None:
    item = create_random_item(db)

    crud.delete_item(session=db, db_item=item)

    assert crud.get_item_by_id(session=db, item_id=item.id) is None

    with Session(engine) as verification_session:
        assert (
            crud.get_item_by_id(session=verification_session, item_id=item.id)
            is not None
        )

    db.commit()

    with Session(engine) as verification_session:
        assert (
            crud.get_item_by_id(session=verification_session, item_id=item.id) is None
        )


def test_get_item_by_id_missing(db: Session) -> None:
    assert crud.get_item_by_id(session=db, item_id=uuid.uuid4()) is None

import uuid

from sqlmodel import Session

from app import crud
from app.schemas.item import ItemCreate, ItemUpdate
from tests.utils.item import create_random_item
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_create_item(db: Session) -> None:
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


def test_update_item(db: Session) -> None:
    item = create_random_item(db)
    item_in = ItemUpdate(
        title="updated-title",
        description="updated-description",
    )

    updated_item = crud.update_item(session=db, db_item=item, item_in=item_in)

    assert updated_item.title == item_in.title
    assert updated_item.description == item_in.description


def test_delete_item(db: Session) -> None:
    item = create_random_item(db)

    crud.delete_item(session=db, db_item=item)

    assert crud.get_item_by_id(session=db, item_id=item.id) is None


def test_get_item_by_id_missing(db: Session) -> None:
    assert crud.get_item_by_id(session=db, item_id=uuid.uuid4()) is None

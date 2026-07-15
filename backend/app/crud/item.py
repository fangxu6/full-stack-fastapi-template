import uuid

from sqlmodel import Session, col, delete, func, select

from app.models import Item
from app.schemas.item import ItemCreate, ItemUpdate


def count_items(*, session: Session, owner_id: uuid.UUID | None = None) -> int:
    statement = select(func.count()).select_from(Item)
    if owner_id is not None:
        statement = statement.where(Item.owner_id == owner_id)
    return session.exec(statement).one()


def get_items(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    owner_id: uuid.UUID | None = None,
) -> list[Item]:
    statement = (
        select(Item)
        .order_by(col(Item.created_at).desc(), col(Item.id).desc())
        .offset(skip)
        .limit(limit)
    )
    if owner_id is not None:
        statement = statement.where(Item.owner_id == owner_id)
    return list(session.exec(statement).all())


def get_item_by_id(*, session: Session, item_id: uuid.UUID) -> Item | None:
    return session.get(Item, item_id)


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    return db_item


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Item:
    update_data = item_in.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(update_data)
    session.add(db_item)
    return db_item


def delete_item(*, session: Session, db_item: Item) -> None:
    session.delete(db_item)
    session.flush()


def delete_items_by_owner(*, session: Session, owner_id: uuid.UUID) -> None:
    statement = delete(Item).where(col(Item.owner_id) == owner_id)
    session.exec(statement)

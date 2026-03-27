import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app import crud
from app.models import Item, ItemCreate, ItemsPublic, ItemUpdate, Message, User


def read_items(
    *, session: Session, current_user: User, skip: int = 0, limit: int = 100
) -> ItemsPublic:
    owner_id = None if current_user.is_superuser else current_user.id
    count = crud.count_items(session=session, owner_id=owner_id)
    items = crud.get_items(session=session, skip=skip, limit=limit, owner_id=owner_id)

    return ItemsPublic(data=items, count=count)


def read_item(*, session: Session, current_user: User, id: uuid.UUID) -> Item:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


def create_item(*, session: Session, current_user: User, item_in: ItemCreate) -> Item:
    return crud.create_item(session=session, item_in=item_in, owner_id=current_user.id)


def update_item(
    *, session: Session, current_user: User, id: uuid.UUID, item_in: ItemUpdate
) -> Item:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud.update_item(session=session, db_item=item, item_in=item_in)


def delete_item(*, session: Session, current_user: User, id: uuid.UUID) -> Message:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    crud.delete_item(session=session, db_item=item)
    return Message(message="Item deleted successfully")

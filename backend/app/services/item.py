import uuid

from sqlmodel import Session

from app import crud
from app.core.exceptions import ItemNotFoundError, PermissionDeniedError
from app.models import Item, User
from app.schemas.item import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate
from app.schemas.security import Message


def read_items(
    *, session: Session, current_user: User, skip: int = 0, limit: int = 100
) -> ItemsPublic:
    owner_id = None if current_user.is_superuser else current_user.id
    count = crud.count_items(session=session, owner_id=owner_id)
    items = crud.get_items(session=session, skip=skip, limit=limit, owner_id=owner_id)

    items_public = [ItemPublic.model_validate(item) for item in items]
    return ItemsPublic(data=items_public, count=count)


def read_item(*, session: Session, current_user: User, id: uuid.UUID) -> Item:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    return item


def create_item(*, session: Session, current_user: User, item_in: ItemCreate) -> Item:
    item = crud.create_item(session=session, item_in=item_in, owner_id=current_user.id)
    session.commit()
    session.refresh(item)
    return item


def update_item(
    *, session: Session, current_user: User, id: uuid.UUID, item_in: ItemUpdate
) -> Item:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    item = crud.update_item(session=session, db_item=item, item_in=item_in)
    session.commit()
    session.refresh(item)
    return item


def delete_item(*, session: Session, current_user: User, id: uuid.UUID) -> Message:
    item = crud.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    crud.delete_item(session=session, db_item=item)
    session.commit()
    return Message(message="Item deleted successfully")

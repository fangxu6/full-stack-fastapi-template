import uuid

from sqlmodel import Session

from app.core.exceptions import ItemNotFoundError, PermissionDeniedError
from app.models import Item, User
from app.schemas.item import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate
from app.schemas.security import Message

from . import repository


def read_items(
    *, session: Session, current_user: User, skip: int = 0, limit: int = 100
) -> ItemsPublic:
    owner_id = None if current_user.is_superuser else current_user.id
    count = repository.count_items(session=session, owner_id=owner_id)
    items = repository.get_items(
        session=session, skip=skip, limit=limit, owner_id=owner_id
    )

    items_public = [ItemPublic.model_validate(item) for item in items]
    return ItemsPublic(data=items_public, count=count)


def read_item(*, session: Session, current_user: User, id: uuid.UUID) -> Item:
    item = repository.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    return item


def create_item(*, session: Session, current_user: User, item_in: ItemCreate) -> Item:
    item = repository.create_item(
        session=session, item_in=item_in, owner_id=current_user.id
    )
    session.commit()
    session.refresh(item)
    return item


def update_item(
    *, session: Session, current_user: User, id: uuid.UUID, item_in: ItemUpdate
) -> Item:
    item = repository.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    item = repository.update_item(session=session, db_item=item, item_in=item_in)
    session.commit()
    session.refresh(item)
    return item


def delete_item(*, session: Session, current_user: User, id: uuid.UUID) -> Message:
    item = repository.get_item_by_id(session=session, item_id=id)
    if not item:
        raise ItemNotFoundError()
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise PermissionDeniedError("Not enough permissions")
    repository.delete_item(session=session, db_item=item)
    session.commit()
    return Message(message="Item deleted successfully")

import uuid
from typing import Any

from fastapi import APIRouter, Query

from app import services
from app.api.deps import CurrentUser, SessionDep, WriteSessionDep
from app.schemas.item import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate
from app.schemas.security import Message

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
) -> Any:
    """
    Retrieve items.
    """
    return services.item.read_items(
        session=session, current_user=current_user, skip=skip, limit=limit
    )


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    return services.item.read_item(session=session, current_user=current_user, id=id)


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: WriteSessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    return services.item.create_item(
        session=session, current_user=current_user, item_in=item_in
    )


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: WriteSessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    return services.item.update_item(
        session=session, current_user=current_user, id=id, item_in=item_in
    )


@router.delete("/{id}")
def delete_item(
    session: WriteSessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    return services.item.delete_item(session=session, current_user=current_user, id=id)

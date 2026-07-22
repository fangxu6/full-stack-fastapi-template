import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app import services
from app.api.deps import (
    CurrentUser,
    SessionDep,
)
from app.modules.iam.dependencies import permission_required
from app.schemas.security import Message
from app.schemas.user import (
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/",
    dependencies=[Depends(permission_required("system.users.read"))],
    response_model=UsersPublic,
)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    return services.user.read_users(session=session, skip=skip, limit=limit)


@router.post(
    "/", dependencies=[Depends(permission_required("system.users.manage"))], response_model=UserPublic
)
def create_user(*, session: SessionDep, user_in: UserCreate) -> Any:
    """
    Create new user.
    """
    user = services.user.create_user(session=session, user_in=user_in)
    return services.user.user_public(session=session, user=user)


@router.patch("/me", response_model=UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """
    user = services.user.update_user_me(
        session=session, user_in=user_in, current_user=current_user
    )
    return services.user.user_public(session=session, user=user)


@router.patch("/me/password", response_model=Message)
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    return services.user.update_password_me(
        session=session, body=body, current_user=current_user
    )


@router.get("/me", response_model=UserPublic)
def read_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return services.user.user_public(session=session, user=current_user)


@router.delete("/me", response_model=Message)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    return services.user.delete_user(
        session=session, user_id=current_user.id
    )


@router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    user = services.user.register_user(session=session, user_in=user_in)
    return services.user.user_public(session=session, user=user)


@router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Get a specific user by id.
    """
    if user_id != current_user.id:
        from app.modules.iam import service as iam_service

        iam_service.require_permission(
            session=session,
            user=current_user,
            permission_code="system.users.read",
        )
    user = services.user.read_user_by_id(session=session, user_id=user_id)
    return services.user.user_public(session=session, user=user)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(permission_required("system.users.manage"))],
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> Any:
    """
    Update a user.
    """
    user = services.user.update_user(session=session, user_id=user_id, user_in=user_in)
    return services.user.user_public(session=session, user=user)


@router.delete("/{user_id}", dependencies=[Depends(permission_required("system.users.manage"))])
def delete_user(
    session: SessionDep, user_id: uuid.UUID
) -> Message:
    """
    Delete a user.
    """
    return services.user.delete_user(
        session=session, user_id=user_id
    )

from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    UserNotFoundError,
)
from app.core.observability import set_actor_kind_authenticated
from app.models import User
from app.schemas.security import TokenPayload

from .database import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep, request: Request) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError, ValidationError:
        raise AuthenticationError()
    user = session.get(User, token_data.sub)
    if not user:
        raise UserNotFoundError()
    if not user.is_active:
        raise BadRequestError("Inactive user")
    request.state.actor_kind = "authenticated"
    set_actor_kind_authenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("The user doesn't have enough privileges")
    return current_user

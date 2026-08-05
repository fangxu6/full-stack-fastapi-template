from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
)
from app.core.observability import set_actor_kind_authenticated
from app.models import AuthSession, User

from .database import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

SessionDep = Annotated[Session, Depends(get_db, scope="function")]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep, request: Request) -> User:
    try:
        token_data = security.decode_access_token(token)
    except InvalidTokenError, ValidationError:
        raise AuthenticationError()
    user = session.get(User, token_data.sub)
    if not user:
        raise AuthenticationError()
    if user.is_system_actor:
        raise AuthenticationError()
    if not user.is_active:
        raise AuthenticationError()
    auth_session = session.get(AuthSession, token_data.sid)
    if (
        auth_session is None
        or auth_session.user_id != user.id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= datetime.now(UTC)
    ):
        raise AuthenticationError()
    request.state.actor_kind = "authenticated"
    set_actor_kind_authenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("The user doesn't have enough privileges")
    return current_user

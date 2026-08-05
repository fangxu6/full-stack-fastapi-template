from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError
from app.core.observability import set_actor_kind_authenticated
from app.models import User
from app.modules.auth import session as auth_session

from .database import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

SessionDep = Annotated[Session, Depends(get_db, scope="function")]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep, request: Request) -> User:
    user = auth_session.validate_access_token(session=session, token=token)
    request.state.actor_kind = "authenticated"
    set_actor_kind_authenticated()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("The user doesn't have enough privileges")
    return current_user

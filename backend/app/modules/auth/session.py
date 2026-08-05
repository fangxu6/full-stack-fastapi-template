import uuid
from datetime import UTC, datetime, timedelta

from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlalchemy import update
from sqlmodel import Session, col

from app.core import security
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.models import AuthSession, User


def issue_access_token(*, session: Session, user_id: uuid.UUID) -> str:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    auth_session = AuthSession(
        user_id=user_id,
        expires_at=datetime.now(UTC) + access_token_expires,
    )
    session.add(auth_session)
    session.flush()
    return security.create_access_token(
        subject=user_id,
        session_id=auth_session.id,
        expires_delta=access_token_expires,
    )


def validate_access_token(*, session: Session, token: str) -> User:
    try:
        token_data = security.decode_access_token(token)
    except (InvalidTokenError, ValidationError) as error:
        raise AuthenticationError() from error

    user = session.get(User, token_data.sub)
    if not user or user.is_system_actor or not user.is_active:
        raise AuthenticationError()

    auth_session = session.get(AuthSession, token_data.sid)
    if (
        auth_session is None
        or auth_session.user_id != user.id
        or auth_session.revoked_at is not None
        or auth_session.expires_at <= datetime.now(UTC)
    ):
        raise AuthenticationError()
    return user


def logout(*, session: Session, token: str) -> None:
    try:
        token_data = security.decode_access_token(token, allow_expired=True)
    except (InvalidTokenError, ValidationError) as error:
        raise AuthenticationError() from error
    session.exec(
        update(AuthSession)
        .where(
            col(AuthSession.id) == token_data.sid,
            col(AuthSession.user_id) == token_data.sub,
            col(AuthSession.revoked_at).is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )


def revoke_all_user_sessions(*, session: Session, user_id: uuid.UUID) -> None:
    session.exec(
        update(AuthSession)
        .where(
            col(AuthSession.user_id) == user_id,
            col(AuthSession.revoked_at).is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )

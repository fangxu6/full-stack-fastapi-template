from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.core import security
from app.core.exceptions import AuthenticationError
from app.models import AuthSession, User
from app.modules.auth import session as auth_session
from tests.utils.utils import random_email


def _create_user(db: Session) -> User:
    user = User(email=random_email(), hashed_password="not-used")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_issue_and_validate_access_token(db: Session) -> None:
    user = _create_user(db)

    token = auth_session.issue_access_token(session=db, user_id=user.id)
    db.commit()

    assert auth_session.validate_access_token(session=db, token=token).id == user.id
    payload = security.decode_access_token(token)
    stored = db.get(AuthSession, payload.sid)
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.revoked_at is None


def test_validate_rejects_mismatched_expired_and_revoked_sessions(db: Session) -> None:
    user = _create_user(db)
    other_user = _create_user(db)
    token = auth_session.issue_access_token(session=db, user_id=user.id)
    db.commit()
    payload = security.decode_access_token(token)
    stored = db.get(AuthSession, payload.sid)
    assert stored is not None

    stored.user_id = other_user.id
    db.add(stored)
    db.commit()
    with pytest.raises(AuthenticationError):
        auth_session.validate_access_token(session=db, token=token)

    stored.user_id = user.id
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.add(stored)
    db.commit()
    with pytest.raises(AuthenticationError):
        auth_session.validate_access_token(session=db, token=token)

    stored.expires_at = datetime.now(UTC) + timedelta(minutes=5)
    stored.revoked_at = datetime.now(UTC)
    db.add(stored)
    db.commit()
    with pytest.raises(AuthenticationError):
        auth_session.validate_access_token(session=db, token=token)


def test_logout_is_idempotent_and_accepts_expired_access_token(db: Session) -> None:
    user = _create_user(db)
    stored = AuthSession(
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db.add(stored)
    db.flush()
    token = security.create_access_token(
        subject=user.id,
        session_id=stored.id,
        expires_delta=timedelta(seconds=-1),
    )

    auth_session.logout(session=db, token=token)
    db.commit()
    auth_session.logout(session=db, token=token)
    db.commit()

    db.refresh(stored)
    assert stored.revoked_at is not None


def test_revoke_all_user_sessions_only_updates_active_sessions(db: Session) -> None:
    user = _create_user(db)
    active_token = auth_session.issue_access_token(session=db, user_id=user.id)
    revoked_token = auth_session.issue_access_token(session=db, user_id=user.id)
    db.commit()
    revoked_payload = security.decode_access_token(revoked_token)
    revoked_session = db.get(AuthSession, revoked_payload.sid)
    assert revoked_session is not None
    revoked_session.revoked_at = datetime.now(UTC)
    db.add(revoked_session)
    db.commit()

    auth_session.revoke_all_user_sessions(session=db, user_id=user.id)
    db.commit()

    sessions = db.exec(
        select(AuthSession).where(AuthSession.user_id == user.id)
    ).all()
    assert len(sessions) == 2
    assert all(item.revoked_at is not None for item in sessions)
    with pytest.raises(AuthenticationError):
        auth_session.validate_access_token(session=db, token=active_token)

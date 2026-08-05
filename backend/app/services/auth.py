from fastapi.responses import HTMLResponse
from sqlalchemy import update
from sqlmodel import Session, col

from app import crud
from app.core import security
from app.core.exceptions import BadRequestError, UserNotFoundError
from app.crud.user import increment_password_reset_version
from app.models import User
from app.modules.auth import session as auth_session
from app.schemas.security import Message, NewPassword, Token
from app.services.email_outbox import queue_password_recovery_email
from app.utils import (
    generate_reset_password_email,
    verify_password_reset_token,
)


def login_access_token(*, session: Session, username: str, password: str) -> Token:
    user = crud.authenticate(session=session, email=username, password=password)
    if not user or user.is_system_actor:
        raise BadRequestError("Incorrect email or password")
    if not user.is_active:
        raise BadRequestError("Inactive user")
    return Token(
        access_token=auth_session.issue_access_token(session=session, user_id=user.id)
    )


def logout(*, session: Session, token: str) -> Message:
    auth_session.logout(session=session, token=token)
    return Message(message="Logged out successfully")


def recover_password(*, session: Session, email: str) -> Message:
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user and user.is_active and not user.is_system_actor:
        queue_password_recovery_email(session=session, user=user)
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


def reset_password(*, session: Session, body: NewPassword) -> Message:
    token_data = verify_password_reset_token(token=body.token)
    if not token_data:
        raise BadRequestError("Invalid token")
    user = session.get(User, token_data.sub)
    if not user or user.is_system_actor:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise BadRequestError("Invalid token")
    if not user.is_active:
        raise BadRequestError("Inactive user")
    result = session.exec(
        update(User)
        .where(
            col(User.id) == user.id,
            col(User.password_reset_version) == token_data.version,
        )
        .values(
            hashed_password=security.get_password_hash(body.new_password),
            password_reset_version=User.password_reset_version + 1,
        )
    )
    if result.rowcount != 1:
        raise BadRequestError("Invalid token")
    auth_session.revoke_all_user_sessions(session=session, user_id=user.id)
    return Message(message="Password updated successfully")


def recover_password_html_content(*, session: Session, email: str) -> HTMLResponse:
    user = crud.get_user_by_email(session=session, email=email)

    if not user or user.is_system_actor:
        raise UserNotFoundError(
            "The user with this username does not exist in the system."
        )
    version = increment_password_reset_version(session=session, user=user)
    from app.utils import generate_password_reset_token

    password_reset_token = generate_password_reset_token(
        user_id=user.id,
        purpose="password_reset",
        version=version,
    )
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )

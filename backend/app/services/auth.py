from datetime import timedelta

from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app import crud
from app.core import security
from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    UserNotFoundError,
)
from app.schemas.security import Message, NewPassword, Token
from app.schemas.user import UserUpdate
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
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


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
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise BadRequestError("Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user or user.is_system_actor:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise BadRequestError("Invalid token")
    if not user.is_active:
        raise BadRequestError("Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


def recover_password_html_content(*, session: Session, email: str) -> HTMLResponse:
    user = crud.get_user_by_email(session=session, email=email)

    if not user or user.is_system_actor:
        raise UserNotFoundError(
            "The user with this username does not exist in the system."
        )
    from app.utils import generate_password_reset_token

    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )

import uuid

from sqlmodel import Session, col, func, select

from app import crud
from app.core.config import settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    UserNotFoundError,
)
from app.core.security import get_password_hash, verify_password
from app.models import User
from app.modules.iam import service as iam_service
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
from app.utils import generate_new_account_email, send_email


def read_users(*, session: Session, skip: int = 0, limit: int = 100) -> UsersPublic:
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [user_public(session=session, user=user) for user in users]
    return UsersPublic(data=users_public, count=count)


def user_public(*, session: Session, user: User) -> UserPublic:
    return UserPublic.model_validate(
        user,
        update={
            "roles": [
                role.model_dump()
                for role in iam_service.get_user_role_summaries(
                    session=session, user_id=user.id
                )
            ]
        },
    )


def create_user(*, session: Session, user_in: UserCreate) -> User:
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise BadRequestError("The user with this email already exists in the system.")

    try:
        user = crud.create_user(session=session, user_create=user_in, commit=False)
        if user_in.role_ids:
            iam_service.replace_user_roles(
                session=session, user_id=user.id, role_ids=user_in.role_ids
            )
        else:
            session.commit()
            session.refresh(user)
    except Exception:
        session.rollback()
        raise
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


def _get_required_user(*, session: Session, user_id: uuid.UUID) -> User:
    user = crud.get_user_by_id(session=session, user_id=user_id)
    if user is None:
        raise UserNotFoundError()
    return user


def read_user_by_id(*, session: Session, user_id: uuid.UUID) -> User:
    return _get_required_user(session=session, user_id=user_id)


def update_user_me(
    *, session: Session, user_in: UserUpdateMe, current_user: User
) -> User:
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise ConflictError("User with this email already exists")
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def update_password_me(
    *, session: Session, body: UpdatePassword, current_user: User
) -> Message:
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise BadRequestError("Incorrect password")
    if body.current_password == body.new_password:
        raise BadRequestError("New password cannot be the same as the current one")
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


def register_user(*, session: Session, user_in: UserRegister) -> User:
    user = crud.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise BadRequestError("The user with this email already exists in the system")
    user_create = UserCreate.model_validate(user_in)
    user = crud.create_user(session=session, user_create=user_create)
    return user


def update_user(*, session: Session, user_id: uuid.UUID, user_in: UserUpdate) -> User:
    db_user = crud.get_user_by_id(session=session, user_id=user_id)
    if db_user is None:
        raise UserNotFoundError("The user with this id does not exist in the system")
    if user_in.email:
        existing_user = crud.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise ConflictError("User with this email already exists")

    try:
        was_active = db_user.is_active
        if was_active and user_in.is_active is False:
            iam_service.ensure_user_deactivation_is_safe(session=session, user=db_user)
        db_user = crud.update_user(
            session=session, db_user=db_user, user_in=user_in, commit=False
        )
        session.commit()
        session.refresh(db_user)
        return db_user
    except Exception:
        session.rollback()
        raise


def delete_user(*, session: Session, user_id: uuid.UUID) -> Message:
    user = _get_required_user(session=session, user_id=user_id)
    try:
        iam_service.ensure_user_deactivation_is_safe(session=session, user=user)
        crud.delete_items_by_owner(session=session, owner_id=user_id)
        crud.delete_user(session=session, db_user=user, commit=False)
        session.commit()
        return Message(message="User deleted successfully")
    except Exception:
        session.rollback()
        raise

import secrets
import uuid

from sqlalchemy import event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SASession
from sqlmodel import Session, col, select

from app.core.security import get_password_hash
from app.models.base import AuditFields, get_datetime_utc
from app.models.user import User

AUDIT_ACTOR_SESSION_KEY = "audit_actor_id"
DEFAULT_SYSTEM_ACTOR_KEY = "system"
SYSTEM_ACTOR_EMAIL = "system@example.com"


class AuditActorError(RuntimeError):
    """Raised when an auditable write has no valid actor binding."""


def bind_audit_actor(*, session: Session, actor_id: uuid.UUID) -> None:
    actor = session.get(User, actor_id)
    if actor is None or actor in session.deleted:
        raise AuditActorError("The audit actor does not exist")
    session.info[AUDIT_ACTOR_SESSION_KEY] = actor_id


def clear_audit_actor(*, session: Session) -> None:
    session.info.pop(AUDIT_ACTOR_SESSION_KEY, None)


def ensure_system_actor(*, session: Session) -> User:
    return provision_system_actor(
        session=session,
        actor_key=DEFAULT_SYSTEM_ACTOR_KEY,
        email=SYSTEM_ACTOR_EMAIL,
    )


def provision_system_actor(*, session: Session, actor_key: str, email: str) -> User:
    """Create or return a non-interactive System Actor for a stable key."""
    normalized_key = actor_key.strip()
    if not normalized_key:
        raise ValueError("System Actor key must not be blank")

    system_actor = session.exec(
        select(User).where(
            col(User.is_system_actor).is_(True),
            User.system_actor_key == normalized_key,
        )
    ).first()
    if system_actor is not None:
        return system_actor

    try:
        with session.begin_nested():
            system_actor = User(
                email=email,
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                is_active=False,
                is_system_actor=True,
                system_actor_key=normalized_key,
            )
            session.add(system_actor)
            session.flush()
    except IntegrityError:
        system_actor = session.exec(
            select(User).where(
                col(User.is_system_actor).is_(True),
                User.system_actor_key == normalized_key,
            )
        ).first()
        if system_actor is None:
            raise
    return system_actor


def require_system_actor(*, session: Session) -> uuid.UUID:
    system_actor = session.exec(
        select(User).where(
            col(User.is_system_actor).is_(True),
            User.system_actor_key == DEFAULT_SYSTEM_ACTOR_KEY,
        )
    ).first()
    if system_actor is None:
        raise AuditActorError("The System Actor has not been initialized")
    return system_actor.id


def _require_bound_actor_id(session: SASession) -> uuid.UUID:
    actor_id = session.info.get(AUDIT_ACTOR_SESSION_KEY)
    if not isinstance(actor_id, uuid.UUID):
        raise AuditActorError(
            "An audit actor must be bound before writing audit fields"
        )
    actor = session.get(User, actor_id)
    if actor is None or actor in session.deleted:
        raise AuditActorError("The audit actor does not exist")
    return actor_id


@event.listens_for(SASession, "before_flush")
def apply_audit_fields(
    session: SASession, _flush_context: object, _instances: object
) -> None:
    insert_actor_id: uuid.UUID | None = None
    insert_now = None
    for instance in session.new:
        if not isinstance(instance, AuditFields):
            continue
        if insert_actor_id is None:
            insert_actor_id = _require_bound_actor_id(session)
            insert_now = get_datetime_utc()
        assert insert_now is not None
        instance.created_at = insert_now
        instance.created_by = insert_actor_id
        instance.updated_at = insert_now
        instance.updated_by = insert_actor_id

    update_actor_id: uuid.UUID | None = None
    update_now = None
    for instance in session.dirty:
        if not isinstance(instance, AuditFields) or not session.is_modified(
            instance, include_collections=False
        ):
            continue
        state = inspect(instance)
        assert state is not None
        if state.attrs.created_at.history.has_changes():
            raise AuditActorError("created_at cannot be changed after creation")
        if state.attrs.created_by.history.has_changes():
            raise AuditActorError("created_by cannot be changed after creation")
        if update_actor_id is None:
            update_actor_id = _require_bound_actor_id(session)
            update_now = get_datetime_utc()
        assert update_now is not None
        instance.updated_at = update_now
        instance.updated_by = update_actor_id

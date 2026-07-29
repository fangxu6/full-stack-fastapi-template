from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.audit import bind_audit_actor

from .dependencies import (
    CurrentUser,
    SessionDep,
    TokenDep,
    WriteSessionDep,
    get_current_active_superuser,
    get_current_user,
    get_db,
    reusable_oauth2,
)


def get_audited_write_session(
    session: WriteSessionDep, current_user: CurrentUser
) -> Session:
    bind_audit_actor(session=session, actor_id=current_user.id)
    return session


AuditedWriteSessionDep = Annotated[
    Session, Depends(get_audited_write_session, scope="function")
]

__all__ = [
    "CurrentUser",
    "SessionDep",
    "WriteSessionDep",
    "AuditedWriteSessionDep",
    "TokenDep",
    "get_current_active_superuser",
    "get_current_user",
    "get_db",
    "reusable_oauth2",
]

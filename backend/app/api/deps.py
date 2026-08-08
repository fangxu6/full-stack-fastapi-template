from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.audit import bind_audit_actor, require_system_actor

from .dependencies import (
    CurrentUser,
    ReadSessionDep,
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


def get_system_audited_write_session(session: WriteSessionDep) -> Session:
    bind_audit_actor(session=session, actor_id=require_system_actor(session=session))
    return session


AuditedWriteSessionDep = Annotated[
    Session, Depends(get_audited_write_session, scope="function")
]
SystemAuditedWriteSessionDep = Annotated[
    Session, Depends(get_system_audited_write_session, scope="function")
]

__all__ = [
    "CurrentUser",
    "ReadSessionDep",
    "SessionDep",
    "WriteSessionDep",
    "AuditedWriteSessionDep",
    "SystemAuditedWriteSessionDep",
    "TokenDep",
    "get_current_active_superuser",
    "get_current_user",
    "get_db",
    "reusable_oauth2",
]

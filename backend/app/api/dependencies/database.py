from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.cache import (
    discard_deferred_cache_invalidations,
    drain_deferred_cache_invalidations,
)
from app.core.db import engine, read_engine


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def get_read_db() -> Generator[Session]:
    with Session(read_engine) as session:
        yield session


def get_write_db(
    session: Annotated[Session, Depends(get_db, scope="function")],
) -> Generator[Session]:
    try:
        yield session
        session.commit()
    except Exception:
        discard_deferred_cache_invalidations(session)
        session.rollback()
        raise
    else:
        drain_deferred_cache_invalidations(session)


WriteSessionDep = Annotated[Session, Depends(get_write_db, scope="function")]
ReadSessionDep = Annotated[Session, Depends(get_read_db, scope="function")]

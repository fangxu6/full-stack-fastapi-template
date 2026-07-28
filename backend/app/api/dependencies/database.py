from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.core.db import engine


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def get_write_db(
    session: Annotated[Session, Depends(get_db, scope="function")],
) -> Generator[Session]:
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


WriteSessionDep = Annotated[Session, Depends(get_write_db, scope="function")]

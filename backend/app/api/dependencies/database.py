from collections.abc import Generator

from sqlmodel import Session

from app.core.db import engine


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session

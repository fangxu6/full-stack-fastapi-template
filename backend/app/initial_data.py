from sqlmodel import Session

from app.core.db import engine, init_db
from app.core.observability import configure_observability, log_event


def init() -> None:
    try:
        with Session(engine) as session:
            init_db(session)
    except Exception:
        log_event(
            event_name="startup.failed",
            severity="CRITICAL",
            dependency="postgres",
        )
        raise


def main() -> None:
    configure_observability()
    init()


if __name__ == "__main__":
    main()

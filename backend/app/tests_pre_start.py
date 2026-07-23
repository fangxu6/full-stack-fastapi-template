from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.db import engine
from app.core.observability import configure_observability, log_event

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
)
def init(db_engine: Engine) -> None:
    try:
        # Try to create session to check if DB is awake
        with Session(db_engine) as session:
            session.exec(select(1))
    except Exception:
        log_event(
            event_name="startup.failed",
            severity="CRITICAL",
            dependency="postgres",
        )
        raise


def main() -> None:
    configure_observability()
    init(engine)


if __name__ == "__main__":
    main()

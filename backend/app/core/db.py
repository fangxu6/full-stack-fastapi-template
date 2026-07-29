from sqlmodel import Session, create_engine, select

from app import crud
from app.core.audit import bind_audit_actor, clear_audit_actor, ensure_system_actor
from app.core.config import settings
from app.core.observability import log_event
from app.models import User
from app.modules.iam import service as iam_service
from app.modules.scheduler.service import bootstrap_inventory_jobs
from app.schemas.user import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


class IamBootstrapInitializationError(Exception):
    """Marks an IAM bootstrap failure that has already emitted its startup event."""


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    system_actor = ensure_system_actor(session=session)
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
        )
        user = crud.create_user(session=session, user_create=user_in)
        user.is_superuser = True
        session.add(user)
        session.flush()
    try:
        iam_service.ensure_bootstrap_state(session=session, first_superuser=user)
        bind_audit_actor(session=session, actor_id=system_actor.id)
        bootstrap_inventory_jobs(session=session)
        session.commit()
    except Exception as error:
        session.rollback()
        log_event(
            event_name="startup.failed",
            severity="CRITICAL",
            dependency="iam_bootstrap",
        )
        raise IamBootstrapInitializationError from error
    finally:
        clear_audit_actor(session=session)

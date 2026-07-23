from collections.abc import Callable

from app.api.dependencies.auth import CurrentUser, SessionDep
from app.models import User
from app.modules.iam import service


def permission_required(
    permission_code: str,
) -> Callable[[SessionDep, CurrentUser], User]:
    def dependency(session: SessionDep, current_user: CurrentUser) -> User:
        service.require_permission(
            session=session, user=current_user, permission_code=permission_code
        )
        return current_user

    return dependency

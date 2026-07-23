import uuid

from sqlmodel import Session, col, select

from app.models import IamPermission, IamRole, IamRolePermission, IamUserRole, User


def get_role_by_code(
    *, session: Session, code: str, lock: bool = False
) -> IamRole | None:
    statement = select(IamRole).where(col(IamRole.code) == code)
    if lock:
        statement = statement.with_for_update()
    return session.exec(statement).first()


def get_role_by_id(*, session: Session, role_id: int) -> IamRole | None:
    return session.get(IamRole, role_id)


def get_permissions_by_codes(
    *, session: Session, codes: set[str]
) -> list[IamPermission]:
    if not codes:
        return []
    return list(
        session.exec(
            select(IamPermission).where(col(IamPermission.code).in_(codes))
        ).all()
    )


def get_role_permission_codes(*, session: Session, role_id: int) -> list[str]:
    statement = (
        select(IamPermission.code)
        .join(
            IamRolePermission,
            col(IamRolePermission.permission_id) == col(IamPermission.id),
        )
        .where(col(IamRolePermission.role_id) == role_id)
        .order_by(col(IamPermission.code))
    )
    return list(session.exec(statement).all())


def get_user_role_ids(*, session: Session, user_id: uuid.UUID) -> set[int]:
    return set(
        session.exec(
            select(IamUserRole.role_id).where(col(IamUserRole.user_id) == user_id)
        ).all()
    )


def get_user_roles(
    *, session: Session, user_id: uuid.UUID, active_only: bool
) -> list[IamRole]:
    statement = (
        select(IamRole)
        .join(IamUserRole, col(IamUserRole.role_id) == col(IamRole.id))
        .where(col(IamUserRole.user_id) == user_id)
        .order_by(col(IamRole.name))
    )
    if active_only:
        statement = statement.where(col(IamRole.is_active))
    return list(session.exec(statement).all())


def get_effective_permission_codes(
    *, session: Session, user_id: uuid.UUID
) -> list[str]:
    statement = (
        select(IamPermission.code)
        .join(
            IamRolePermission,
            col(IamRolePermission.permission_id) == col(IamPermission.id),
        )
        .join(IamRole, col(IamRole.id) == col(IamRolePermission.role_id))
        .join(IamUserRole, col(IamUserRole.role_id) == col(IamRole.id))
        .where(col(IamUserRole.user_id) == user_id, col(IamRole.is_active))
        .distinct()
        .order_by(col(IamPermission.code))
    )
    return list(session.exec(statement).all())


def count_active_role_assignments(*, session: Session, role_id: int) -> int:
    statement = (
        select(User.id)
        .join(IamUserRole, col(IamUserRole.user_id) == col(User.id))
        .where(col(IamUserRole.role_id) == role_id, col(User.is_active))
    )
    return len(session.exec(statement).all())

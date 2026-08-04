import uuid

from sqlalchemy import delete
from sqlmodel import Session, col, select
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models import IamPermission, IamRole, IamRolePermission, IamUserRole, User
from app.models.base import get_datetime_utc
from app.modules.audit import service as audit_service
from app.modules.iam import repository
from app.modules.iam.constants import (
    BUILTIN_ROLES,
    PERMISSIONS,
    PLATFORM_ADMINISTRATOR,
    PREREQUISITES,
    is_governance_permission,
)
from app.schemas.iam import (
    EffectivePermissionsPublic,
    PermissionPublic,
    PermissionsPublic,
    RoleCreate,
    RolePublic,
    RolesPublic,
    RoleSummary,
    RoleUpdate,
)

_IAM_AUDIT_EVENT_RULES: dict[str, tuple[str, frozenset[str]]] = {
    "iam.role.created": ("iam_role", frozenset({"code", "permission_codes"})),
    "iam.role.updated": ("iam_role", frozenset({"changed_fields"})),
    "iam.role.activated": ("iam_role", frozenset({"is_active", "changed_fields"})),
    "iam.role.deactivated": (
        "iam_role",
        frozenset({"is_active", "changed_fields"}),
    ),
    "iam.role.permissions_replaced": ("iam_role", frozenset({"permission_codes"})),
    "iam.role.deleted": ("iam_role", frozenset()),
    "iam.user.roles_replaced": ("iam_user", frozenset({"role_ids"})),
}
_IAM_AUDIT_STATE_ACTIONS = frozenset({"iam.role.activated", "iam.role.deactivated"})


class IamValidationError(AppError):
    status_code = HTTP_422_UNPROCESSABLE_CONTENT
    detail = "Role update does not change any fields"


def role_summary(role: IamRole) -> RoleSummary:
    if role.id is None:
        raise RuntimeError("IAM role must be persisted before serialization")
    return RoleSummary(
        id=role.id,
        code=role.code,
        name=role.name,
        is_builtin=role.is_builtin,
        is_active=role.is_active,
    )


def role_public(*, session: Session, role: IamRole) -> RolePublic:
    if role.id is None:
        raise RuntimeError("IAM role must be persisted before serialization")
    return RolePublic(
        **role_summary(role).model_dump(),
        description=role.description,
        permission_codes=repository.get_role_permission_codes(
            session=session, role_id=role.id
        ),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def get_user_role_summaries(
    *, session: Session, user_id: uuid.UUID
) -> list[RoleSummary]:
    return [
        role_summary(role)
        for role in repository.get_user_roles(
            session=session, user_id=user_id, active_only=False
        )
    ]


def get_effective_permissions(
    *, session: Session, user_id: uuid.UUID
) -> EffectivePermissionsPublic:
    active_roles = repository.get_user_roles(
        session=session, user_id=user_id, active_only=True
    )
    return EffectivePermissionsPublic(
        roles=[role_summary(role) for role in active_roles],
        permissions=repository.get_effective_permission_codes(
            session=session, user_id=user_id
        ),
    )


def require_permission(*, session: Session, user: User, permission_code: str) -> None:
    permission_codes = repository.get_effective_permission_codes(
        session=session, user_id=user.id
    )
    if permission_code not in permission_codes:
        raise PermissionDeniedError("The user does not have the required permission")


def list_permissions(*, session: Session) -> PermissionsPublic:
    permissions = list(
        session.exec(select(IamPermission).order_by(col(IamPermission.code))).all()
    )
    return PermissionsPublic(
        data=[
            PermissionPublic.model_validate(permission) for permission in permissions
        ],
        count=len(permissions),
    )


def list_roles(*, session: Session) -> RolesPublic:
    roles = list(
        session.exec(
            select(IamRole).order_by(col(IamRole.is_builtin).desc(), col(IamRole.name))
        ).all()
    )
    return RolesPublic(
        data=[role_public(session=session, role=role) for role in roles],
        count=len(roles),
    )


def _require_custom_role(role: IamRole) -> None:
    if role.is_builtin:
        raise ConflictError("Built-in roles cannot be changed")


def _validate_custom_permission_codes(
    *, session: Session, permission_codes: list[str]
) -> list[IamPermission]:
    selected_codes = set(permission_codes)
    permissions = repository.get_permissions_by_codes(
        session=session, codes=selected_codes
    )
    found_codes = {permission.code for permission in permissions}
    unknown_codes = selected_codes - found_codes
    if unknown_codes:
        raise BadRequestError("Role contains an unknown permission code")
    if any(is_governance_permission(code) for code in selected_codes):
        raise PermissionDeniedError(
            "Custom roles cannot contain Governance Permissions"
        )
    missing_prerequisites = {
        prerequisite
        for code in selected_codes
        for prerequisite in PREREQUISITES.get(code, frozenset())
        if prerequisite not in selected_codes
    }
    if missing_prerequisites:
        raise BadRequestError("Role is missing required read permissions")
    return permissions


def _append_audit_event(
    *,
    session: Session,
    actor_user_id: uuid.UUID | None,
    request_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict[str, object],
) -> None:
    if actor_user_id is None:
        return
    expected_resource_type, allowed_change_keys = _IAM_AUDIT_EVENT_RULES[action]
    change_keys = set(changes)
    if (
        resource_type != expected_resource_type
        or not change_keys <= allowed_change_keys
    ):
        raise ValueError("IAM audit event does not match its action contract")
    if action in _IAM_AUDIT_STATE_ACTIONS:
        if "is_active" not in changes:
            raise ValueError("IAM state audit event must include is_active")
    elif change_keys != allowed_change_keys:
        raise ValueError("IAM audit event has incomplete change summary")
    audit_service.append_audit_event(
        session=session,
        actor_user_id=actor_user_id,
        request_id=request_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
    )


def create_role(
    *,
    session: Session,
    role_in: RoleCreate,
    audit_actor_user_id: uuid.UUID | None = None,
    audit_request_id: str | None = None,
) -> RolePublic:
    if repository.get_role_by_code(session=session, code=role_in.code):
        raise ConflictError("A role with this code already exists")
    permissions = _validate_custom_permission_codes(
        session=session, permission_codes=role_in.permission_codes
    )
    role = IamRole(
        code=role_in.code,
        name=role_in.name,
        description=role_in.description,
        is_builtin=False,
        is_active=True,
    )
    session.add(role)
    session.flush()
    if role.id is None:
        raise RuntimeError("IAM role did not receive an identifier")
    session.add_all(
        [
            IamRolePermission(role_id=role.id, permission_id=permission.id)
            for permission in permissions
            if permission.id is not None
        ]
    )
    session.flush()
    session.refresh(role)
    result = role_public(session=session, role=role)
    _append_audit_event(
        session=session,
        actor_user_id=audit_actor_user_id,
        request_id=audit_request_id,
        action="iam.role.created",
        resource_type="iam_role",
        resource_id=str(result.id),
        changes={"code": result.code, "permission_codes": result.permission_codes},
    )
    return result


def update_role(
    *,
    session: Session,
    role_id: int,
    role_in: RoleUpdate,
    audit_actor_user_id: uuid.UUID | None = None,
    audit_request_id: str | None = None,
) -> RolePublic:
    role = repository.get_role_by_id(session=session, role_id=role_id, lock=True)
    if role is None:
        raise NotFoundError("Role does not exist")
    _require_custom_role(role)
    role_data = role_in.model_dump(exclude_unset=True)
    changed_role_data = {
        field: value
        for field, value in role_data.items()
        if getattr(role, field) != value
    }
    if not changed_role_data:
        raise IamValidationError()
    was_active = role.is_active
    role.sqlmodel_update(changed_role_data)
    role.updated_at = get_datetime_utc()
    session.add(role)
    session.flush()
    session.refresh(role)
    result = role_public(session=session, role=role)
    changes: dict[str, object]
    non_state_changed_fields = sorted(set(changed_role_data) - {"is_active"})
    if "is_active" in changed_role_data and was_active != result.is_active:
        action = "iam.role.activated" if result.is_active else "iam.role.deactivated"
        changes = {"is_active": {"before": was_active, "after": result.is_active}}
        if non_state_changed_fields:
            changes["changed_fields"] = non_state_changed_fields
    else:
        action = "iam.role.updated"
        changes = {"changed_fields": sorted(changed_role_data)}
    _append_audit_event(
        session=session,
        actor_user_id=audit_actor_user_id,
        request_id=audit_request_id,
        action=action,
        resource_type="iam_role",
        resource_id=str(result.id),
        changes=changes,
    )
    return result


def replace_role_permissions(
    *,
    session: Session,
    role_id: int,
    permission_codes: list[str],
    audit_actor_user_id: uuid.UUID | None = None,
    audit_request_id: str | None = None,
) -> RolePublic:
    role = repository.get_role_by_id(session=session, role_id=role_id, lock=True)
    if role is None:
        raise NotFoundError("Role does not exist")
    _require_custom_role(role)
    previous_permission_codes = repository.get_role_permission_codes(
        session=session, role_id=role_id
    )
    permissions = _validate_custom_permission_codes(
        session=session, permission_codes=permission_codes
    )
    session.exec(
        delete(IamRolePermission).where(col(IamRolePermission.role_id) == role_id)
    )
    session.add_all(
        [
            IamRolePermission(role_id=role_id, permission_id=permission.id)
            for permission in permissions
            if permission.id is not None
        ]
    )
    role.updated_at = get_datetime_utc()
    session.add(role)
    session.flush()
    session.refresh(role)
    result = role_public(session=session, role=role)
    _append_audit_event(
        session=session,
        actor_user_id=audit_actor_user_id,
        request_id=audit_request_id,
        action="iam.role.permissions_replaced",
        resource_type="iam_role",
        resource_id=str(result.id),
        changes={
            "permission_codes": {
                "before": previous_permission_codes,
                "after": result.permission_codes,
            }
        },
    )
    return result


def delete_role(
    *,
    session: Session,
    role_id: int,
    audit_actor_user_id: uuid.UUID | None = None,
    audit_request_id: str | None = None,
) -> None:
    role = repository.get_role_by_id(session=session, role_id=role_id, lock=True)
    if role is None:
        raise NotFoundError("Role does not exist")
    _require_custom_role(role)
    if role.is_active:
        raise ConflictError("Only inactive custom roles can be deleted")
    assignment = session.exec(
        select(IamUserRole).where(col(IamUserRole.role_id) == role_id)
    ).first()
    if assignment is not None:
        raise ConflictError("Roles with user assignments cannot be deleted")
    session.exec(
        delete(IamRolePermission).where(col(IamRolePermission.role_id) == role_id)
    )
    session.delete(role)
    session.flush()
    _append_audit_event(
        session=session,
        actor_user_id=audit_actor_user_id,
        request_id=audit_request_id,
        action="iam.role.deleted",
        resource_type="iam_role",
        resource_id=str(role_id),
        changes={},
    )


def _lock_platform_administrator(session: Session) -> IamRole:
    role = repository.get_role_by_code(
        session=session, code=PLATFORM_ADMINISTRATOR, lock=True
    )
    if role is None:
        raise RuntimeError("Platform Administrator role is missing")
    return role


def _ensure_active_platform_administrator(*, session: Session, role: IamRole) -> None:
    if role.id is None or not role.is_active:
        raise ConflictError("The active Platform Administrator role is required")
    if repository.count_active_role_assignments(session=session, role_id=role.id) == 0:
        raise ConflictError("At least one active Platform Administrator is required")


def replace_user_roles(
    *,
    session: Session,
    user_id: uuid.UUID,
    role_ids: list[int],
    audit_actor_user_id: uuid.UUID | None = None,
    audit_request_id: str | None = None,
) -> list[RoleSummary]:
    user = session.get(User, user_id)
    if user is None or user.is_system_actor:
        raise NotFoundError("User does not exist")
    selected_role_ids = set(role_ids)
    existing_role_ids = repository.get_user_role_ids(session=session, user_id=user_id)
    roles = [
        role
        for role_id in selected_role_ids
        if (role := repository.get_role_by_id(session=session, role_id=role_id))
        is not None
    ]
    if len(roles) != len(selected_role_ids):
        raise NotFoundError("One or more roles do not exist")
    if any(not role.is_active and role.id not in existing_role_ids for role in roles):
        raise ConflictError("Inactive roles cannot be assigned")

    platform_role = _lock_platform_administrator(session)
    session.exec(delete(IamUserRole).where(col(IamUserRole.user_id) == user_id))
    session.add_all(
        [
            IamUserRole(user_id=user_id, role_id=role.id)
            for role in roles
            if role.id is not None
        ]
    )
    session.flush()
    _ensure_active_platform_administrator(session=session, role=platform_role)
    result = get_user_role_summaries(session=session, user_id=user_id)
    _append_audit_event(
        session=session,
        actor_user_id=audit_actor_user_id,
        request_id=audit_request_id,
        action="iam.user.roles_replaced",
        resource_type="iam_user",
        resource_id=str(user_id),
        changes={
            "role_ids": {
                "before": sorted(existing_role_ids),
                "after": sorted(role.id for role in result),
            }
        },
    )
    return result


def ensure_user_deactivation_is_safe(*, session: Session, user: User) -> None:
    platform_role = _lock_platform_administrator(session)
    if platform_role.id is None or not platform_role.is_active or not user.is_active:
        return
    if platform_role.id not in repository.get_user_role_ids(
        session=session, user_id=user.id
    ):
        return
    if (
        repository.count_active_role_assignments(
            session=session, role_id=platform_role.id
        )
        <= 1
    ):
        raise ConflictError("At least one active Platform Administrator is required")


def ensure_bootstrap_state(*, session: Session, first_superuser: User) -> None:
    existing_permissions = {
        permission.code: permission
        for permission in session.exec(select(IamPermission)).all()
    }
    for code, group_name, label, description in PERMISSIONS:
        if code not in existing_permissions:
            session.add(
                IamPermission(
                    code=code,
                    group_name=group_name,
                    label=label,
                    description=description,
                )
            )
    session.flush()

    permissions_by_code = {
        permission.code: permission
        for permission in session.exec(select(IamPermission)).all()
    }
    builtin_roles: dict[str, IamRole] = {}
    for code, (name, description, _) in BUILTIN_ROLES.items():
        role = repository.get_role_by_code(session=session, code=code)
        if role is None:
            role = IamRole(
                code=code,
                name=name,
                description=description,
                is_builtin=True,
                is_active=True,
            )
            session.add(role)
            session.flush()
        else:
            role.name = name
            role.description = description
            role.is_builtin = True
            role.is_active = True
            role.updated_at = get_datetime_utc()
            session.add(role)
        builtin_roles[code] = role

    session.flush()
    for code, (_, _, permission_codes) in BUILTIN_ROLES.items():
        role = builtin_roles[code]
        if role.id is None:
            raise RuntimeError("Built-in role did not receive an identifier")
        session.exec(
            delete(IamRolePermission).where(col(IamRolePermission.role_id) == role.id)
        )
        session.add_all(
            [
                IamRolePermission(role_id=role.id, permission_id=permission.id)
                for permission_code in permission_codes
                if (permission := permissions_by_code[permission_code]).id is not None
            ]
        )

    platform_role = _lock_platform_administrator(session)
    if platform_role.id is None:
        raise RuntimeError("Platform Administrator role did not receive an identifier")
    assigned_ids = repository.get_user_role_ids(
        session=session, user_id=first_superuser.id
    )
    if platform_role.id not in assigned_ids:
        session.add(IamUserRole(user_id=first_superuser.id, role_id=platform_role.id))
    session.flush()
    _ensure_active_platform_administrator(session=session, role=platform_role)

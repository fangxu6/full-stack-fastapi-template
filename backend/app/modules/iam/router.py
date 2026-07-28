import uuid

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, SessionDep, WriteSessionDep
from app.modules.iam import service
from app.modules.iam.dependencies import permission_required
from app.schemas.iam import (
    EffectivePermissionsPublic,
    PermissionsPublic,
    RoleCreate,
    RolePermissionsReplace,
    RolePublic,
    RolesPublic,
    RoleUpdate,
    UserRolesPublic,
    UserRolesReplace,
)
from app.schemas.security import Message

router = APIRouter(prefix="/iam", tags=["iam"])


@router.get("/me/permissions", response_model=EffectivePermissionsPublic)
def read_my_permissions(
    session: SessionDep, current_user: CurrentUser
) -> EffectivePermissionsPublic:
    return service.get_effective_permissions(session=session, user_id=current_user.id)


@router.get(
    "/permissions",
    dependencies=[Depends(permission_required("iam.roles.read"))],
    response_model=PermissionsPublic,
)
def read_permission_catalog(session: SessionDep) -> PermissionsPublic:
    return service.list_permissions(session=session)


@router.get(
    "/roles",
    dependencies=[Depends(permission_required("iam.roles.read"))],
    response_model=RolesPublic,
)
def read_roles(session: SessionDep) -> RolesPublic:
    return service.list_roles(session=session)


@router.post(
    "/roles",
    dependencies=[Depends(permission_required("iam.roles.manage"))],
    response_model=RolePublic,
)
def create_role(session: WriteSessionDep, role_in: RoleCreate) -> RolePublic:
    return service.create_role(session=session, role_in=role_in)


@router.patch(
    "/roles/{role_id}",
    dependencies=[Depends(permission_required("iam.roles.manage"))],
    response_model=RolePublic,
)
def update_role(
    session: WriteSessionDep, role_id: int, role_in: RoleUpdate
) -> RolePublic:
    return service.update_role(session=session, role_id=role_id, role_in=role_in)


@router.put(
    "/roles/{role_id}/permissions",
    dependencies=[Depends(permission_required("iam.roles.manage"))],
    response_model=RolePublic,
)
def replace_role_permissions(
    session: WriteSessionDep, role_id: int, body: RolePermissionsReplace
) -> RolePublic:
    return service.replace_role_permissions(
        session=session, role_id=role_id, permission_codes=body.permission_codes
    )


@router.delete(
    "/roles/{role_id}",
    dependencies=[Depends(permission_required("iam.roles.manage"))],
    response_model=Message,
)
def delete_role(session: WriteSessionDep, role_id: int) -> Message:
    service.delete_role(session=session, role_id=role_id)
    return Message(message="Role deleted successfully")


@router.put(
    "/users/{user_id}/roles",
    dependencies=[Depends(permission_required("system.users.manage"))],
    response_model=UserRolesPublic,
)
def replace_user_roles(
    session: WriteSessionDep, user_id: uuid.UUID, body: UserRolesReplace
) -> UserRolesPublic:
    return UserRolesPublic(
        data=service.replace_user_roles(
            session=session, user_id=user_id, role_ids=body.role_ids
        )
    )

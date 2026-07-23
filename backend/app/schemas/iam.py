from datetime import datetime

from sqlmodel import Field, SQLModel
from sqlmodel._compat import SQLModelConfig


class PermissionPublic(SQLModel):
    id: int
    code: str
    group_name: str
    label: str
    description: str


class PermissionsPublic(SQLModel):
    data: list[PermissionPublic]
    count: int


class RoleSummary(SQLModel):
    id: int
    code: str
    name: str
    is_builtin: bool
    is_active: bool


class RolePublic(RoleSummary):
    description: str | None = None
    permission_codes: list[str]
    created_at: datetime
    updated_at: datetime


class RolesPublic(SQLModel):
    data: list[RolePublic]
    count: int


class RoleCreate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    code: str = Field(regex=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class RolePermissionsReplace(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    permission_codes: list[str]


class UserRolesReplace(SQLModel):
    model_config = SQLModelConfig(extra="forbid")

    role_ids: list[int]


class UserRolesPublic(SQLModel):
    data: list[RoleSummary]


class EffectivePermissionsPublic(SQLModel):
    roles: list[RoleSummary]
    permissions: list[str]

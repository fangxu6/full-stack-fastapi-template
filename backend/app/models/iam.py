import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Identity, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class IamPermission(SQLModel, table=True):
    __tablename__ = "iam_permission"

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    code: str = Field(max_length=128, unique=True, index=True)
    group_name: str = Field(max_length=64)
    label: str = Field(max_length=128)
    description: str = Field(max_length=255)


class IamRole(SQLModel, table=True):
    __tablename__ = "iam_role"
    __table_args__ = (UniqueConstraint("code", name="uq_iam_role_code"),)

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    code: str = Field(max_length=64, index=True)
    name: str = Field(max_length=128)
    description: str | None = Field(default=None, max_length=255)
    is_builtin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        nullable=False,
    )


class IamRolePermission(SQLModel, table=True):
    __tablename__ = "iam_role_permission"

    role_id: int = Field(
        foreign_key="iam_role.id", primary_key=True, nullable=False, ondelete="RESTRICT"
    )
    permission_id: int = Field(
        foreign_key="iam_permission.id",
        primary_key=True,
        nullable=False,
        ondelete="RESTRICT",
    )


class IamUserRole(SQLModel, table=True):
    __tablename__ = "iam_user_role"

    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, nullable=False, ondelete="CASCADE"
    )
    role_id: int = Field(
        foreign_key="iam_role.id", primary_key=True, nullable=False, ondelete="RESTRICT"
    )
    assigned_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        nullable=False,
    )

import uuid
from datetime import datetime

from pydantic import ConfigDict, EmailStr
from sqlmodel import Field, SQLModel

from app.schemas.iam import RoleSummary


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")  # ty:ignore[invalid-assignment]

    password: str = Field(min_length=8, max_length=128)
    role_ids: list[int] = Field(default_factory=list)


class UserRegister(SQLModel):
    model_config = ConfigDict(extra="forbid")  # ty:ignore[invalid-assignment]

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    model_config = ConfigDict(extra="forbid")  # ty:ignore[invalid-assignment]
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Properties to return via API
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None
    roles: list[RoleSummary] = Field(default_factory=list)


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int

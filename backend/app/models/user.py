import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship

from app.schemas.user import UserBase

from .base import get_datetime_utc

if TYPE_CHECKING:
    from .item import Item


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    password_reset_version: int = Field(
        default=0,
        nullable=False,
        sa_column_kwargs={"comment": "密码重置版本"},
    )
    # Compatibility marker for template Items and AI only. RBAC owns new access checks.
    is_superuser: bool = Field(default=False)
    is_system_actor: bool = Field(default=False, nullable=False)
    system_actor_key: str | None = Field(default=None, max_length=100)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)

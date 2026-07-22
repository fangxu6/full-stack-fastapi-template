"""create_iam_rbac_tables

Revision ID: 7b22a1c9e5d4
Revises: 5f3a7c1d9e2b
Create Date: 2026-07-22

"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "7b22a1c9e5d4"
down_revision = "5f3a7c1d9e2b"
branch_labels = None
depends_on = None


PERMISSIONS = (
    ("system.users.read", "System", "View users", "View user accounts and roles."),
    ("system.users.manage", "System", "Manage users", "Create, update, and delete user accounts."),
    ("iam.roles.read", "Access control", "View roles", "View roles and the permission catalog."),
    ("iam.roles.manage", "Access control", "Manage roles", "Create and maintain custom roles."),
    ("inventory.masters.read", "Inventory", "View master data", "View processing and receiving units."),
    ("inventory.masters.manage", "Inventory", "Manage master data", "Create and update processing and receiving units."),
    ("inventory.documents.read", "Inventory", "View documents", "View inventory documents."),
    ("inventory.documents.manage", "Inventory", "Manage documents", "Create, update, delete, and restore inventory documents."),
    ("inventory.balances.read", "Inventory", "View balances", "View current inventory balances."),
    ("inventory.ledger.read", "Inventory", "View ledger", "View inventory ledger entries."),
)

BUILTIN_ROLES = {
    "platform_administrator": (
        "Platform Administrator",
        "Full platform administration access.",
        tuple(permission[0] for permission in PERMISSIONS),
    ),
    "inventory_operator": (
        "Inventory Operator",
        "Create and manage inventory masters and documents.",
        tuple(permission[0] for permission in PERMISSIONS if permission[0].startswith("inventory.")),
    ),
    "inventory_viewer": (
        "Inventory Viewer",
        "Read inventory masters, documents, balances, and ledger entries.",
        (
            "inventory.masters.read",
            "inventory.documents.read",
            "inventory.balances.read",
            "inventory.ledger.read",
        ),
    ),
}


def upgrade() -> None:
    op.create_table(
        "iam_permission",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("group_name", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_iam_permission"),
        sa.UniqueConstraint("code", name="uq_iam_permission_code"),
    )
    op.create_index("ix_iam_permission_code", "iam_permission", ["code"], unique=False)

    op.create_table(
        "iam_role",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_iam_role"),
        sa.UniqueConstraint("code", name="uq_iam_role_code"),
    )
    op.create_index("ix_iam_role_code", "iam_role", ["code"], unique=False)

    op.create_table(
        "iam_role_permission",
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("permission_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["iam_permission.id"],
            name="fk_iam_role_permission_permission",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["iam_role.id"],
            name="fk_iam_role_permission_role",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_iam_role_permission"),
    )

    op.create_table(
        "iam_user_role",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["iam_role.id"],
            name="fk_iam_user_role_role",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_iam_user_role_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_iam_user_role"),
    )

    iam_permission = sa.table(
        "iam_permission",
        sa.column("code", sa.String),
        sa.column("group_name", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.String),
    )
    iam_role = sa.table(
        "iam_role",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_builtin", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    op.bulk_insert(
        iam_permission,
        [
            {
                "code": code,
                "group_name": group_name,
                "label": label,
                "description": description,
            }
            for code, group_name, label, description in PERMISSIONS
        ],
    )
    op.bulk_insert(
        iam_role,
        [
            {
                "code": code,
                "name": name,
                "description": description,
                "is_builtin": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            for code, (name, description, _) in BUILTIN_ROLES.items()
        ],
    )

    for role_code, (_, _, permission_codes) in BUILTIN_ROLES.items():
        quoted_codes = ", ".join(f"'{code}'" for code in permission_codes)
        op.execute(
            sa.text(
                "INSERT INTO iam_role_permission (role_id, permission_id) "
                "SELECT role.id, permission.id "
                "FROM iam_role AS role CROSS JOIN iam_permission AS permission "
                "WHERE role.code = :role_code AND permission.code IN ("
                f"{quoted_codes})"
            ).bindparams(role_code=role_code)
        )

    op.execute(
        sa.text(
            "INSERT INTO iam_user_role (user_id, role_id, assigned_at) "
            "SELECT users.id, role.id, NOW() "
            "FROM \"user\" AS users CROSS JOIN iam_role AS role "
            "WHERE users.is_superuser = TRUE "
            "AND role.code = 'platform_administrator'"
        )
    )


def downgrade() -> None:
    op.drop_table("iam_user_role")
    op.drop_table("iam_role_permission")
    op.drop_index("ix_iam_role_code", table_name="iam_role")
    op.drop_table("iam_role")
    op.drop_index("ix_iam_permission_code", table_name="iam_permission")
    op.drop_table("iam_permission")

"""add auth sessions and password token versions

Revision ID: c4e7a91d2f6b
Revises: c5f4a8d2e7b1
Create Date: 2026-08-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "c4e7a91d2f6b"
down_revision = "c5f4a8d2e7b1"
branch_labels = None
depends_on = None


PASSWORD_LINK_KINDS = "'ACCOUNT_SET_PASSWORD', 'PASSWORD_RECOVERY'"
ACTIVE_OUTBOX_STATUSES = "'PENDING', 'LEASED', 'RETRY_WAIT'"


def _email_error_constraint() -> sa.CheckConstraint:
    return sa.CheckConstraint(
        "last_error_category IS NULL OR last_error_category IN "
        "('SMTP_NOT_CONFIGURED', 'SMTP_DELIVERY_FAILED', "
        "'DELIVERY_LEASE_EXPIRED', 'RECIPIENT_INVALID', "
        "'MAX_ATTEMPTS_EXCEEDED', 'TOKEN_SUPERSEDED')",
        name="ck_email_outbox_error_category",
    )


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "password_reset_version",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
            comment="密码重置版本",
        ),
    )
    op.alter_column("user", "password_reset_version", server_default=None)
    op.add_column(
        "email_outbox",
        sa.Column(
            "password_reset_version",
            sa.Integer(),
            nullable=True,
            comment="密码链接版本快照",
        ),
    )

    op.drop_constraint(
        "ck_email_outbox_error_category", "email_outbox", type_="check"
    )
    op.create_check_constraint(
        "ck_email_outbox_error_category",
        "email_outbox",
        _email_error_constraint().sqltext,
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE email_outbox "
            "SET status = 'FAILED', lease_expires_at = NULL, "
            "last_error_category = 'TOKEN_SUPERSEDED', failed_at = now() "
            f"WHERE kind IN ({PASSWORD_LINK_KINDS}) "
            f"AND status IN ({ACTIVE_OUTBOX_STATUSES})"
        )
    )
    op.create_check_constraint(
        "ck_email_outbox_password_reset_version",
        "email_outbox",
        "kind = 'RENDERED' OR password_reset_version IS NOT NULL "
        "OR status IN ('FAILED', 'DELIVERED')",
    )

    op.create_table(
        "auth_session",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="认证会话唯一标识",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="会话所属用户标识",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="会话创建时间",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="会话过期时间",
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="会话撤销时间",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_auth_session_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_session"),
        comment="用户认证会话",
    )
    op.create_index("ix_auth_session_user_id", "auth_session", ["user_id"])
    op.create_index(
        "ix_auth_session_active",
        "auth_session",
        ["user_id", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_session_active", table_name="auth_session")
    op.drop_index("ix_auth_session_user_id", table_name="auth_session")
    op.drop_table("auth_session")

    op.drop_constraint(
        "ck_email_outbox_password_reset_version", "email_outbox", type_="check"
    )
    op.drop_constraint(
        "ck_email_outbox_error_category", "email_outbox", type_="check"
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE email_outbox SET last_error_category = NULL "
            "WHERE last_error_category = 'TOKEN_SUPERSEDED'"
        )
    )
    op.create_check_constraint(
        "ck_email_outbox_error_category",
        "email_outbox",
        "last_error_category IS NULL OR last_error_category IN "
        "('SMTP_NOT_CONFIGURED', 'SMTP_DELIVERY_FAILED', "
        "'DELIVERY_LEASE_EXPIRED', 'RECIPIENT_INVALID', "
        "'MAX_ATTEMPTS_EXCEEDED')",
    )
    op.drop_column("email_outbox", "password_reset_version")
    op.drop_column("user", "password_reset_version")

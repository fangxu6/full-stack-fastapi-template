"""seed scheduler IAM permissions for existing databases

Revision ID: f6a1b2c3d4e5
Revises: c4e7a91d2f6b
Create Date: 2026-08-11

"""

import sqlalchemy as sa
from alembic import op

revision = "f6a1b2c3d4e5"
down_revision = "c4e7a91d2f6b"
branch_labels = None
depends_on = None


SCHEDULER_PERMISSIONS = (
    (
        "scheduler.jobs.read",
        "Scheduler",
        "View scheduled tasks",
        "View scheduled task definitions and runs.",
    ),
    (
        "scheduler.jobs.manage",
        "Scheduler",
        "Manage scheduled tasks",
        "Create, change, run, and delete scheduled tasks.",
    ),
)


def upgrade() -> None:
    bind = op.get_bind()
    for code, group_name, label, description in SCHEDULER_PERMISSIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO iam_permission (code, group_name, label, description)
                VALUES (:code, :group_name, :label, :description)
                ON CONFLICT (code) DO UPDATE SET
                    group_name = EXCLUDED.group_name,
                    label = EXCLUDED.label,
                    description = EXCLUDED.description
                """
            ),
            {
                "code": code,
                "group_name": group_name,
                "label": label,
                "description": description,
            },
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO iam_role_permission (role_id, permission_id)
            SELECT role.id, permission.id
            FROM iam_role AS role
            CROSS JOIN iam_permission AS permission
            WHERE role.code = 'platform_administrator'
              AND permission.code IN ('scheduler.jobs.read', 'scheduler.jobs.manage')
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM iam_role_permission
            WHERE role_id IN (
                SELECT id FROM iam_role WHERE code = 'platform_administrator'
            )
            AND permission_id IN (
                SELECT id
                FROM iam_permission
                WHERE code IN ('scheduler.jobs.read', 'scheduler.jobs.manage')
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM iam_permission AS permission
            WHERE permission.code IN ('scheduler.jobs.read', 'scheduler.jobs.manage')
              AND NOT EXISTS (
                  SELECT 1
                  FROM iam_role_permission AS role_permission
                  WHERE role_permission.permission_id = permission.id
              )
            """
        )
    )

"""create inventory correction tables

Revision ID: c5f4a8d2e7b1
Revises: aa03e8f7c9b1
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c5f4a8d2e7b1"
down_revision = "aa03e8f7c9b1"
branch_labels = None
depends_on = None


inventory_correction_operation = postgresql.ENUM(
    "UPDATE_DOCUMENT",
    "DELETE_DOCUMENT",
    "RESTORE_DOCUMENT",
    name="inventory_correction_operation",
    create_type=False,
)
inventory_correction_request_status = postgresql.ENUM(
    "PENDING_REVIEW",
    "APPROVED",
    "REJECTED",
    "WITHDRAWN",
    "STALE",
    "APPLIED",
    "APPLICATION_FAILED",
    name="inventory_correction_request_status",
    create_type=False,
)
inventory_correction_work_item_status = postgresql.ENUM(
    "APPROVED_PENDING_APPLY",
    "RUNNING",
    "SUCCEEDED",
    "TERMINAL_FAILED",
    name="inventory_correction_work_item_status",
    create_type=False,
)
inventory_correction_attempt_status = postgresql.ENUM(
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "TERMINAL_FAILED",
    name="inventory_correction_attempt_status",
    create_type=False,
)
inventory_correction_attempt_origin = postgresql.ENUM(
    "INITIAL",
    "RECOVERY",
    name="inventory_correction_attempt_origin",
    create_type=False,
)
inventory_correction_failure_category = postgresql.ENUM(
    "STALE_TARGET",
    "NEGATIVE_BALANCE",
    "EXECUTION_LOST",
    "EXECUTION_FAILED",
    name="inventory_correction_failure_category",
    create_type=False,
)


def _audit_columns():
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间"
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="创建人标识",
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间"
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="更新人标识",
        ),
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"
        ),
    ]


def _audit_foreign_keys(table: str) -> tuple[sa.ForeignKeyConstraint, ...]:
    return (
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name=f"fk_{table}_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name=f"fk_{table}_updated_by",
            ondelete="RESTRICT",
        ),
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        inventory_correction_operation,
        inventory_correction_request_status,
        inventory_correction_work_item_status,
        inventory_correction_attempt_status,
        inventory_correction_attempt_origin,
        inventory_correction_failure_category,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "inventory_correction_request",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="纠错申请唯一标识",
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="库存单据标识",
        ),
        sa.Column(
            "operation",
            inventory_correction_operation,
            nullable=False,
            comment="纠错操作",
        ),
        sa.Column(
            "expected_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="目标单据预期更新时间",
        ),
        sa.Column(
            "proposal",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="不可变纠错提案",
        ),
        sa.Column(
            "proposal_hash", sa.String(length=64), nullable=False, comment="提案哈希值"
        ),
        sa.Column("reason", sa.String(length=500), nullable=False, comment="纠错原因"),
        sa.Column(
            "status",
            inventory_correction_request_status,
            nullable=False,
            comment="纠错申请状态",
        ),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="审核人标识",
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="审核决定时间",
        ),
        *_audit_columns(),
        sa.CheckConstraint(
            "proposal IS NULL OR jsonb_typeof(proposal) = 'object'",
            name="ck_inventory_correction_request_proposal_object",
        ),
        sa.CheckConstraint(
            "(operation = 'UPDATE_DOCUMENT' AND proposal IS NOT NULL) OR (operation <> 'UPDATE_DOCUMENT' AND proposal IS NULL)",
            name="ck_inventory_correction_request_operation_proposal",
        ),
        sa.CheckConstraint(
            "btrim(reason) <> ''", name="ck_inventory_correction_request_reason"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["inventory_document.id"],
            name="fk_inventory_correction_request_document",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["user.id"],
            name="fk_inventory_correction_request_reviewer",
            ondelete="RESTRICT",
        ),
        *_audit_foreign_keys("inventory_correction_request"),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_correction_request"),
        comment="库存异常纠错申请",
    )
    op.create_index(
        "uq_inventory_correction_request_active_document",
        "inventory_correction_request",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING_REVIEW', 'APPROVED')"),
    )
    op.create_index(
        "ix_inventory_correction_request_creator_created",
        "inventory_correction_request",
        ["created_by", "created_at", "id"],
    )

    op.create_table(
        "inventory_correction_work_item",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="纠错工作项唯一标识",
        ),
        sa.Column(
            "request_id", sa.BigInteger(), nullable=False, comment="纠错申请标识"
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="库存单据标识",
        ),
        sa.Column(
            "expected_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="目标单据预期更新时间",
        ),
        sa.Column(
            "proposal",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="纠错提案快照",
        ),
        sa.Column(
            "proposal_hash", sa.String(length=64), nullable=False, comment="提案哈希值"
        ),
        sa.Column(
            "handler_type", sa.String(length=64), nullable=False, comment="固定处理类型"
        ),
        sa.Column(
            "status",
            inventory_correction_work_item_status,
            nullable=False,
            comment="工作项状态",
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="应用租约到期时间",
        ),
        sa.Column(
            "current_attempt_sequence",
            sa.Integer(),
            nullable=False,
            comment="当前应用尝试序号",
        ),
        sa.Column(
            "terminal_failure_category",
            inventory_correction_failure_category,
            nullable=True,
            comment="最终失败类别",
        ),
        *_audit_columns(),
        sa.CheckConstraint(
            "proposal IS NULL OR jsonb_typeof(proposal) = 'object'",
            name="ck_inventory_correction_work_item_proposal_object",
        ),
        sa.CheckConstraint(
            "handler_type = 'inventory.document_correction'",
            name="ck_inventory_correction_work_item_handler",
        ),
        sa.CheckConstraint(
            "current_attempt_sequence > 0",
            name="ck_inventory_correction_work_item_attempt_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["inventory_correction_request.id"],
            name="fk_inventory_correction_work_item_request",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["inventory_document.id"],
            name="fk_inventory_correction_work_item_document",
            ondelete="RESTRICT",
        ),
        *_audit_foreign_keys("inventory_correction_work_item"),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_correction_work_item"),
        sa.UniqueConstraint(
            "request_id", name="uq_inventory_correction_work_item_request"
        ),
        comment="库存异常纠错应用工作项",
    )
    op.create_index(
        "ix_inventory_correction_work_item_pending_created",
        "inventory_correction_work_item",
        ["status", "created_at", "id"],
        postgresql_where=sa.text("status = 'APPROVED_PENDING_APPLY'"),
    )

    op.create_table(
        "inventory_correction_attempt",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            comment="纠错应用尝试唯一标识",
        ),
        sa.Column(
            "work_item_id", sa.BigInteger(), nullable=False, comment="纠错工作项标识"
        ),
        sa.Column("sequence", sa.Integer(), nullable=False, comment="应用尝试序号"),
        sa.Column(
            "origin",
            inventory_correction_attempt_origin,
            nullable=False,
            comment="应用尝试来源",
        ),
        sa.Column(
            "status",
            inventory_correction_attempt_status,
            nullable=False,
            comment="应用尝试状态",
        ),
        sa.Column(
            "scheduler_run_id",
            sa.BigInteger(),
            nullable=True,
            comment="调度运行标识快照",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="开始应用时间",
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="完成应用时间",
        ),
        sa.Column(
            "failure_category",
            inventory_correction_failure_category,
            nullable=True,
            comment="失败类别",
        ),
        *_audit_columns(),
        sa.CheckConstraint(
            "sequence > 0", name="ck_inventory_correction_attempt_sequence"
        ),
        sa.ForeignKeyConstraint(
            ["work_item_id"],
            ["inventory_correction_work_item.id"],
            name="fk_inventory_correction_attempt_work_item",
            ondelete="RESTRICT",
        ),
        *_audit_foreign_keys("inventory_correction_attempt"),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_correction_attempt"),
        sa.UniqueConstraint(
            "work_item_id",
            "sequence",
            name="uq_inventory_correction_attempt_work_item_sequence",
        ),
        comment="库存异常纠错应用尝试",
    )
    op.create_index(
        "ix_inventory_correction_attempt_pending_work_item",
        "inventory_correction_attempt",
        ["status", "work_item_id"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "inventory_correction_attempt",
        "inventory_correction_work_item",
        "inventory_correction_request",
    ):
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar():
            raise RuntimeError(
                f"cannot downgrade {table} while it contains correction records"
            )
    op.drop_index(
        "ix_inventory_correction_attempt_pending_work_item",
        table_name="inventory_correction_attempt",
    )
    op.drop_table("inventory_correction_attempt")
    op.drop_index(
        "ix_inventory_correction_work_item_pending_created",
        table_name="inventory_correction_work_item",
    )
    op.drop_table("inventory_correction_work_item")
    op.drop_index(
        "ix_inventory_correction_request_creator_created",
        table_name="inventory_correction_request",
    )
    op.drop_index(
        "uq_inventory_correction_request_active_document",
        table_name="inventory_correction_request",
    )
    op.drop_table("inventory_correction_request")
    for enum in (
        inventory_correction_failure_category,
        inventory_correction_attempt_origin,
        inventory_correction_attempt_status,
        inventory_correction_work_item_status,
        inventory_correction_request_status,
        inventory_correction_operation,
    ):
        enum.drop(bind, checkfirst=True)

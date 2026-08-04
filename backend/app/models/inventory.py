# SQLModel exposes ORM columns as their Python value type to mypy, while this
# module must also pass SQLAlchemy column descriptors through ``Field``.
# mypy's current SQLModel overloads cannot represent that combination.
# mypy: disable-error-code=call-overload

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from app.models.base import AuditFields, get_datetime_utc


class InventoryDocumentType(StrEnum):
    RAW_RECEIPT = "RAW_RECEIPT"
    RAW_RETURN = "RAW_RETURN"
    FINISHED_SHIPMENT = "FINISHED_SHIPMENT"
    FINISHED_RECEIPT = "FINISHED_RECEIPT"


class InventoryLedgerKind(StrEnum):
    RAW = "RAW"
    FINISHED = "FINISHED"


class InventoryMovementType(StrEnum):
    RAW_RECEIPT = "RAW_RECEIPT"
    RAW_RETURN = "RAW_RETURN"
    FINISHED_RECEIPT = "FINISHED_RECEIPT"
    FINISHED_SHIPMENT = "FINISHED_SHIPMENT"
    MIGRATION_RECONCILIATION_OPENING = "MIGRATION_RECONCILIATION_OPENING"


class InventoryDailyReportStatus(StrEnum):
    PENDING = "PENDING"
    RETRY_WAIT = "RETRY_WAIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class InventoryDailyReportDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    RETRY_WAIT = "RETRY_WAIT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class InventoryCorrectionOperation(StrEnum):
    UPDATE_DOCUMENT = "UPDATE_DOCUMENT"
    DELETE_DOCUMENT = "DELETE_DOCUMENT"
    RESTORE_DOCUMENT = "RESTORE_DOCUMENT"


class InventoryCorrectionRequestStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    STALE = "STALE"
    APPLIED = "APPLIED"
    APPLICATION_FAILED = "APPLICATION_FAILED"


class InventoryCorrectionWorkItemStatus(StrEnum):
    APPROVED_PENDING_APPLY = "APPROVED_PENDING_APPLY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    TERMINAL_FAILED = "TERMINAL_FAILED"


class InventoryCorrectionAttemptStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    TERMINAL_FAILED = "TERMINAL_FAILED"


class InventoryCorrectionAttemptOrigin(StrEnum):
    INITIAL = "INITIAL"
    RECOVERY = "RECOVERY"


class InventoryCorrectionFailureCategory(StrEnum):
    STALE_TARGET = "STALE_TARGET"
    NEGATIVE_BALANCE = "NEGATIVE_BALANCE"
    EXECUTION_LOST = "EXECUTION_LOST"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class LegacyWorkbookKind(StrEnum):
    RAW = "RAW"
    FINISHED = "FINISHED"


class ProcessingUnit(AuditFields, table=True):
    __tablename__ = "processing_unit"
    __table_args__ = (UniqueConstraint("normalized_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)


class ReceivingUnit(AuditFields, table=True):
    __tablename__ = "receiving_unit"
    __table_args__ = (UniqueConstraint("normalized_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    normalized_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)


class InventoryDocument(AuditFields, table=True):
    __tablename__ = "inventory_document"
    __table_args__ = (
        CheckConstraint(
            "(document_type = 'FINISHED_SHIPMENT' AND receiving_unit_id IS NOT NULL) "
            "OR (document_type <> 'FINISHED_SHIPMENT' AND receiving_unit_id IS NULL)",
            name="ck_inventory_document_receiving_unit",
        ),
        CheckConstraint(
            "is_legacy OR (document_number IS NOT NULL AND btrim(document_number) <> '')",
            name="ck_inventory_document_number",
        ),
        Index("ix_inventory_document_type_date", "document_type", "business_date"),
        Index(
            "ix_inventory_document_processing_date",
            "processing_unit_id",
            "business_date",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_type: InventoryDocumentType = Field(
        sa_type=SAEnum(InventoryDocumentType, name="inventory_document_type")  # ty:ignore[invalid-argument-type]
    )
    business_date: date
    processing_unit_id: uuid.UUID = Field(
        foreign_key="processing_unit.id", nullable=False, ondelete="RESTRICT"
    )
    receiving_unit_id: uuid.UUID | None = Field(
        default=None, foreign_key="receiving_unit.id", ondelete="RESTRICT"
    )
    document_number: str | None = Field(default=None, max_length=64)
    remarks: str | None = None
    is_legacy: bool = Field(default=False)


class InventoryDocumentLine(AuditFields, table=True):
    __tablename__ = "inventory_document_line"
    __table_args__ = (
        UniqueConstraint("document_id", "line_no"),
        CheckConstraint("line_no > 0", name="ck_inventory_document_line_number"),
        CheckConstraint("quantity_rolls >= 0", name="ck_inventory_document_line_rolls"),
        CheckConstraint(
            "quantity_meters IS NULL OR quantity_meters > 0",
            name="ck_inventory_document_line_meters",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="inventory_document.id", nullable=False, ondelete="CASCADE"
    )
    line_no: int
    item_name: str = Field(max_length=255)
    item_code: str | None = Field(default=None, max_length=255)
    wool_content: str = Field(max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)
    quantity_rolls: Decimal = Field(
        sa_type=Numeric(18, 2)  # ty:ignore[invalid-argument-type]
    )
    quantity_meters: Decimal | None = Field(default=None, sa_type=Numeric(18, 3))  # ty:ignore[invalid-argument-type]


class InventoryImportBatch(AuditFields, table=True):
    __tablename__ = "inventory_import_batch"
    __table_args__ = (UniqueConstraint("source_fingerprint"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_fingerprint: str = Field(max_length=64)
    raw_workbook_sha256: str = Field(max_length=64)
    finished_workbook_sha256: str = Field(max_length=64)
    importer_version: str = Field(max_length=64)
    reconciliation_report: dict[str, object] = Field(sa_type=JSONB)
    imported_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )


class LegacyImportRow(AuditFields, table=True):
    __tablename__ = "legacy_import_row"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id", "workbook_kind", "worksheet_name", "source_row_number"
        ),
        CheckConstraint("source_row_number > 0", name="ck_legacy_import_row_number"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    import_batch_id: uuid.UUID = Field(
        foreign_key="inventory_import_batch.id", nullable=False, ondelete="RESTRICT"
    )
    workbook_kind: LegacyWorkbookKind = Field(
        sa_type=SAEnum(LegacyWorkbookKind, name="legacy_workbook_kind")  # ty:ignore[invalid-argument-type]
    )
    workbook_name: str = Field(max_length=255)
    worksheet_name: str = Field(max_length=255)
    source_row_number: int
    raw_cells: dict[str, object] = Field(sa_type=JSONB)
    source_balance_snapshot: dict[str, object] = Field(sa_type=JSONB)
    requires_cleanup: bool = Field(default=False)


class InventoryLedgerEntry(AuditFields, table=True):
    __tablename__ = "inventory_ledger_entry"
    __table_args__ = (
        UniqueConstraint("document_line_id"),
        CheckConstraint(
            "(movement_type = 'MIGRATION_RECONCILIATION_OPENING' "
            "AND document_line_id IS NULL AND import_batch_id IS NOT NULL) "
            "OR (movement_type <> 'MIGRATION_RECONCILIATION_OPENING' "
            "AND document_line_id IS NOT NULL)",
            name="ck_inventory_ledger_entry_source",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    ledger_kind: InventoryLedgerKind = Field(
        sa_type=SAEnum(InventoryLedgerKind, name="inventory_ledger_kind")  # ty:ignore[invalid-argument-type]
    )
    movement_type: InventoryMovementType = Field(
        sa_type=SAEnum(InventoryMovementType, name="inventory_movement_type")  # ty:ignore[invalid-argument-type]
    )
    business_date: date
    processing_unit_id: uuid.UUID = Field(
        foreign_key="processing_unit.id", nullable=False, ondelete="RESTRICT"
    )
    document_line_id: uuid.UUID | None = Field(
        default=None, foreign_key="inventory_document_line.id", ondelete="RESTRICT"
    )
    legacy_import_row_id: uuid.UUID | None = Field(
        default=None, foreign_key="legacy_import_row.id", ondelete="RESTRICT"
    )
    import_batch_id: uuid.UUID | None = Field(
        default=None, foreign_key="inventory_import_batch.id", ondelete="RESTRICT"
    )
    item_name: str = Field(max_length=255)
    item_code: str | None = Field(default=None, max_length=255)
    wool_content: str = Field(max_length=255)
    color_code: str | None = Field(default=None, max_length=255)
    dye_lot_no: str | None = Field(default=None, max_length=255)
    rolls_delta: Decimal = Field(
        sa_type=Numeric(18, 2)  # ty:ignore[invalid-argument-type]
    )
    meters_delta: Decimal = Field(default=Decimal("0"), sa_type=Numeric(18, 3))  # ty:ignore[invalid-argument-type]
    reason: str | None = None


class InventoryCorrectionRequest(AuditFields, table=True):
    __tablename__ = "inventory_correction_request"
    __table_args__ = (
        CheckConstraint(
            "proposal IS NULL OR jsonb_typeof(proposal) = 'object'",
            name="ck_inventory_correction_request_proposal_object",
        ),
        ForeignKeyConstraint(
            ["document_id"],
            ["inventory_document.id"],
            name="fk_inventory_correction_request_document",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["reviewer_id"],
            ["user.id"],
            name="fk_inventory_correction_request_reviewer",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_inventory_correction_request_active_document",
            "document_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING_REVIEW', 'APPROVED')"),
        ),
        Index(
            "ix_inventory_correction_request_creator_created",
            "created_by",
            "created_at",
            "id",
        ),
        {"comment": "库存异常纠错申请"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="纠错申请唯一标识",
        ),
    )
    document_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), nullable=False, comment="库存单据标识")
    )
    operation: InventoryCorrectionOperation = Field(
        sa_type=SAEnum(
            InventoryCorrectionOperation,
            name="inventory_correction_operation",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "纠错操作"},
    )
    expected_updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "目标单据预期更新时间"},
    )
    proposal: dict[str, object] | None = Field(
        default=None,
        sa_type=JSONB,
        sa_column_kwargs={"comment": "不可变纠错提案"},
    )
    proposal_hash: str = Field(
        max_length=64,
        sa_column_kwargs={"comment": "提案哈希值"},
    )
    reason: str = Field(max_length=500, sa_column_kwargs={"comment": "纠错原因"})
    status: InventoryCorrectionRequestStatus = Field(
        default=InventoryCorrectionRequestStatus.PENDING_REVIEW,
        sa_type=SAEnum(
            InventoryCorrectionRequestStatus,
            name="inventory_correction_request_status",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "纠错申请状态"},
    )
    reviewer_id: uuid.UUID | None = Field(
        default=None,
        sa_type=PGUUID(as_uuid=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "审核人标识"},
    )
    decided_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "审核决定时间"},
    )


class InventoryCorrectionWorkItem(AuditFields, table=True):
    __tablename__ = "inventory_correction_work_item"
    __table_args__ = (
        CheckConstraint(
            "proposal IS NULL OR jsonb_typeof(proposal) = 'object'",
            name="ck_inventory_correction_work_item_proposal_object",
        ),
        CheckConstraint(
            "handler_type = 'inventory.document_correction'",
            name="ck_inventory_correction_work_item_handler",
        ),
        CheckConstraint(
            "current_attempt_sequence > 0",
            name="ck_inventory_correction_work_item_attempt_sequence",
        ),
        ForeignKeyConstraint(
            ["request_id"],
            ["inventory_correction_request.id"],
            name="fk_inventory_correction_work_item_request",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["document_id"],
            ["inventory_document.id"],
            name="fk_inventory_correction_work_item_document",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "request_id", name="uq_inventory_correction_work_item_request"
        ),
        Index(
            "ix_inventory_correction_work_item_pending_created",
            "status",
            "created_at",
            "id",
            postgresql_where=text("status = 'APPROVED_PENDING_APPLY'"),
        ),
        {"comment": "库存异常纠错应用工作项"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="纠错工作项唯一标识",
        ),
    )
    request_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, comment="纠错申请标识")
    )
    document_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), nullable=False, comment="库存单据标识")
    )
    expected_updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "目标单据预期更新时间"},
    )
    proposal: dict[str, object] | None = Field(
        default=None,
        sa_type=JSONB,
        sa_column_kwargs={"comment": "纠错提案快照"},
    )
    proposal_hash: str = Field(
        max_length=64,
        sa_column_kwargs={"comment": "提案哈希值"},
    )
    handler_type: str = Field(
        default="inventory.document_correction",
        max_length=64,
        sa_column_kwargs={"comment": "固定处理类型"},
    )
    status: InventoryCorrectionWorkItemStatus = Field(
        default=InventoryCorrectionWorkItemStatus.APPROVED_PENDING_APPLY,
        sa_type=SAEnum(
            InventoryCorrectionWorkItemStatus,
            name="inventory_correction_work_item_status",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "工作项状态"},
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "应用租约到期时间"},
    )
    current_attempt_sequence: int = Field(
        default=1,
        sa_column_kwargs={"comment": "当前应用尝试序号"},
    )
    terminal_failure_category: InventoryCorrectionFailureCategory | None = Field(
        default=None,
        sa_type=SAEnum(
            InventoryCorrectionFailureCategory,
            name="inventory_correction_failure_category",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "最终失败类别"},
    )


class InventoryCorrectionAttempt(AuditFields, table=True):
    __tablename__ = "inventory_correction_attempt"
    __table_args__ = (
        CheckConstraint(
            "sequence > 0",
            name="ck_inventory_correction_attempt_sequence",
        ),
        ForeignKeyConstraint(
            ["work_item_id"],
            ["inventory_correction_work_item.id"],
            name="fk_inventory_correction_attempt_work_item",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "work_item_id",
            "sequence",
            name="uq_inventory_correction_attempt_work_item_sequence",
        ),
        Index(
            "ix_inventory_correction_attempt_pending_work_item",
            "status",
            "work_item_id",
            postgresql_where=text("status = 'PENDING'"),
        ),
        {"comment": "库存异常纠错应用尝试"},
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
            comment="纠错应用尝试唯一标识",
        ),
    )
    work_item_id: int = Field(
        sa_column=Column(BigInteger, nullable=False, comment="纠错工作项标识")
    )
    sequence: int = Field(sa_column_kwargs={"comment": "应用尝试序号"})
    origin: InventoryCorrectionAttemptOrigin = Field(
        sa_type=SAEnum(
            InventoryCorrectionAttemptOrigin,
            name="inventory_correction_attempt_origin",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "应用尝试来源"},
    )
    status: InventoryCorrectionAttemptStatus = Field(
        default=InventoryCorrectionAttemptStatus.PENDING,
        sa_type=SAEnum(
            InventoryCorrectionAttemptStatus,
            name="inventory_correction_attempt_status",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "应用尝试状态"},
    )
    scheduler_run_id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, nullable=True, comment="调度运行标识快照"),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "开始应用时间"},
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "完成应用时间"},
    )
    failure_category: InventoryCorrectionFailureCategory | None = Field(
        default=None,
        sa_type=SAEnum(
            InventoryCorrectionFailureCategory,
            name="inventory_correction_failure_category",
        ),  # ty:ignore[invalid-argument-type]
        sa_column_kwargs={"comment": "失败类别"},
    )


class InventoryDailyReport(SQLModel, table=True):
    __tablename__ = "inventory_daily_report"
    __table_args__ = (
        CheckConstraint(
            "resolution_attempt_count >= 0 AND resolution_attempt_count <= 8",
            name="ck_inventory_daily_report_resolution_attempts",
        ),
        Index(
            "ix_inventory_daily_report_recipient_retry",
            "status",
            "next_recipient_attempt_at",
        ),
        UniqueConstraint(
            "processing_unit_id",
            "business_date",
            name="uq_inventory_daily_report_unit_date",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    processing_unit_id: uuid.UUID = Field(
        sa_column=Column(
            PGUUID(as_uuid=True),
            ForeignKey(
                "processing_unit.id",
                name="fk_inventory_daily_report_processing_unit",
                ondelete="RESTRICT",
            ),
            nullable=False,
        )
    )
    business_date: date
    processing_unit_name: str = Field(max_length=255)
    snapshot: dict[str, object] = Field(sa_type=JSONB)
    status: InventoryDailyReportStatus = Field(
        default=InventoryDailyReportStatus.PENDING,
        sa_type=SAEnum(
            InventoryDailyReportStatus, name="inventory_daily_report_status"
        ),  # ty:ignore[invalid-argument-type]
    )
    recipients_resolved_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    resolution_attempt_count: int = Field(default=0)
    next_recipient_attempt_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    last_error_category: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )


class InventoryDailyReportDelivery(SQLModel, table=True):
    __tablename__ = "inventory_daily_report_delivery"
    __table_args__ = (
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 8",
            name="ck_inventory_daily_report_delivery_attempts",
        ),
        Index(
            "ix_inventory_daily_report_delivery_retry",
            "status",
            "next_attempt_at",
        ),
        UniqueConstraint(
            "report_id",
            "email",
            name="uq_inventory_daily_report_delivery_report_email",
        ),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True),
    )
    report_id: int = Field(
        sa_column=Column(
            BigInteger,
            ForeignKey(
                "inventory_daily_report.id",
                name="fk_inventory_daily_report_delivery_report",
                ondelete="CASCADE",
            ),
            nullable=False,
        )
    )
    email: str = Field(max_length=320)
    status: InventoryDailyReportDeliveryStatus = Field(
        default=InventoryDailyReportDeliveryStatus.PENDING,
        sa_type=SAEnum(
            InventoryDailyReportDeliveryStatus,
            name="inventory_daily_report_delivery_status",
        ),  # ty:ignore[invalid-argument-type]
    )
    attempt_count: int = Field(default=0)
    next_attempt_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    last_error_category: str | None = Field(default=None, max_length=64)
    delivered_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # ty:ignore[invalid-argument-type]
    )

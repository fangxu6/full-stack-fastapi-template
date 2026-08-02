"""backfill Chinese PostgreSQL comments

Revision ID: 3e0ac19b57b1
Revises: b5c6d7e8f9a0
Create Date: 2026-08-02 10:35:41.244167

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "3e0ac19b57b1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


COMMENTS: dict[str, tuple[str, dict[str, str]]] = {
    "email_outbox": (
        "邮件发件箱",
        {
            "id": "邮件唯一标识",
            "kind": "邮件类别",
            "recipient": "收件人邮箱",
            "user_id": "关联用户标识",
            "subject": "邮件主题",
            "html_content": "富文本邮件正文",
            "status": "投递状态",
            "attempt_count": "投递尝试次数",
            "next_attempt_at": "下次投递时间",
            "lease_expires_at": "投递租约到期时间",
            "last_error_category": "最后错误类别",
            "delivered_at": "投递完成时间",
            "failed_at": "最终失败时间",
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
        },
    ),
    "iam_permission": (
        "权限定义",
        {
            "id": "权限唯一标识",
            "code": "权限代码",
            "group_name": "权限分组名称",
            "label": "权限显示名称",
            "description": "权限说明",
        },
    ),
    "iam_role": (
        "角色定义",
        {
            "id": "角色唯一标识",
            "code": "角色代码",
            "name": "角色名称",
            "description": "角色说明",
            "is_builtin": "是否内置角色",
            "is_active": "是否启用",
            "created_at": "创建时间",
            "updated_at": "更新时间",
        },
    ),
    "iam_role_permission": (
        "角色权限关联",
        {
            "role_id": "角色标识",
            "permission_id": "权限标识",
        },
    ),
    "iam_user_role": (
        "用户角色关联",
        {
            "user_id": "用户标识",
            "role_id": "角色标识",
            "assigned_at": "角色分配时间",
        },
    ),
    "inventory_daily_report": (
        "库存日报",
        {
            "id": "日报唯一标识",
            "processing_unit_id": "加工单位标识",
            "business_date": "业务日期",
            "processing_unit_name": "加工单位名称快照",
            "snapshot": "库存快照",
            "status": "日报状态",
            "recipients_resolved_at": "收件人解析时间",
            "resolution_attempt_count": "收件人解析尝试次数",
            "next_recipient_attempt_at": "下次收件人解析时间",
            "last_error_category": "最后错误类别",
            "created_at": "创建时间",
            "updated_at": "更新时间",
        },
    ),
    "inventory_daily_report_delivery": (
        "库存日报投递记录",
        {
            "id": "日报投递记录唯一标识",
            "report_id": "库存日报标识",
            "email": "收件人邮箱",
            "status": "投递状态",
            "attempt_count": "投递尝试次数",
            "next_attempt_at": "下次投递时间",
            "lease_expires_at": "投递租约到期时间",
            "last_error_category": "最后错误类别",
            "delivered_at": "投递完成时间",
            "created_at": "创建时间",
            "updated_at": "更新时间",
        },
    ),
    "inventory_document": (
        "库存单据",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "库存单据唯一标识",
            "document_type": "单据类型",
            "business_date": "业务日期",
            "processing_unit_id": "加工单位标识",
            "receiving_unit_id": "收货单位标识",
            "document_number": "单据编号",
            "remarks": "备注",
            "is_legacy": "是否历史导入数据",
        },
    ),
    "inventory_document_line": (
        "库存单据明细",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "单据明细唯一标识",
            "document_id": "库存单据标识",
            "line_no": "明细行号",
            "item_name": "货品名称",
            "item_code": "货品编码",
            "wool_content": "羊毛成分",
            "color_code": "色号",
            "dye_lot_no": "染缸号",
            "quantity_rolls": "卷数",
            "quantity_meters": "米数",
        },
    ),
    "inventory_import_batch": (
        "历史库存导入批次",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "导入批次唯一标识",
            "source_fingerprint": "源文件指纹",
            "raw_workbook_sha256": "原始工作簿哈希值",
            "finished_workbook_sha256": "完成工作簿哈希值",
            "importer_version": "导入器版本",
            "reconciliation_report": "对账报告",
            "imported_at": "导入时间",
        },
    ),
    "inventory_ledger_entry": (
        "库存台账流水",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "台账流水唯一标识",
            "ledger_kind": "台账类型",
            "movement_type": "库存变动类型",
            "business_date": "业务日期",
            "processing_unit_id": "加工单位标识",
            "document_line_id": "单据明细标识",
            "legacy_import_row_id": "历史导入行标识",
            "import_batch_id": "导入批次标识",
            "item_name": "货品名称",
            "item_code": "货品编码",
            "wool_content": "羊毛成分",
            "color_code": "色号",
            "dye_lot_no": "染缸号",
            "rolls_delta": "卷数变动",
            "meters_delta": "米数变动",
            "reason": "变动原因",
        },
    ),
    "item": (
        "业务条目",
        {
            "description": "条目描述",
            "title": "条目标题",
            "id": "条目唯一标识",
            "owner_id": "所属用户标识",
            "created_at": "创建时间",
        },
    ),
    "legacy_import_row": (
        "历史库存导入行",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "历史导入行唯一标识",
            "import_batch_id": "导入批次标识",
            "workbook_kind": "工作簿类型",
            "workbook_name": "工作簿名称",
            "worksheet_name": "工作表名称",
            "source_row_number": "源行号",
            "raw_cells": "原始单元格数据",
            "source_balance_snapshot": "源余额快照",
            "requires_cleanup": "是否需要清理",
        },
    ),
    "processing_unit": (
        "加工单位",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "加工单位唯一标识",
            "name": "加工单位名称",
            "normalized_name": "规范化加工单位名称",
            "is_active": "是否启用",
        },
    ),
    "receiving_unit": (
        "收货单位",
        {
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
            "id": "收货单位唯一标识",
            "name": "收货单位名称",
            "normalized_name": "规范化收货单位名称",
            "is_active": "是否启用",
        },
    ),
    "scheduler_job": (
        "调度任务",
        {
            "id": "调度任务唯一标识",
            "name": "任务名称",
            "class_path": "任务处理类路径",
            "cron_expression": "定时表达式",
            "config": "任务配置",
            "enabled": "是否启用",
            "next_run_at": "下次计划执行时间",
            "bootstrap_key": "内置任务标识",
            "run_failure_alerted_at": "执行失败告警时间",
            "overlap_alerted_at": "执行重叠告警时间",
            "configuration_alerted_at": "配置错误告警时间",
            "created_at": "创建时间",
            "created_by": "创建人标识",
            "updated_at": "更新时间",
            "updated_by": "更新人标识",
            "deleted_at": "删除时间",
        },
    ),
    "scheduler_run": (
        "调度任务运行记录",
        {
            "id": "运行记录唯一标识",
            "job_id": "调度任务标识",
            "status": "运行状态",
            "trigger": "触发方式",
            "planned_at": "计划执行时间",
            "class_path": "执行类路径快照",
            "config": "执行配置快照",
            "requested_by": "手动触发用户标识",
            "created_at": "创建时间",
            "started_at": "开始执行时间",
            "finished_at": "完成执行时间",
            "lease_expires_at": "执行租约到期时间",
            "attempt_count": "执行尝试次数",
            "error_category": "错误类别",
            "error_summary": "错误摘要",
            "next_dispatch_at": "下次派发时间",
        },
    ),
    "user": (
        "用户账户",
        {
            "email": "用户邮箱",
            "is_active": "是否启用",
            "is_superuser": "是否超级管理员",
            "full_name": "用户姓名",
            "hashed_password": "密码哈希",
            "id": "用户唯一标识",
            "created_at": "创建时间",
            "is_system_actor": "是否系统服务账号",
            "system_actor_key": "系统服务账号标识",
        },
    ),
}


def _set_comments(*, clear: bool) -> None:
    for table_name, (table_comment, column_comments) in COMMENTS.items():
        op.create_table_comment(
            table_name,
            None if clear else table_comment,
            existing_comment=table_comment if clear else None,
        )
        for column_name, column_comment in column_comments.items():
            op.alter_column(
                table_name,
                column_name,
                comment=None if clear else column_comment,
                existing_comment=column_comment if clear else None,
            )


def upgrade() -> None:
    _set_comments(clear=False)


def downgrade() -> None:
    _set_comments(clear=True)

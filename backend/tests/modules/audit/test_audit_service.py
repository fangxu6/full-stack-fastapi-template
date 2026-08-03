from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.db import engine
from app.models import AuditEvent
from app.modules.audit import service


def test_cleanup_expired_events_keeps_the_retention_boundary(db: Session) -> None:
    now = datetime(2026, 8, 3, tzinfo=UTC)
    expired = AuditEvent(
        occurred_at=now - timedelta(days=366),
        action="test.expired",
        resource_type="test",
        resource_id="expired",
        changes={},
    )
    retained = AuditEvent(
        occurred_at=now - timedelta(days=365),
        action="test.retained",
        resource_type="test",
        resource_id="retained",
        changes={},
    )
    db.add_all([expired, retained])
    db.commit()

    assert service.cleanup_expired_events(session=db, now=now) == 1
    db.commit()

    events = list(
        db.exec(
            select(AuditEvent)
            .where(AuditEvent.resource_type == "test")
            .order_by(AuditEvent.resource_id)
        ).all()
    )
    assert [event.resource_id for event in events] == ["retained"]


def test_audit_event_schema_has_chinese_comments(db: Session) -> None:
    del db
    with engine.connect() as connection:
        table_comment = connection.execute(
            text("SELECT obj_description('audit_event'::regclass, 'pg_class')")
        ).scalar_one()
        column_comments = dict(
            connection.execute(
                text(
                    "SELECT a.attname, col_description(a.attrelid, a.attnum) "
                    "FROM pg_attribute AS a "
                    "WHERE a.attrelid = 'audit_event'::regclass "
                    "AND a.attnum > 0 AND NOT a.attisdropped"
                )
            ).all()
        )

    assert table_comment == "语义变更审计事件"
    assert column_comments == {
        "id": "审计事件唯一标识",
        "occurred_at": "事件发生时间",
        "actor_user_id": "操作者用户标识",
        "request_id": "请求关联标识",
        "action": "事件动作",
        "resource_type": "资源类型",
        "resource_id": "资源标识",
        "changes": "变更摘要",
    }

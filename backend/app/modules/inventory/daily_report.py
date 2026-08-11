import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models.inventory import (
    InventoryDailyReport,
    InventoryDailyReportDelivery,
    InventoryDailyReportDeliveryStatus,
    InventoryDailyReportStatus,
    InventoryLedgerKind,
    ProcessingUnit,
)
from app.modules.inventory.config import inventory_settings
from app.modules.inventory.service import list_balances_as_of
from app.utils import render_email_template, send_email

DAILY_REPORT_TIMEZONE = ZoneInfo("Asia/Shanghai")
DAILY_REPORT_HOUR = 8
DAILY_REPORT_GRACE_MINUTES = 15
DAILY_REPORT_MAX_ATTEMPTS = 8
DAILY_REPORT_RETRY_DELAY = timedelta(minutes=15)
DAILY_REPORT_LEASE_DURATION = timedelta(
    seconds=settings.CELERY_VISIBILITY_TIMEOUT_SECONDS
)


@dataclass(frozen=True)
class DeliveryPayload:
    delivery_id: int
    email: str
    subject: str
    html_content: str
    lease_expires_at: datetime


def _require_id(value: int | None, name: str) -> int:
    if value is None:
        raise RuntimeError(f"{name} must be persisted before scheduling delivery")
    return value


def _utc_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("daily report timestamps must be timezone-aware")
    return now.astimezone(UTC)


def _snapshot(
    *, session: Session, processing_unit_id: uuid.UUID, business_date: date
) -> dict[str, object]:
    raw = list_balances_as_of(
        session=session,
        ledger_kind=InventoryLedgerKind.RAW,
        processing_unit_id=processing_unit_id,
        business_date=business_date,
    )
    finished = list_balances_as_of(
        session=session,
        ledger_kind=InventoryLedgerKind.FINISHED,
        processing_unit_id=processing_unit_id,
        business_date=business_date,
    )
    return {
        "raw": [
            balance.model_dump(mode="json", exclude={"processing_unit_id"})
            for balance in raw
        ],
        "finished": [
            balance.model_dump(mode="json", exclude={"processing_unit_id"})
            for balance in finished
        ],
    }


def report_date_for_scheduled_run(now: datetime | None = None) -> date | None:
    current = _utc_now(now).astimezone(DAILY_REPORT_TIMEZONE)
    start = time(hour=DAILY_REPORT_HOUR)
    end = time(hour=DAILY_REPORT_HOUR, minute=DAILY_REPORT_GRACE_MINUTES)
    if not start <= current.timetz().replace(tzinfo=None) < end:
        return None
    return current.date() - timedelta(days=1)


def create_daily_reports(*, session: Session, now: datetime | None = None) -> list[int]:
    business_date = report_date_for_scheduled_run(now)
    if business_date is None:
        return []
    current = _utc_now(now)
    units = list(
        session.exec(
            select(ProcessingUnit).where(
                ProcessingUnit.deleted_at.is_(None),  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
                ProcessingUnit.is_active == True,  # noqa: E712
            )
        ).all()
    )
    report_ids: list[int] = []
    for unit in units:
        existing = session.exec(
            select(InventoryDailyReport.id).where(
                InventoryDailyReport.processing_unit_id == unit.id,
                InventoryDailyReport.business_date == business_date,
            )
        ).first()
        if existing is not None:
            continue
        report = InventoryDailyReport(
            processing_unit_id=unit.id,
            business_date=business_date,
            processing_unit_name=unit.name,
            snapshot=_snapshot(
                session=session,
                processing_unit_id=unit.id,
                business_date=business_date,
            ),
            next_recipient_attempt_at=current,
            created_at=current,
            updated_at=current,
        )
        try:
            with session.begin_nested():
                session.add(report)
                session.flush()
                report_ids.append(_require_id(report.id, "daily report"))
        except IntegrityError:
            continue
    session.commit()
    return report_ids


def _mark_missing_recipients(report: InventoryDailyReport, now: datetime) -> None:
    report.resolution_attempt_count += 1
    report.last_error_category = "RECIPIENTS_NOT_CONFIGURED"
    report.updated_at = now
    if report.resolution_attempt_count >= DAILY_REPORT_MAX_ATTEMPTS:
        report.status = InventoryDailyReportStatus.FAILED
        return
    report.status = InventoryDailyReportStatus.RETRY_WAIT
    report.next_recipient_attempt_at = now + DAILY_REPORT_RETRY_DELAY


def _resolve_report_recipients(
    *, session: Session, report: InventoryDailyReport, now: datetime
) -> None:
    recipients = inventory_settings.INVENTORY_DAILY_REPORT_RECIPIENTS.get(
        report.processing_unit_id, []
    )
    if not recipients:
        _mark_missing_recipients(report, now)
        session.add(report)
        return
    report_id = _require_id(report.id, "daily report")
    for recipient in recipients:
        session.add(
            InventoryDailyReportDelivery(
                report_id=report_id,
                email=str(recipient),
                next_attempt_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    report.recipients_resolved_at = now
    report.last_error_category = None
    report.status = InventoryDailyReportStatus.PENDING
    report.updated_at = now
    session.add(report)


def _refresh_report_status(
    *, session: Session, report: InventoryDailyReport, now: datetime
) -> None:
    deliveries = list(
        session.exec(
            select(InventoryDailyReportDelivery.status).where(
                InventoryDailyReportDelivery.report_id
                == _require_id(report.id, "daily report")
            )
        ).all()
    )
    if not deliveries:
        return
    if all(
        status is InventoryDailyReportDeliveryStatus.DELIVERED for status in deliveries
    ):
        report.status = InventoryDailyReportStatus.DELIVERED
        report.last_error_category = None
    elif any(
        status
        in {
            InventoryDailyReportDeliveryStatus.PENDING,
            InventoryDailyReportDeliveryStatus.DELIVERING,
            InventoryDailyReportDeliveryStatus.RETRY_WAIT,
        }
        for status in deliveries
    ):
        report.status = InventoryDailyReportStatus.RETRY_WAIT
    else:
        report.status = InventoryDailyReportStatus.FAILED
    report.updated_at = now
    session.add(report)


def queue_due_daily_report_deliveries(
    *, session: Session, now: datetime | None = None
) -> list[int]:
    current = _utc_now(now)
    reports = list(
        session.exec(
            select(InventoryDailyReport)
            .where(
                InventoryDailyReport.recipients_resolved_at.is_(None),  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
                InventoryDailyReport.status != InventoryDailyReportStatus.FAILED,
                InventoryDailyReport.next_recipient_attempt_at <= current,
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    for report in reports:
        _resolve_report_recipients(session=session, report=report, now=current)
    expired = list(
        session.exec(
            select(InventoryDailyReportDelivery)
            .where(
                InventoryDailyReportDelivery.status
                == InventoryDailyReportDeliveryStatus.DELIVERING,
                InventoryDailyReportDelivery.lease_expires_at.is_not(None),  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
                InventoryDailyReportDelivery.lease_expires_at <= current,  # type: ignore[operator]  # ty:ignore[unsupported-operator]
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    for delivery in expired:
        if delivery.attempt_count >= DAILY_REPORT_MAX_ATTEMPTS:
            delivery.status = InventoryDailyReportDeliveryStatus.FAILED
        else:
            delivery.status = InventoryDailyReportDeliveryStatus.RETRY_WAIT
            delivery.next_attempt_at = current
        delivery.lease_expires_at = None
        delivery.last_error_category = "DELIVERY_LEASE_EXPIRED"
        delivery.updated_at = current
        session.add(delivery)
        delivery_report = session.get(InventoryDailyReport, delivery.report_id)
        if delivery_report:
            _refresh_report_status(session=session, report=delivery_report, now=current)
    due_ids = list(
        session.exec(
            select(InventoryDailyReportDelivery.id).where(
                InventoryDailyReportDelivery.status.in_(  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
                    [
                        InventoryDailyReportDeliveryStatus.PENDING,
                        InventoryDailyReportDeliveryStatus.RETRY_WAIT,
                    ]
                ),
                InventoryDailyReportDelivery.next_attempt_at <= current,
            )
        ).all()
    )
    session.commit()
    return [delivery_id for delivery_id in due_ids if delivery_id is not None]


def _delivery_payload(
    *, session: Session, delivery_id: int, now: datetime
) -> DeliveryPayload | None:
    delivery = session.exec(
        select(InventoryDailyReportDelivery)
        .where(InventoryDailyReportDelivery.id == delivery_id)
        .with_for_update()
    ).one_or_none()
    if delivery is None or delivery.status in {
        InventoryDailyReportDeliveryStatus.DELIVERED,
        InventoryDailyReportDeliveryStatus.FAILED,
    }:
        return None
    if (
        delivery.status is InventoryDailyReportDeliveryStatus.DELIVERING
        and delivery.lease_expires_at is not None
        and delivery.lease_expires_at > now
    ):
        return None
    if (
        delivery.status
        in {
            InventoryDailyReportDeliveryStatus.PENDING,
            InventoryDailyReportDeliveryStatus.RETRY_WAIT,
        }
        and delivery.next_attempt_at > now
    ):
        return None
    report = session.get(InventoryDailyReport, delivery.report_id)
    if report is None:
        return None
    if delivery.attempt_count >= DAILY_REPORT_MAX_ATTEMPTS:
        delivery.status = InventoryDailyReportDeliveryStatus.FAILED
        delivery.last_error_category = "MAX_ATTEMPTS_EXCEEDED"
        delivery.lease_expires_at = None
        delivery.updated_at = now
        session.add(delivery)
        _refresh_report_status(session=session, report=report, now=now)
        return None
    delivery.attempt_count += 1
    delivery.status = InventoryDailyReportDeliveryStatus.DELIVERING
    delivery.lease_expires_at = now + DAILY_REPORT_LEASE_DURATION
    delivery.updated_at = now
    session.add(delivery)
    assert delivery.lease_expires_at is not None
    return DeliveryPayload(
        delivery_id=delivery_id,
        email=delivery.email,
        subject=f"{report.business_date.isoformat()} 库存日报 - {report.processing_unit_name}",
        html_content=render_email_template(
            template_name="inventory_daily_report.html",
            context={
                "business_date": report.business_date.isoformat(),
                "processing_unit_name": report.processing_unit_name,
                "raw_rows": report.snapshot["raw"],
                "finished_rows": report.snapshot["finished"],
            },
        ),
        lease_expires_at=delivery.lease_expires_at,
    )


def _locked_active_delivery(
    *, session: Session, payload: DeliveryPayload
) -> InventoryDailyReportDelivery | None:
    delivery = session.exec(
        select(InventoryDailyReportDelivery)
        .where(InventoryDailyReportDelivery.id == payload.delivery_id)
        .with_for_update()
    ).one_or_none()
    if (
        delivery is None
        or delivery.status is not InventoryDailyReportDeliveryStatus.DELIVERING
        or delivery.lease_expires_at != payload.lease_expires_at
    ):
        return None
    return delivery


def _complete_delivery(
    *, session: Session, payload: DeliveryPayload, now: datetime
) -> None:
    delivery = _locked_active_delivery(session=session, payload=payload)
    if delivery is None:
        return
    delivery.status = InventoryDailyReportDeliveryStatus.DELIVERED
    delivery.delivered_at = now
    delivery.lease_expires_at = None
    delivery.last_error_category = None
    delivery.updated_at = now
    session.add(delivery)
    report = session.get(InventoryDailyReport, delivery.report_id)
    if report:
        _refresh_report_status(session=session, report=report, now=now)


def _fail_delivery(
    *,
    session: Session,
    payload: DeliveryPayload,
    error_category: str,
    now: datetime,
) -> None:
    delivery = _locked_active_delivery(session=session, payload=payload)
    if delivery is None:
        return
    delivery.last_error_category = error_category
    delivery.lease_expires_at = None
    delivery.updated_at = now
    if delivery.attempt_count >= DAILY_REPORT_MAX_ATTEMPTS:
        delivery.status = InventoryDailyReportDeliveryStatus.FAILED
    else:
        delivery.status = InventoryDailyReportDeliveryStatus.RETRY_WAIT
        delivery.next_attempt_at = now + DAILY_REPORT_RETRY_DELAY
    session.add(delivery)
    report = session.get(InventoryDailyReport, delivery.report_id)
    if report:
        _refresh_report_status(session=session, report=report, now=now)


def deliver_daily_report_email(delivery_id: int) -> None:
    if not isinstance(delivery_id, int):
        raise ValueError("inventory daily report delivery id must be an integer")
    now = _utc_now()
    with Session(engine) as session:
        payload = _delivery_payload(session=session, delivery_id=delivery_id, now=now)
        session.commit()
    if payload is None:
        return
    error_category: str | None = None
    try:
        if not settings.emails_enabled:
            error_category = "SMTP_NOT_CONFIGURED"
        else:
            send_email(
                email_to=payload.email,
                subject=payload.subject,
                html_content=payload.html_content,
            )
    except Exception:
        error_category = "SMTP_DELIVERY_FAILED"
    with Session(engine) as session:
        if error_category is None:
            _complete_delivery(session=session, payload=payload, now=_utc_now())
        else:
            _fail_delivery(
                session=session,
                payload=payload,
                error_category=error_category,
                now=_utc_now(),
            )
        session.commit()

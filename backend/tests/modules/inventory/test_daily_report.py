import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TypedDict, cast
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    InventoryDailyReport,
    InventoryDailyReportDelivery,
    InventoryDocument,
    InventoryDocumentLine,
    InventoryLedgerEntry,
    ProcessingUnit,
)
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryDailyReportDeliveryStatus,
    InventoryDailyReportStatus,
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
)
from app.models.user import User
from app.modules.inventory.config import inventory_settings
from app.modules.inventory.daily_report import (
    DAILY_REPORT_MAX_ATTEMPTS,
    DAILY_REPORT_TIMEZONE,
    create_daily_reports,
    deliver_daily_report_email,
    queue_due_daily_report_deliveries,
    report_date_for_scheduled_run,
)
from tests.utils.user import create_random_user


class AuditValues(TypedDict):
    created_by: uuid.UUID
    updated_by: uuid.UUID


def _audit(user: User) -> AuditValues:
    if user.id is None:
        raise RuntimeError("test user must be persisted")
    return {"created_by": user.id, "updated_by": user.id}


def _create_processing_unit(
    *, session: Session, user: User, active: bool = True
) -> ProcessingUnit:
    name = f"Daily report unit {uuid.uuid4()}"
    unit = ProcessingUnit(
        name=name,
        normalized_name=name,
        is_active=active,
        **_audit(user),
    )
    session.add(unit)
    session.commit()
    session.refresh(unit)
    return unit


def _add_ledger(
    *,
    session: Session,
    user: User,
    unit: ProcessingUnit,
    ledger_kind: InventoryLedgerKind,
    business_date: date,
    rolls_delta: Decimal,
    meters_delta: Decimal = Decimal("0"),
) -> None:
    is_finished = ledger_kind is InventoryLedgerKind.FINISHED
    document = InventoryDocument(
        document_type=(
            InventoryDocumentType.FINISHED_RECEIPT
            if is_finished
            else InventoryDocumentType.RAW_RECEIPT
        ),
        business_date=business_date,
        processing_unit_id=unit.id,
        document_number=f"daily-report-{uuid.uuid4()}",
        **_audit(user),
    )
    session.add(document)
    session.flush()
    line = InventoryDocumentLine(
        document_id=document.id,
        line_no=1,
        item_name="Finished fabric" if is_finished else "Raw fabric",
        item_code="F-001" if is_finished else "R-001",
        wool_content="100% wool",
        color_code="blue" if is_finished else None,
        dye_lot_no="lot-1" if is_finished else None,
        quantity_rolls=abs(rolls_delta),
        quantity_meters=abs(meters_delta) if is_finished else None,
        **_audit(user),
    )
    session.add(line)
    session.flush()
    session.add(
        InventoryLedgerEntry(
            ledger_kind=ledger_kind,
            movement_type=(
                InventoryMovementType.FINISHED_RECEIPT
                if is_finished
                else InventoryMovementType.RAW_RECEIPT
            ),
            business_date=business_date,
            processing_unit_id=unit.id,
            document_line_id=line.id,
            item_name=line.item_name,
            item_code=line.item_code,
            wool_content=line.wool_content,
            color_code=line.color_code,
            dye_lot_no=line.dye_lot_no,
            rolls_delta=rolls_delta,
            meters_delta=meters_delta,
            **_audit(user),
        )
    )
    session.commit()


def _scheduled_now(value: date) -> datetime:
    return datetime.combine(value, time(8, 1), DAILY_REPORT_TIMEZONE).astimezone(UTC)


def _report_for_unit(session: Session, unit: ProcessingUnit) -> InventoryDailyReport:
    report = session.exec(
        select(InventoryDailyReport).where(
            InventoryDailyReport.processing_unit_id == unit.id
        )
    ).one()
    return report


def _set_delivery_due(session: Session, delivery_id: int) -> None:
    delivery = session.get(InventoryDailyReportDelivery, delivery_id)
    if delivery is None:
        raise RuntimeError("daily report delivery was not created")
    delivery.next_attempt_at = get_datetime_utc() - timedelta(seconds=1)
    session.add(delivery)
    session.commit()


def _enable_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "sender@example.com")


def test_report_date_uses_previous_calendar_day_and_grace_window() -> None:
    assert report_date_for_scheduled_run(
        datetime(2026, 7, 27, 0, 1, tzinfo=UTC)
    ) == date(2026, 7, 26)
    assert (
        report_date_for_scheduled_run(datetime(2026, 7, 27, 0, 15, tzinfo=UTC)) is None
    )


def test_daily_reports_snapshot_cutoff_and_include_empty_active_units(
    db: Session,
) -> None:
    user = create_random_user(db)
    stocked_unit = _create_processing_unit(session=db, user=user)
    empty_unit = _create_processing_unit(session=db, user=user)
    _create_processing_unit(session=db, user=user, active=False)
    report_day = date(2026, 7, 24)
    _add_ledger(
        session=db,
        user=user,
        unit=stocked_unit,
        ledger_kind=InventoryLedgerKind.RAW,
        business_date=report_day,
        rolls_delta=Decimal("10"),
    )
    _add_ledger(
        session=db,
        user=user,
        unit=stocked_unit,
        ledger_kind=InventoryLedgerKind.FINISHED,
        business_date=report_day,
        rolls_delta=Decimal("3"),
        meters_delta=Decimal("120"),
    )
    _add_ledger(
        session=db,
        user=user,
        unit=stocked_unit,
        ledger_kind=InventoryLedgerKind.RAW,
        business_date=date(2026, 7, 25),
        rolls_delta=Decimal("2"),
    )

    created = create_daily_reports(session=db, now=_scheduled_now(date(2026, 7, 25)))

    stocked_report = _report_for_unit(db, stocked_unit)
    empty_report = _report_for_unit(db, empty_unit)
    assert stocked_report.id in created
    assert empty_report.id in created
    assert stocked_report.snapshot["raw"] == [
        {
            "item_name": "Raw fabric",
            "item_code": "R-001",
            "wool_content": "100% wool",
            "color_code": None,
            "dye_lot_no": None,
            "rolls_balance": "10.00",
            "meters_balance": "0.000",
        }
    ]
    finished_snapshot = stocked_report.snapshot["finished"]
    assert isinstance(finished_snapshot, list)
    finished_row = cast(dict[str, object], finished_snapshot[0])
    assert finished_row["meters_balance"] == "120.000"
    assert empty_report.snapshot == {"raw": [], "finished": []}

    _add_ledger(
        session=db,
        user=user,
        unit=stocked_unit,
        ledger_kind=InventoryLedgerKind.RAW,
        business_date=report_day,
        rolls_delta=Decimal("7"),
    )
    db.refresh(stocked_report)
    raw_snapshot = stocked_report.snapshot["raw"]
    assert isinstance(raw_snapshot, list)
    raw_row = cast(dict[str, object], raw_snapshot[0])
    assert raw_row["rolls_balance"] == "10.00"
    assert create_daily_reports(session=db, now=_scheduled_now(date(2026, 7, 25))) == []


def test_missing_recipients_retry_after_configuration_is_added(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = create_random_user(db)
    unit = _create_processing_unit(session=db, user=user)
    now = _scheduled_now(date(2026, 7, 25))
    create_daily_reports(session=db, now=now)
    monkeypatch.setattr(inventory_settings, "INVENTORY_DAILY_REPORT_RECIPIENTS", {})

    assert queue_due_daily_report_deliveries(session=db, now=now) == []
    report = _report_for_unit(db, unit)
    assert report.status is InventoryDailyReportStatus.RETRY_WAIT
    assert report.resolution_attempt_count == 1
    monkeypatch.setattr(
        inventory_settings,
        "INVENTORY_DAILY_REPORT_RECIPIENTS",
        {unit.id: ["daily@example.com"]},
    )

    delivery_ids = queue_due_daily_report_deliveries(
        session=db, now=now + timedelta(minutes=15)
    )

    assert len(delivery_ids) == 1
    db.refresh(report)
    assert report.recipients_resolved_at is not None
    monkeypatch.setattr(
        inventory_settings,
        "INVENTORY_DAILY_REPORT_RECIPIENTS",
        {unit.id: ["changed@example.com"]},
    )
    deliveries = list(
        db.exec(
            select(InventoryDailyReportDelivery).where(
                InventoryDailyReportDelivery.report_id == report.id
            )
        ).all()
    )
    assert [delivery.email for delivery in deliveries] == ["daily@example.com"]


def test_delivery_retries_only_the_failed_recipient(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = create_random_user(db)
    unit = _create_processing_unit(session=db, user=user)
    now = _scheduled_now(date(2026, 7, 25))
    create_daily_reports(session=db, now=now)
    monkeypatch.setattr(
        inventory_settings,
        "INVENTORY_DAILY_REPORT_RECIPIENTS",
        {unit.id: ["good@example.com", "bad@example.com"]},
    )
    _enable_email(monkeypatch)
    delivery_ids = queue_due_daily_report_deliveries(session=db, now=now)
    for delivery_id in delivery_ids:
        _set_delivery_due(db, delivery_id)

    sent_to: list[str] = []

    def send(email_to: str, **_: object) -> None:
        sent_to.append(email_to)
        if email_to == "bad@example.com":
            raise RuntimeError("smtp rejected recipient")

    with patch("app.modules.inventory.daily_report.send_email", side_effect=send):
        for delivery_id in delivery_ids:
            deliver_daily_report_email(delivery_id)
        bad_delivery = db.exec(
            select(InventoryDailyReportDelivery).where(
                InventoryDailyReportDelivery.email == "bad@example.com"
            )
        ).one()
        _set_delivery_due(db, bad_delivery.id or 0)
        deliver_daily_report_email(bad_delivery.id or 0)

    assert sent_to.count("good@example.com") == 1
    assert sent_to.count("bad@example.com") == 2
    good_delivery = db.exec(
        select(InventoryDailyReportDelivery).where(
            InventoryDailyReportDelivery.email == "good@example.com"
        )
    ).one()
    db.refresh(bad_delivery)
    assert good_delivery.status is InventoryDailyReportDeliveryStatus.DELIVERED
    assert bad_delivery.status is InventoryDailyReportDeliveryStatus.RETRY_WAIT
    assert bad_delivery.attempt_count == 2


def test_delivery_stops_after_eight_attempts(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = create_random_user(db)
    unit = _create_processing_unit(session=db, user=user)
    now = _scheduled_now(date(2026, 7, 25))
    create_daily_reports(session=db, now=now)
    monkeypatch.setattr(
        inventory_settings,
        "INVENTORY_DAILY_REPORT_RECIPIENTS",
        {unit.id: ["daily@example.com"]},
    )
    _enable_email(monkeypatch)
    delivery_id = queue_due_daily_report_deliveries(session=db, now=now)[0]

    with patch(
        "app.modules.inventory.daily_report.send_email",
        side_effect=RuntimeError("smtp unavailable"),
    ) as send_email:
        for _ in range(DAILY_REPORT_MAX_ATTEMPTS):
            _set_delivery_due(db, delivery_id)
            deliver_daily_report_email(delivery_id)
        deliver_daily_report_email(delivery_id)

    db.expire_all()
    delivery = db.get(InventoryDailyReportDelivery, delivery_id)
    assert delivery is not None
    assert delivery.status is InventoryDailyReportDeliveryStatus.FAILED
    assert delivery.attempt_count == DAILY_REPORT_MAX_ATTEMPTS
    assert send_email.call_count == DAILY_REPORT_MAX_ATTEMPTS

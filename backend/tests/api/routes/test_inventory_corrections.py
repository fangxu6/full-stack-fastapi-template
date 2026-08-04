import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.audit import require_system_actor
from app.core.config import settings
from app.models import (
    AuditEvent,
    InventoryCorrectionAttempt,
    InventoryCorrectionWorkItem,
    InventoryDocument,
)
from app.models.base import get_datetime_utc
from app.models.inventory import (
    InventoryCorrectionAttemptStatus,
    InventoryCorrectionFailureCategory,
    InventoryCorrectionRequestStatus,
    InventoryCorrectionWorkItemStatus,
)
from app.models.scheduler import SchedulerRunTrigger
from app.modules.inventory.scheduled_tasks import InventoryCorrectionApplyTask
from app.modules.scheduler.contracts import ScheduledTaskConfig, ScheduledTaskContext

INVENTORY_PATH = f"{settings.API_V1_STR}/inventory"


def _create_raw_receipt(
    client: TestClient,
    headers: dict[str, str],
    *,
    processing_unit_id: str,
    item_code: str,
    quantity_rolls: str,
) -> tuple[dict[str, object], dict[str, object]]:
    document = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit_id,
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Correction fabric",
                "item_code": item_code,
                "wool_content": "100% wool",
                "quantity_rolls": quantity_rolls,
            }
        ],
    }
    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=headers, json=document
    )
    assert response.status_code == 200, response.json()
    return document, response.json()


def _create_processing_unit(
    client: TestClient, headers: dict[str, str]
) -> dict[str, str]:
    response = client.post(
        f"{INVENTORY_PATH}/processing-units",
        headers=headers,
        json={"name": f"Correction unit {uuid.uuid4()}"},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _correction_payload(
    *,
    document: dict[str, object],
    created: dict[str, object],
    quantity_rolls: str,
) -> dict[str, object]:
    proposal = {
        **document,
        "document_number": f"C-{uuid.uuid4()}",
        "lines": [{**document["lines"][0], "quantity_rolls": quantity_rolls}],
    }
    return {
        "document_id": created["id"],
        "operation": "UPDATE_DOCUMENT",
        "expected_updated_at": created["updated_at"],
        "proposal": proposal,
        "reason": "Correct the saved inventory document.",
    }


def _run_correction_executor(db: Session, *, run_id: int) -> None:
    now = get_datetime_utc()
    InventoryCorrectionApplyTask().run(
        context=ScheduledTaskContext(
            run_id=run_id,
            actor_id=require_system_actor(session=db),
            trigger=SchedulerRunTrigger.SCHEDULED,
            planned_at=now,
            started_at=now,
        ),
        config=ScheduledTaskConfig(),
    )


def test_self_reviewed_correction_is_applied_by_scheduler(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_code = f"C-{uuid.uuid4()}"
    document, created = _create_raw_receipt(
        client,
        superuser_token_headers,
        processing_unit_id=processing_unit["id"],
        item_code=item_code,
        quantity_rolls="5",
    )
    created_request = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json=_correction_payload(
            document=document,
            created=created,
            quantity_rolls="3",
        ),
    )
    assert created_request.status_code == 201, created_request.json()
    request_id = created_request.json()["id"]
    assert created_request.json()["status"] == "PENDING_REVIEW"

    approved = client.post(
        f"{INVENTORY_PATH}/correction-requests/{request_id}/approve",
        headers=superuser_token_headers,
    )
    assert approved.status_code == 200, approved.json()
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["work_item"]["status"] == "APPROVED_PENDING_APPLY"
    assert approved.json()["work_item"]["attempts"][0]["status"] == "PENDING"

    duplicate = client.post(
        f"{INVENTORY_PATH}/correction-requests/{request_id}/approve",
        headers=superuser_token_headers,
    )
    assert duplicate.status_code == 409

    _run_correction_executor(db, run_id=1001)
    db.expire_all()
    detail = client.get(
        f"{INVENTORY_PATH}/correction-requests/{request_id}",
        headers=superuser_token_headers,
    )
    assert detail.status_code == 200, detail.json()
    assert detail.json()["status"] == "APPLIED"
    assert detail.json()["work_item"]["status"] == "SUCCEEDED"
    assert detail.json()["work_item"]["attempts"][0]["status"] == "SUCCEEDED"
    balances = client.get(
        f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers
    )
    balance = next(
        item for item in balances.json()["data"] if item["item_code"] == item_code
    )
    assert balance["rolls_balance"] == "3.00"
    applied_event = db.exec(
        select(AuditEvent).where(AuditEvent.action == "inventory.correction.applied")
    ).one()
    assert applied_event.resource_id == str(request_id)
    assert set(applied_event.changes) == {
        "operation",
        "document_id",
        "proposal_hash",
        "work_item_id",
        "attempt_sequence",
    }
    assert "reason" not in applied_event.changes
    _run_correction_executor(db, run_id=1003)
    repeated = client.get(
        f"{INVENTORY_PATH}/correction-requests/{request_id}",
        headers=superuser_token_headers,
    )
    assert len(repeated.json()["work_item"]["attempts"]) == 1


def test_correction_validation_and_stale_approval(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    document, created = _create_raw_receipt(
        client,
        superuser_token_headers,
        processing_unit_id=processing_unit["id"],
        item_code=f"S-{uuid.uuid4()}",
        quantity_rolls="5",
    )
    payload = _correction_payload(
        document=document,
        created=created,
        quantity_rolls="3",
    )
    invalid = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json={**payload, "expected_updated_at": "2026-08-04T12:00:00"},
    )
    assert invalid.status_code == 422
    invalid_reason = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json={**payload, "reason": "   ", "unexpected": True},
    )
    assert invalid_reason.status_code == 422

    created_request = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json=payload,
    )
    assert created_request.status_code == 201, created_request.json()
    request_id = created_request.json()["id"]
    target = db.get(InventoryDocument, uuid.UUID(str(created["id"])))
    assert target is not None
    target.remarks = "Changed after submission"
    db.add(target)
    db.commit()

    stale = client.post(
        f"{INVENTORY_PATH}/correction-requests/{request_id}/approve",
        headers=superuser_token_headers,
    )
    assert stale.status_code == 200, stale.json()
    assert stale.json()["status"] == "STALE"
    assert stale.json()["work_item"] is None


def test_terminal_failure_can_be_recovered_only_after_active_request_is_closed(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    assert (
        client.get(
            f"{INVENTORY_PATH}/correction-requests/review-queue",
            headers=normal_user_token_headers,
        ).status_code
        == 403
    )
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_code = f"F-{uuid.uuid4()}"
    document, created = _create_raw_receipt(
        client,
        superuser_token_headers,
        processing_unit_id=processing_unit["id"],
        item_code=item_code,
        quantity_rolls="5",
    )
    returned = client.post(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        json={
            **document,
            "document_type": "RAW_RETURN",
            "document_number": f"RET-{uuid.uuid4()}",
        },
    )
    assert returned.status_code == 200, returned.json()
    request = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json=_correction_payload(
            document=document,
            created=created,
            quantity_rolls="1",
        ),
    )
    assert request.status_code == 201, request.json()
    request_id = request.json()["id"]
    assert (
        client.post(
            f"{INVENTORY_PATH}/correction-requests/{request_id}/approve",
            headers=superuser_token_headers,
        ).status_code
        == 200
    )
    _run_correction_executor(db, run_id=1002)
    db.expire_all()
    failed = client.get(
        f"{INVENTORY_PATH}/correction-requests/{request_id}",
        headers=superuser_token_headers,
    )
    assert failed.status_code == 200, failed.json()
    work_item_id = failed.json()["work_item"]["id"]
    assert failed.json()["status"] == "APPLICATION_FAILED"
    assert failed.json()["work_item"]["status"] == "TERMINAL_FAILED"
    assert failed.json()["work_item"]["terminal_failure_category"] == "NEGATIVE_BALANCE"

    pending = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json=_correction_payload(
            document=document,
            created=created,
            quantity_rolls="2",
        ),
    )
    assert pending.status_code == 201, pending.json()
    blocked = client.post(
        f"{INVENTORY_PATH}/correction-work-items/{work_item_id}/recover",
        headers=superuser_token_headers,
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "INVENTORY_CORRECTION_ACTIVE_REQUEST"
    assert (
        client.post(
            f"{INVENTORY_PATH}/correction-requests/{pending.json()['id']}/withdraw",
            headers=superuser_token_headers,
        ).status_code
        == 200
    )
    recovered = client.post(
        f"{INVENTORY_PATH}/correction-work-items/{work_item_id}/recover",
        headers=superuser_token_headers,
    )
    assert recovered.status_code == 202, recovered.json()
    assert recovered.json()["status"] == "APPROVED_PENDING_APPLY"
    assert recovered.json()["attempts"][-1]["origin"] == "RECOVERY"
    assert recovered.json()["attempts"][-1]["status"] == "PENDING"


def test_expired_correction_lease_is_terminal_and_not_reapplied(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    document, created = _create_raw_receipt(
        client,
        superuser_token_headers,
        processing_unit_id=processing_unit["id"],
        item_code=f"L-{uuid.uuid4()}",
        quantity_rolls="5",
    )
    request = client.post(
        f"{INVENTORY_PATH}/correction-requests",
        headers=superuser_token_headers,
        json=_correction_payload(
            document=document,
            created=created,
            quantity_rolls="3",
        ),
    )
    assert request.status_code == 201, request.json()
    request_id = request.json()["id"]
    approved = client.post(
        f"{INVENTORY_PATH}/correction-requests/{request_id}/approve",
        headers=superuser_token_headers,
    )
    assert approved.status_code == 200, approved.json()
    work_item_id = approved.json()["work_item"]["id"]
    work_item = db.get(InventoryCorrectionWorkItem, work_item_id)
    assert work_item is not None
    attempt = db.exec(
        select(InventoryCorrectionAttempt).where(
            InventoryCorrectionAttempt.work_item_id == work_item_id
        )
    ).one()
    work_item.status = InventoryCorrectionWorkItemStatus.RUNNING
    work_item.lease_expires_at = get_datetime_utc().replace(year=2025)
    attempt.status = InventoryCorrectionAttemptStatus.RUNNING
    attempt.started_at = get_datetime_utc().replace(year=2025)
    db.add_all((work_item, attempt))
    db.commit()

    _run_correction_executor(db, run_id=1004)
    db.expire_all()
    failed = client.get(
        f"{INVENTORY_PATH}/correction-requests/{request_id}",
        headers=superuser_token_headers,
    )
    assert failed.status_code == 200, failed.json()
    assert (
        failed.json()["status"] == InventoryCorrectionRequestStatus.APPLICATION_FAILED
    )
    assert (
        failed.json()["work_item"]["status"]
        == InventoryCorrectionWorkItemStatus.TERMINAL_FAILED
    )
    assert (
        failed.json()["work_item"]["attempts"][0]["failure_category"]
        == InventoryCorrectionFailureCategory.EXECUTION_LOST
    )
    _run_correction_executor(db, run_id=1005)
    again = client.get(
        f"{INVENTORY_PATH}/correction-requests/{request_id}",
        headers=superuser_token_headers,
    )
    assert len(again.json()["work_item"]["attempts"]) == 1

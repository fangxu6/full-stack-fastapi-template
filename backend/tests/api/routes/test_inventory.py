import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import InventoryDocument
from app.schemas.inventory import InventoryLinePublic

INVENTORY_PATH = f"{settings.API_V1_STR}/inventory"


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _create_processing_unit(
    client: TestClient, headers: dict[str, str]
) -> dict[str, str]:
    response = client.post(
        f"{INVENTORY_PATH}/processing-units",
        headers=headers,
        json={"name": f"Unit {uuid.uuid4()}"},
    )
    assert response.status_code == 200
    return response.json()


def _create_receiving_unit(
    client: TestClient, headers: dict[str, str]
) -> dict[str, str]:
    response = client.post(
        f"{INVENTORY_PATH}/receiving-units",
        headers=headers,
        json={"name": f"Customer {uuid.uuid4()}"},
    )
    assert response.status_code == 200
    return response.json()


def _create_raw_receipt(
    client: TestClient,
    headers: dict[str, str],
    *,
    processing_unit_id: str,
    item_name: str,
    item_code: str,
    document_number: str | None = None,
    business_date: date | None = None,
    quantity_rolls: str = "1",
) -> dict[str, object]:
    payload = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(business_date or date.today()),
        "processing_unit_id": processing_unit_id,
        "document_number": document_number or f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": item_name,
                "item_code": item_code,
                "wool_content": "100% wool",
                "quantity_rolls": quantity_rolls,
            }
        ],
    }
    response = client.post(f"{INVENTORY_PATH}/documents", headers=headers, json=payload)
    assert response.status_code == 200, response.json()
    return response.json()


@pytest.mark.parametrize(
    ("endpoint", "factory"),
    [
        ("processing-units", _create_processing_unit),
        ("receiving-units", _create_receiving_unit),
    ],
)
def test_master_unit_lists_are_offset_paginated(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    endpoint: str,
    factory: object,
) -> None:
    for _ in range(3):
        factory(client, superuser_token_headers)

    response = client.get(
        f"{INVENTORY_PATH}/{endpoint}",
        headers=superuser_token_headers,
        params={"skip": 1, "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert payload["count"] >= 3
    assert payload["count"] > len(payload["data"])


@pytest.mark.parametrize("endpoint", ["processing-units", "receiving-units"])
def test_master_unit_lists_filter_by_name_and_status(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    endpoint: str,
) -> None:
    prefix = f"Filter {uuid.uuid4()}"
    endpoint_url = f"{INVENTORY_PATH}/{endpoint}"
    active_response = client.post(
        endpoint_url,
        headers=superuser_token_headers,
        json={"name": f"{prefix} Active"},
    )
    inactive_response = client.post(
        endpoint_url,
        headers=superuser_token_headers,
        json={"name": f"{prefix} Inactive"},
    )
    unrelated_response = client.post(
        endpoint_url,
        headers=superuser_token_headers,
        json={"name": f"Other {uuid.uuid4()}"},
    )
    assert active_response.status_code == 200
    assert inactive_response.status_code == 200
    assert unrelated_response.status_code == 200

    update_response = client.put(
        f"{endpoint_url}/{inactive_response.json()['id']}",
        headers=superuser_token_headers,
        json={"is_active": False},
    )
    assert update_response.status_code == 200

    filtered_response = client.get(
        endpoint_url,
        headers=superuser_token_headers,
        params={"name": f"  {prefix}  ", "skip": 0, "limit": 20},
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["count"] == 2
    assert {unit["name"] for unit in filtered_payload["data"]} == {
        f"{prefix} Active",
        f"{prefix} Inactive",
    }

    active_filtered_response = client.get(
        endpoint_url,
        headers=superuser_token_headers,
        params={"name": prefix, "is_active": True},
    )
    assert active_filtered_response.status_code == 200
    assert active_filtered_response.json()["count"] == 1
    assert active_filtered_response.json()["data"][0]["name"] == f"{prefix} Active"

    inactive_filtered_response = client.get(
        endpoint_url,
        headers=superuser_token_headers,
        params={"name": prefix, "is_active": False},
    )
    assert inactive_filtered_response.status_code == 200
    assert inactive_filtered_response.json()["count"] == 1
    assert inactive_filtered_response.json()["data"][0]["name"] == f"{prefix} Inactive"


def test_document_list_paginates_after_filters(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    prefix = f"PG-{uuid.uuid4()}"
    for index in range(3):
        _create_raw_receipt(
            client,
            superuser_token_headers,
            processing_unit_id=processing_unit["id"],
            item_name=f"Raw fabric {prefix}",
            item_code=f"RF-{uuid.uuid4()}",
            document_number=f"{prefix}-{index}",
        )

    response = client.get(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        params={"document_number": prefix, "skip": 1, "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert payload["count"] == 3


def test_balance_list_paginates_aggregated_rows(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    prefix = f"Balance {uuid.uuid4()}"
    for index in range(3):
        _create_raw_receipt(
            client,
            superuser_token_headers,
            processing_unit_id=processing_unit["id"],
            item_name=f"{prefix}-{index}",
            item_code=f"RB-{uuid.uuid4()}",
        )

    response = client.get(
        f"{INVENTORY_PATH}/balances/raw",
        headers=superuser_token_headers,
        params={"item_name": prefix, "skip": 1, "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 2
    assert payload["count"] == 3


def test_ledger_list_paginates_matching_entries(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_name = f"Ledger {uuid.uuid4()}"
    item_code = f"RL-{uuid.uuid4()}"
    for day in range(1, 4):
        _create_raw_receipt(
            client,
            superuser_token_headers,
            processing_unit_id=processing_unit["id"],
            item_name=item_name,
            item_code=item_code,
            business_date=date(2026, 7, day),
        )

    response = client.get(
        f"{INVENTORY_PATH}/ledger",
        headers=superuser_token_headers,
        params={
            "ledger_kind": "RAW",
            "processing_unit_id": processing_unit["id"],
            "item_name": item_name,
            "item_code": item_code,
            "wool_content": "100% wool",
            "skip": 1,
            "limit": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["count"] == 3


@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1, "limit": 20},
        {"skip": 0, "limit": 0},
        {"skip": 0, "limit": 101},
    ],
)
def test_inventory_lists_reject_invalid_pagination(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    params: dict[str, int],
) -> None:
    response = client.get(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        params=params,
    )

    assert response.status_code == 422
    assert response.json()["request_id"]


def test_raw_receipt_return_and_balance(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_code = f"RF-{uuid.uuid4()}"
    receipt = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": item_code,
                "wool_content": "100% wool",
                "quantity_rolls": "5.50",
            }
        ],
    }
    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=receipt
    )
    assert response.status_code == 200

    return_document = {
        **receipt,
        "document_type": "RAW_RETURN",
        "document_number": f"T-{uuid.uuid4()}",
    }
    return_document["lines"] = [{**receipt["lines"][0], "quantity_rolls": "2.25"}]
    response = client.post(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        json=return_document,
    )
    assert response.status_code == 200

    response = client.get(
        f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers
    )
    assert response.status_code == 200
    balance = next(
        item for item in response.json()["data"] if item["item_code"] == item_code
    )
    assert _decimal(balance["rolls_balance"]) == Decimal("3.25")


def test_raw_return_rejects_negative_balance(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_code = f"RF-{uuid.uuid4()}"
    payload = {
        "document_type": "RAW_RETURN",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"T-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": item_code,
                "wool_content": "100% wool",
                "quantity_rolls": 1,
            }
        ],
    }
    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=payload
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient inventory"
    assert response.json()["request_id"]


def test_document_update_delete_and_restore_recalculate_balance(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_code = f"RF-{uuid.uuid4()}"
    document = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": item_code,
                "wool_content": "100% wool",
                "quantity_rolls": "5.50",
            }
        ],
    }
    created = client.post(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        json=document,
    )
    assert created.status_code == 200
    document_id = created.json()["id"]

    document["lines"][0]["quantity_rolls"] = "3.25"
    updated = client.put(
        f"{INVENTORY_PATH}/documents/{document_id}",
        headers=superuser_token_headers,
        json=document,
    )
    assert updated.status_code == 200, updated.json()

    response = client.get(
        f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers
    )
    balance = next(
        item for item in response.json()["data"] if item["item_code"] == item_code
    )
    assert _decimal(balance["rolls_balance"]) == Decimal("3.25")

    deleted = client.delete(
        f"{INVENTORY_PATH}/documents/{document_id}", headers=superuser_token_headers
    )
    assert deleted.status_code == 200
    response = client.get(
        f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers
    )
    assert all(item["item_code"] != item_code for item in response.json()["data"])

    restored = client.post(
        f"{INVENTORY_PATH}/documents/{document_id}/restore",
        headers=superuser_token_headers,
    )
    assert restored.status_code == 200
    response = client.get(
        f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers
    )
    balance = next(
        item for item in response.json()["data"] if item["item_code"] == item_code
    )
    assert _decimal(balance["rolls_balance"]) == Decimal("3.25")


def test_finished_shipment_updates_roll_and_meter_balances(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    receiving = client.post(
        f"{INVENTORY_PATH}/receiving-units",
        headers=superuser_token_headers,
        json={"name": f"Customer {uuid.uuid4()}"},
    )
    assert receiving.status_code == 200
    shipment = {
        "document_type": "FINISHED_SHIPMENT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "receiving_unit_id": receiving.json()["id"],
        "document_number": f"S-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Finished fabric",
                "wool_content": "70% wool",
                "color_code": "Blue-01",
                "dye_lot_no": "LOT-01",
                "quantity_rolls": "0.50",
                "quantity_meters": "12.5",
            }
        ],
    }

    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=shipment
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Insufficient inventory"


@pytest.mark.parametrize("quantity_rolls", ["0", "-0.01", "1.001"])
def test_roll_quantity_rejects_non_positive_or_over_precision_values(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    quantity_rolls: str,
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    payload = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": f"RF-{uuid.uuid4()}",
                "wool_content": "100% wool",
                "quantity_rolls": quantity_rolls,
            }
        ],
    }

    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=payload
    )

    assert response.status_code == 422
    assert response.json()["request_id"]


def test_historical_read_model_allows_zero_rolls() -> None:
    line = InventoryLinePublic(
        id=uuid.uuid4(),
        line_no=1,
        item_name="Legacy finished fabric",
        item_code=None,
        wool_content="70% wool",
        color_code="Blue-01",
        dye_lot_no="LOT-01",
        quantity_rolls=Decimal("0"),
        quantity_meters=Decimal("20"),
    )

    assert line.quantity_rolls == Decimal("0")


def test_inactive_processing_unit_rejects_new_document(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    deactivated = client.put(
        f"{INVENTORY_PATH}/processing-units/{processing_unit['id']}",
        headers=superuser_token_headers,
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    payload = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": f"RF-{uuid.uuid4()}",
                "wool_content": "100% wool",
                "quantity_rolls": 1,
            }
        ],
    }

    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=payload
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Processing unit is not active"


def test_document_number_and_legacy_placeholders_are_rejected(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    number = f"R-{uuid.uuid4()}"
    payload = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": number,
        "lines": [
            {
                "item_name": "Raw fabric",
                "item_code": f"RF-{uuid.uuid4()}",
                "wool_content": "100% wool",
                "quantity_rolls": 1,
            }
        ],
    }
    assert (
        client.post(
            f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=payload
        ).status_code
        == 200
    )

    duplicate = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=payload
    )
    assert duplicate.status_code == 409

    placeholder = client.post(
        f"{INVENTORY_PATH}/documents",
        headers=superuser_token_headers,
        json={
            **payload,
            "document_number": f"R-{uuid.uuid4()}",
            "lines": [{**payload["lines"][0], "item_code": "未填写品号"}],
        },
    )
    assert placeholder.status_code == 400
    assert (
        placeholder.json()["detail"]
        == "Legacy placeholder values cannot be used in new documents"
    )


def test_legacy_documents_cannot_be_updated_deleted_or_restored(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    document = _create_raw_receipt(
        client,
        superuser_token_headers,
        processing_unit_id=processing_unit["id"],
        item_name="Legacy fabric",
        item_code=f"LEGACY-{uuid.uuid4()}",
    )
    stored_document = db.get(InventoryDocument, uuid.UUID(str(document["id"])))
    assert stored_document is not None
    stored_document.is_legacy = True
    db.add(stored_document)
    db.commit()

    update_response = client.put(
        f"{INVENTORY_PATH}/documents/{stored_document.id}",
        headers=superuser_token_headers,
        json={
            "document_type": "RAW_RECEIPT",
            "business_date": str(date.today()),
            "processing_unit_id": processing_unit["id"],
            "document_number": f"LEGACY-EDIT-{uuid.uuid4()}",
            "lines": [
                {
                    "item_name": "Legacy fabric",
                    "item_code": "LEGACY-CODE",
                    "wool_content": "100% wool",
                    "quantity_rolls": 1,
                }
            ],
        },
    )
    delete_response = client.delete(
        f"{INVENTORY_PATH}/documents/{stored_document.id}",
        headers=superuser_token_headers,
    )
    restore_response = client.post(
        f"{INVENTORY_PATH}/documents/{stored_document.id}/restore",
        headers=superuser_token_headers,
    )

    assert update_response.status_code == 400
    assert (
        update_response.json()["detail"]
        == "Legacy inventory documents cannot be edited"
    )
    assert delete_response.status_code == 400
    assert (
        delete_response.json()["detail"]
        == "Legacy inventory documents cannot be deleted"
    )
    assert restore_response.status_code == 400
    assert (
        restore_response.json()["detail"]
        == "Legacy inventory documents cannot be restored"
    )


def test_suggestions_return_saved_values(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    processing_unit = _create_processing_unit(client, superuser_token_headers)
    item_name = f"Raw {uuid.uuid4()}"
    receipt = {
        "document_type": "RAW_RECEIPT",
        "business_date": str(date.today()),
        "processing_unit_id": processing_unit["id"],
        "document_number": f"R-{uuid.uuid4()}",
        "lines": [
            {
                "item_name": item_name,
                "item_code": f"RF-{uuid.uuid4()}",
                "wool_content": "100% wool",
                "quantity_rolls": 1,
            }
        ],
    }
    assert (
        client.post(
            f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=receipt
        ).status_code
        == 200
    )

    response = client.get(
        f"{INVENTORY_PATH}/suggestions",
        headers=superuser_token_headers,
        params={"ledger_kind": "RAW", "field": "item_name", "query": item_name},
    )

    assert response.status_code == 200
    assert response.json()["data"] == [item_name]

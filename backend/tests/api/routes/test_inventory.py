import uuid
from datetime import date

from fastapi.testclient import TestClient

from app.core.config import settings

INVENTORY_PATH = f"{settings.API_V1_STR}/inventory"


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
                "quantity_rolls": 5,
            }
        ],
    }
    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=receipt
    )
    assert response.status_code == 200

    return_document = {**receipt, "document_type": "RAW_RETURN", "document_number": f"T-{uuid.uuid4()}"}
    return_document["lines"] = [{**receipt["lines"][0], "quantity_rolls": 2}]
    response = client.post(
        f"{INVENTORY_PATH}/documents", headers=superuser_token_headers, json=return_document
    )
    assert response.status_code == 200

    response = client.get(f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers)
    assert response.status_code == 200
    balance = next(item for item in response.json()["data"] if item["item_code"] == item_code)
    assert balance["rolls_balance"] == 3


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
                "quantity_rolls": 5,
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

    document["lines"][0]["quantity_rolls"] = 3
    updated = client.put(
        f"{INVENTORY_PATH}/documents/{document_id}",
        headers=superuser_token_headers,
        json=document,
    )
    assert updated.status_code == 200, updated.json()

    response = client.get(f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers)
    balance = next(item for item in response.json()["data"] if item["item_code"] == item_code)
    assert balance["rolls_balance"] == 3

    deleted = client.delete(
        f"{INVENTORY_PATH}/documents/{document_id}", headers=superuser_token_headers
    )
    assert deleted.status_code == 200
    response = client.get(f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers)
    assert all(item["item_code"] != item_code for item in response.json()["data"])

    restored = client.post(
        f"{INVENTORY_PATH}/documents/{document_id}/restore",
        headers=superuser_token_headers,
    )
    assert restored.status_code == 200
    response = client.get(f"{INVENTORY_PATH}/balances/raw", headers=superuser_token_headers)
    balance = next(item for item in response.json()["data"] if item["item_code"] == item_code)
    assert balance["rolls_balance"] == 3

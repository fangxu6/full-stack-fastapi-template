from fastapi.testclient import TestClient


def test_retired_inventory_ai_query_is_not_registered(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai/inventory/query",
        json={"question": "查询库存"},
    )

    assert response.status_code == 404

from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.status import HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.exceptions import PermissionDeniedError
from app.main import app


def test_request_id_header_is_added(client: TestClient) -> None:
    response = client.get("/api/v1/utils/health-check/")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_unhandled_exceptions_return_request_id() -> None:
    router = APIRouter()

    @router.get("/__test/error")
    def raise_error() -> None:
        raise RuntimeError("boom")

    app.include_router(router)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/__test/error")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "detail": "Internal Server Error",
        "request_id": response.headers["X-Request-ID"],
    }


def test_modules_router_is_registered(client: TestClient) -> None:
    response = client.get("/api/v1/modules/health-check/")

    assert response.status_code == 200
    assert response.json() == {"message": "Modules router ready"}


def test_app_error_returns_structured_json() -> None:
    router = APIRouter()

    @router.get("/__test/permission-denied")
    def raise_permission_denied() -> None:
        raise PermissionDeniedError()

    app.include_router(router)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/__test/permission-denied")

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "detail": "Permission denied",
        "request_id": response.headers["X-Request-ID"],
    }

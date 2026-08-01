from unittest.mock import patch

from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError
from app.main import app


def test_request_id_header_is_added(client: TestClient) -> None:
    response = client.get("/api/v1/utils/health-check/")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_cors_preflight_has_request_correlation_and_telemetry() -> None:
    with (
        patch("app.core.exceptions.log_event") as mock_log_event,
        patch("app.core.exceptions.should_sample_success", return_value=True),
    ):
        with TestClient(app) as test_client:
            response = test_client.options(
                "/api/v1/utils/health-check/",
                headers={
                    "Origin": settings.FRONTEND_HOST,
                    "Access-Control-Request-Method": "GET",
                },
            )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    event = mock_log_event.call_args.kwargs
    assert {
        "event_name": "http.request.completed",
        "severity": "INFO",
        "method": "OPTIONS",
        "route_template": "unmatched",
        "status_code": 200,
    }.items() <= event.items()


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


def test_framework_http_exceptions_return_structured_json(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/users/me")

    assert response.status_code == HTTP_401_UNAUTHORIZED
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "detail": "Not authenticated",
        "request_id": response.headers["X-Request-ID"],
    }


def test_validation_errors_return_structured_json() -> None:
    router = APIRouter()

    @router.get("/__test/validation")
    def validate_input(value: int) -> dict[str, int]:
        return {"value": value}

    app.include_router(router)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/__test/validation")

    assert response.status_code == HTTP_422_UNPROCESSABLE_CONTENT
    assert response.headers["X-Request-ID"]
    payload = response.json()
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert isinstance(payload["detail"], list)
    assert payload["detail"]


def test_openapi_documents_request_id_for_validation_errors() -> None:
    validation_error = app.openapi()["components"]["schemas"]["HTTPValidationError"]

    assert validation_error["properties"]["request_id"] == {
        "title": "Request Id",
        "type": "string",
    }
    assert "request_id" in validation_error["required"]


def test_unhandled_exceptions_emit_safe_failure_event() -> None:
    router = APIRouter()

    @router.get("/__test/logged-error")
    def raise_error() -> None:
        raise RuntimeError("boom")

    app.include_router(router)

    with patch("app.core.exceptions.log_event") as mock_log_event:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/__test/logged-error")

    assert response.status_code == HTTP_500_INTERNAL_SERVER_ERROR
    mock_log_event.assert_called_once()
    assert mock_log_event.call_args.kwargs["event_name"] == "http.request.failed"
    assert mock_log_event.call_args.kwargs["severity"] == "ERROR"
    assert "boom" not in str(mock_log_event.call_args.kwargs)


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


def test_permission_denial_emits_authorization_event() -> None:
    router = APIRouter()

    @router.get("/__test/permission-denied-log")
    def raise_permission_denied() -> None:
        raise PermissionDeniedError()

    app.include_router(router)

    with patch("app.core.exceptions.log_event") as mock_log_event:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/__test/permission-denied-log")

    assert response.status_code == HTTP_403_FORBIDDEN
    events = [call.kwargs for call in mock_log_event.call_args_list]
    assert {
        "event_name": "authorization.denied",
        "severity": "WARNING",
        "actor_kind": "anonymous",
        "authorization_result": "denied",
    } in events

from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.dependencies import auth, database
from app.api.main import api_router
from app.core.config import settings


class TrackingSession:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


def tracking_db(session: TrackingSession, events: list[str]) -> Generator[Any]:
    events.append("open")
    try:
        yield session
    finally:
        events.append("close")


def test_write_dependency_commits_shared_function_scope_session_before_close() -> None:
    events: list[str] = []
    session = TrackingSession(events)
    app = FastAPI()
    write_session_dep = getattr(database, "WriteSessionDep", None)

    assert write_session_dep is not None

    def get_tracking_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    app.dependency_overrides[database.get_db] = get_tracking_db

    @app.post("/write")
    def write(
        write_session: write_session_dep, read_session: auth.SessionDep
    ) -> dict[str, bool]:
        return {"same_session": write_session is read_session}

    with TestClient(app) as client:
        response = client.post("/write")

    assert response.status_code == 200
    assert response.json() == {"same_session": True}
    assert events == ["open", "commit", "close"]


def test_write_dependency_rolls_back_http_exception_before_close() -> None:
    events: list[str] = []
    session = TrackingSession(events)
    app = FastAPI()
    write_session_dep = getattr(database, "WriteSessionDep", None)

    assert write_session_dep is not None

    def get_tracking_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    app.dependency_overrides[database.get_db] = get_tracking_db

    @app.post("/failure")
    def fail(write_session: write_session_dep) -> None:
        del write_session
        raise HTTPException(status_code=409, detail="conflict")

    with TestClient(app) as client:
        response = client.post("/failure")

    assert response.status_code == 409
    assert events == ["open", "rollback", "close"]


def test_all_http_write_handlers_depend_on_write_session() -> None:
    write_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def api_routes(router: Any) -> Generator[APIRoute]:
        for route in router.routes:
            included_router = getattr(route, "original_router", None)
            if included_router is not None:
                yield from api_routes(included_router)
            elif isinstance(route, APIRoute):
                yield route

    write_routes = [route for route in api_routes(api_router) if route.methods & write_methods]
    missing_write_session = [
        route.path
        for route in write_routes
        if not any(
            dependency.call is database.get_write_db
            for dependency in route.dependant.dependencies
        )
    ]

    assert len(write_routes) == 38
    assert missing_write_session == []


def test_test_email_sends_after_request_commit(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    original_commit = Session.commit

    def record_commit(session: Session) -> None:
        events.append("commit")
        original_commit(session)

    def send_email_after_commit(**_: str) -> None:
        events.append("email")
        assert events == ["commit", "email"]

    monkeypatch.setattr(Session, "commit", record_commit)
    monkeypatch.setattr("app.api.routes.utils.send_email", send_email_after_commit)

    response = client.post(
        f"{settings.API_V1_STR}/utils/test-email/?email_to=test@example.com",
        headers=superuser_token_headers,
    )

    assert response.status_code == 201
    assert events == ["commit", "email"]

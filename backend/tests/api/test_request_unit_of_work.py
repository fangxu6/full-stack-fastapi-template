from collections.abc import Generator
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.dependencies import auth, database
from app.api.main import api_router
from app.core import cache
from app.core.config import settings
from app.models import EmailOutbox, EmailOutboxKind


class TrackingSession:
    def __init__(
        self, events: list[str], commit_error: Exception | None = None
    ) -> None:
        self.events = events
        self.commit_error = commit_error
        self.info: dict[str, object] = {}

    def commit(self) -> None:
        self.events.append("commit")
        if self.commit_error is not None:
            raise self.commit_error

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


@pytest.mark.parametrize("raises_error", [False, True])
def test_read_dependency_closes_without_a_transaction(raises_error: bool) -> None:
    events: list[str] = []
    session = TrackingSession(events)
    app = FastAPI()
    read_session_dep = getattr(database, "ReadSessionDep", None)

    assert read_session_dep is not None

    def get_tracking_read_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    app.dependency_overrides[database.get_read_db] = get_tracking_read_db

    @app.get("/read")
    def read(read_session: read_session_dep) -> dict[str, bool]:
        del read_session
        if raises_error:
            raise HTTPException(status_code=409, detail="conflict")
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/read")

    assert response.status_code == (409 if raises_error else 200)
    assert events == ["open", "close"]


def test_read_dependency_propagates_replica_failures_without_primary_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary_engine = object()
    replica_engine = object()
    replica_error = RuntimeError("replica unavailable")
    called_engines: list[object] = []

    def failing_session(engine: object) -> None:
        called_engines.append(engine)
        raise replica_error

    monkeypatch.setattr(database, "engine", primary_engine)
    monkeypatch.setattr(database, "read_engine", replica_engine)
    monkeypatch.setattr(database, "Session", failing_session)

    with pytest.raises(RuntimeError, match="replica unavailable"):
        next(database.get_read_db())

    assert called_engines == [replica_engine]


def test_write_dependency_invalidates_after_successful_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    session = TrackingSession(events)
    app = FastAPI()
    write_session_dep = getattr(database, "WriteSessionDep", None)
    key = cache.make_cache_key("test", "success")

    assert write_session_dep is not None

    def get_tracking_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    def record_delete(*keys: str) -> None:
        assert keys == (key,)
        events.append("cache_delete")

    monkeypatch.setattr(cache, "delete", record_delete)
    app.dependency_overrides[database.get_db] = get_tracking_db

    @app.post("/__test/cache-commit")
    def write(write_session: write_session_dep) -> dict[str, bool]:
        cache.defer_cache_invalidation(write_session, key)
        return {"ok": True}

    with TestClient(app) as client:
        response = client.post("/__test/cache-commit")

    assert response.status_code == 200
    assert events == ["open", "commit", "cache_delete", "close"]
    assert session.info == {}


def test_write_dependency_discards_invalidation_on_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    session = TrackingSession(events)
    app = FastAPI()
    write_session_dep = getattr(database, "WriteSessionDep", None)
    key = cache.make_cache_key("test", "rollback")

    assert write_session_dep is not None

    def get_tracking_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    monkeypatch.setattr(cache, "delete", lambda *keys: events.append("cache_delete"))
    app.dependency_overrides[database.get_db] = get_tracking_db

    @app.post("/__test/cache-rollback")
    def fail(write_session: write_session_dep) -> None:
        cache.defer_cache_invalidation(write_session, key)
        raise HTTPException(status_code=409, detail="conflict")

    with TestClient(app) as client:
        response = client.post("/__test/cache-rollback")

    assert response.status_code == 409
    assert events == ["open", "rollback", "close"]
    assert session.info == {}


def test_write_dependency_discards_invalidation_when_commit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    session = TrackingSession(events, commit_error=RuntimeError("commit failed"))
    app = FastAPI()
    write_session_dep = getattr(database, "WriteSessionDep", None)
    key = cache.make_cache_key("test", "commit-failure")

    assert write_session_dep is not None

    def get_tracking_db() -> Generator[Any]:
        yield from tracking_db(session, events)

    monkeypatch.setattr(cache, "delete", lambda *keys: events.append("cache_delete"))
    app.dependency_overrides[database.get_db] = get_tracking_db

    @app.post("/write")
    def write(write_session: write_session_dep) -> dict[str, bool]:
        cache.defer_cache_invalidation(write_session, key)
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/write")

    assert response.status_code == 500
    assert events == ["open", "commit", "rollback", "close"]
    assert session.info == {}


def test_all_http_write_handlers_depend_on_write_session() -> None:
    write_methods = {"POST", "PUT", "PATCH", "DELETE"}

    def api_routes(router: Any) -> Generator[APIRoute]:
        for route in router.routes:
            included_router = getattr(route, "original_router", None)
            if included_router is not None:
                yield from api_routes(included_router)
            elif isinstance(route, APIRoute):
                yield route

    write_routes = [
        route for route in api_routes(api_router) if route.methods & write_methods
    ]

    def depends_on_write_session(dependency: Any) -> bool:
        if dependency.call is database.get_write_db:
            return True
        return any(depends_on_write_session(child) for child in dependency.dependencies)

    missing_write_session = [
        route.path
        for route in write_routes
        if not any(
            depends_on_write_session(dependency)
            for dependency in route.dependant.dependencies
        )
    ]

    assert write_routes
    assert missing_write_session == []


def test_only_allowlisted_read_handlers_depend_on_read_session() -> None:
    expected_paths = {
        "/inventory/excel/ledger",
        "/inventory/processing-units",
        "/inventory/receiving-units",
        "/inventory/documents",
        "/inventory/documents/{document_id}",
        "/inventory/balances/raw",
        "/inventory/balances/finished",
        "/inventory/ledger",
        "/inventory/suggestions",
        "/scheduler/jobs",
        "/scheduler/jobs/{job_id}",
        "/scheduler/jobs/{job_id}/runs",
    }

    def api_routes(router: Any) -> Generator[APIRoute]:
        for route in router.routes:
            included_router = getattr(route, "original_router", None)
            if included_router is not None:
                yield from api_routes(included_router)
            elif isinstance(route, APIRoute):
                yield route

    def depends_on(callable_: Any, dependency: Any) -> bool:
        return dependency.call is callable_ or any(
            depends_on(callable_, child) for child in dependency.dependencies
        )

    read_routes = [
        route
        for route in api_routes(api_router)
        if any(
            depends_on(database.get_read_db, dependency)
            for dependency in route.dependant.dependencies
        )
    ]

    assert {route.path for route in read_routes} == expected_paths
    assert all(route.methods == {"GET"} for route in read_routes)
    assert all(
        any(
            depends_on(database.get_db, dependency)
            for dependency in route.dependant.dependencies
        )
        for route in read_routes
    )


def test_test_email_queues_outbox_at_request_commit(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_commit = Session.commit
    commit_count = 0

    def record_commit(session: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit(session)

    monkeypatch.setattr(Session, "commit", record_commit)

    response = client.post(
        f"{settings.API_V1_STR}/utils/test-email/?email_to=test@example.com",
        headers=superuser_token_headers,
    )

    assert response.status_code == 202
    assert response.json() == {"message": "Test email queued"}
    assert commit_count == 1
    db.expire_all()
    outbox = db.exec(
        select(EmailOutbox).where(EmailOutbox.recipient == "test@example.com")
    ).one()
    assert outbox.kind is EmailOutboxKind.RENDERED

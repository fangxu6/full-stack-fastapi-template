import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import redis
from sqlmodel import Session, select

from app.core.audit import bind_audit_actor
from app.core.config import settings
from app.core.db import engine
from app.models import AuditEvent, EventDelivery, EventDeliveryState, User
from app.modules.events import service, tasks
from app.modules.events.contracts import EventEnvelope
from app.modules.events.registry import event_registry
from tests.modules.events.runtime_support import (
    AUDIT_ACTION,
    HANDLER_KEY,
    register_runtime_handler,
)


def test_real_worker_processes_persisted_event() -> None:
    redis_port = int(os.environ.get("REDIS_PORT", "6381"))
    redis_binary = shutil.which("redis-server")
    assert redis_binary is not None, "redis-server is required for runtime E2E"
    redis_process = subprocess.Popen(
        [
            redis_binary,
            "--port",
            str(redis_port),
            "--save",
            "",
            "--appendonly",
            "no",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    worker: subprocess.Popen[bytes] | None = None
    try:
        broker = redis.Redis(host="127.0.0.1", port=redis_port, db=0)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if redis_process.poll() is not None:
                raise AssertionError("test Redis process exited before becoming ready")
            try:
                if broker.ping():
                    break
            except redis.RedisError:
                time.sleep(0.1)
        else:
            raise AssertionError("test Redis process did not become ready")

        event_registry.clear_for_testing()
        register_runtime_handler()
        envelope = EventEnvelope(
            event_id=uuid.uuid4(),
            event_type="test.runtime.changed",
            producer="test",
            schema_version=1,
            resource_type="fixture",
            resource_id="runtime",
            occurred_at=datetime.now(UTC),
            payload={"value": 1},
        )
        with Session(engine) as session:
            actor = session.exec(
                select(User).where(User.email == settings.FIRST_SUPERUSER)
            ).one()
            bind_audit_actor(session=session, actor_id=actor.id)
            publication = service.publish_event(session=session, envelope=envelope)
            session.commit()
            assert publication.id is not None
            delivery = session.exec(
                select(EventDelivery).where(
                    EventDelivery.publication_id == publication.id,
                    EventDelivery.handler_key == HANDLER_KEY,
                )
            ).one()
            assert delivery.id is not None
            delivery_id = delivery.id

        worker_script = (
            "from tests.modules.events.runtime_support import register_runtime_handler\n"
            "register_runtime_handler()\n"
            "from app.core.celery import celery_app\n"
            "celery_app.worker_main(['worker', '--pool=solo', '--concurrency=1', "
            "'--loglevel=WARNING', '--without-gossip', '--without-mingle', "
            "'--without-heartbeat'])\n"
        )
        worker = subprocess.Popen(
            [sys.executable, "-c", worker_script],
            cwd=Path(__file__).resolve().parents[2],
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        tasks.dispatch_due_deliveries(now=envelope.occurred_at + timedelta(seconds=1))
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with Session(engine) as session:
                current = session.get(EventDelivery, delivery_id)
                if (
                    current is not None
                    and current.state is EventDeliveryState.SUCCEEDED
                ):
                    handled = session.exec(
                        select(AuditEvent).where(
                            AuditEvent.action == AUDIT_ACTION,
                            AuditEvent.resource_id == str(envelope.event_id),
                        )
                    ).all()
                    assert len(handled) == 1
                    return
            time.sleep(0.2)
        raise AssertionError("real event worker did not complete the delivery")
    finally:
        event_registry.clear_for_testing()
        if worker is not None:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
        redis_process.terminate()
        try:
            redis_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            redis_process.kill()
            redis_process.wait(timeout=5)

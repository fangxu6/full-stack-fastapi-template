import importlib.util
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest
from sqlmodel import Session, select

from app.core.audit import (
    AuditActorError,
    bind_audit_actor,
    clear_audit_actor,
)
from app.core.db import engine
from app.models import (
    IamUserRole,
    InventoryDailyReport,
    InventoryDailyReportDelivery,
    InventoryDocument,
    InventoryDocumentLine,
    InventoryImportBatch,
    InventoryLedgerEntry,
    Item,
    LegacyImportRow,
    ProcessingUnit,
    ReceivingUnit,
    SchedulerJob,
    SchedulerRun,
    User,
)
from app.models.base import AuditFields
from app.models.inventory import (
    InventoryDocumentType,
    InventoryLedgerKind,
    InventoryMovementType,
    LegacyWorkbookKind,
)
from app.models.scheduler import SchedulerRunStatus, SchedulerRunTrigger


def test_user_model_has_a_private_system_actor_marker() -> None:
    column = User.__table__.c.get("is_system_actor")
    key_column = User.__table__.c.get("system_actor_key")

    assert column is not None
    assert column.nullable is False
    assert column.default is not None
    assert column.default.arg is False
    assert key_column is not None
    assert key_column.nullable is True


def test_init_db_creates_the_system_actor(db: Session) -> None:
    system_actor = db.exec(
        select(User).where(User.system_actor_key == "system")
    ).one_or_none()

    assert system_actor is not None
    assert system_actor.email == "system@example.com"
    assert system_actor.is_active is False
    assert system_actor.system_actor_key == "system"


def test_ensure_system_actor_is_idempotent_and_unmanaged() -> None:
    from app.core.audit import SYSTEM_ACTOR_EMAIL, ensure_system_actor

    with Session(engine) as session:
        first = ensure_system_actor(session=session)
        session.commit()
        second = ensure_system_actor(session=session)
        session.commit()

        default_actors = list(
            session.exec(select(User).where(User.system_actor_key == "system")).all()
        )
        roles = list(
            session.exec(
                select(IamUserRole).where(IamUserRole.user_id == first.id)
            ).all()
        )

    assert first.id == second.id
    assert len(default_actors) == 1
    assert first.email == SYSTEM_ACTOR_EMAIL
    assert first.is_active is False
    assert roles == []


def test_init_db_is_idempotent_for_the_default_system_actor(db: Session) -> None:
    from app.core.config import settings
    from app.core.db import init_db

    first_superuser = db.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).one()
    try:
        init_db(db)
        init_db(db)
        db.commit()

        actors = list(
            db.exec(select(User).where(User.system_actor_key == "system")).all()
        )
        assert len(actors) == 1
        assert actors[0].is_system_actor is True
    finally:
        bind_audit_actor(session=db, actor_id=first_superuser.id)


def test_parallel_system_actor_provisioning_is_idempotent(db: Session) -> None:
    from app.core.audit import provision_system_actor

    actor_key = f"parallel-{uuid.uuid4().hex}"
    email = f"{actor_key}@system.invalid"

    def provision() -> uuid.UUID:
        with Session(engine) as session:
            actor = provision_system_actor(
                session=session,
                actor_key=actor_key,
                email=email,
            )
            session.commit()
            return actor.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        actor_ids = list(executor.map(lambda _: provision(), range(2)))

    assert actor_ids[0] == actor_ids[1]
    actor = db.exec(select(User).where(User.system_actor_key == actor_key)).one()
    assert actor.email == email
    db.delete(actor)
    db.commit()


def test_provision_system_actor_is_idempotent_per_key() -> None:
    from app.core.audit import provision_system_actor

    with Session(engine) as session:
        inventory_import = provision_system_actor(
            session=session,
            actor_key="inventory-ai-import",
            email="inventory-ai-import@system.invalid",
        )
        session.commit()
        same_inventory_import = provision_system_actor(
            session=session,
            actor_key="inventory-ai-import",
            email="inventory-ai-import@system.invalid",
        )
        report_export = provision_system_actor(
            session=session,
            actor_key="report-ai-export",
            email="report-ai-export@system.invalid",
        )
        session.commit()

        actors = list(
            session.exec(select(User).where(User.is_system_actor.is_(True))).all()
        )

        assert inventory_import.id == same_inventory_import.id
        assert inventory_import.id != report_export.id
        assert {actor.system_actor_key for actor in actors} >= {
            "system",
            "inventory-ai-import",
            "report-ai-export",
        }
        assert all(actor.is_active is False for actor in actors)

        session.delete(inventory_import)
        session.delete(report_export)
        session.commit()


def test_bound_actor_owns_new_audit_fields() -> None:
    from app.core.audit import bind_audit_actor

    with Session(engine) as session:
        actor = User(
            email="audit-owner@example.com",
            hashed_password="not-used",
        )
        session.add(actor)
        session.flush()
        bind_audit_actor(session=session, actor_id=actor.id)

        unit = ProcessingUnit(
            name="Audit Unit",
            normalized_name="audit unit",
        )
        session.add(unit)
        session.flush()

        assert unit.created_by == actor.id
        assert unit.updated_by == actor.id
        assert unit.created_at == unit.updated_at

        session.rollback()


def test_audit_fields_reject_missing_actor_before_insert() -> None:
    with Session(engine) as session:
        session.add(
            ProcessingUnit(
                name="Unattributed Unit",
                normalized_name="unattributed unit",
                created_by=uuid.uuid4(),
                updated_by=uuid.uuid4(),
            )
        )

        with pytest.raises(RuntimeError, match="audit actor"):
            session.flush()

        session.rollback()


def test_audit_fields_reject_creator_tampering_on_update() -> None:
    from app.core.audit import bind_audit_actor

    with Session(engine) as session:
        actor = User(
            email="creator-owner@example.com",
            hashed_password="not-used",
        )
        session.add(actor)
        session.flush()
        bind_audit_actor(session=session, actor_id=actor.id)
        unit = ProcessingUnit(
            name="Immutable Creator",
            normalized_name="immutable creator",
            created_by=actor.id,
            updated_by=actor.id,
        )
        session.add(unit)
        session.commit()

        unit.created_by = uuid.uuid4()
        with pytest.raises(RuntimeError, match="created_by"):
            session.flush()

        session.rollback()


def test_all_audited_models_share_the_bound_actor_and_flush_timestamp() -> None:
    with Session(engine) as session:
        actor = User(email="all-audit-owner@example.com", hashed_password="not-used")
        session.add(actor)
        session.flush()
        bind_audit_actor(session=session, actor_id=actor.id)

        processing_unit = ProcessingUnit(
            name="All Audit Processing",
            normalized_name="all audit processing",
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        receiving_unit = ReceivingUnit(
            name="All Audit Receiving",
            normalized_name="all audit receiving",
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        batch = InventoryImportBatch(
            source_fingerprint="a" * 64,
            raw_workbook_sha256="b" * 64,
            finished_workbook_sha256="c" * 64,
            importer_version="test",
            reconciliation_report={},
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        scheduler_job = SchedulerJob(
            name="Audit model coverage",
            class_path="app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask",
            cron_expression="0 8 * * *",
            next_run_at=datetime(2026, 7, 29, tzinfo=UTC),
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        audited_models = [
            processing_unit,
            receiving_unit,
            batch,
            scheduler_job,
        ]
        session.add_all(audited_models)
        session.flush()

        assert len({model.created_at for model in audited_models}) == 1

        document = InventoryDocument(
            document_type=InventoryDocumentType.RAW_RECEIPT,
            business_date=date(2026, 7, 28),
            processing_unit_id=processing_unit.id,
            document_number="AUDIT-ALL-001",
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        session.add(document)
        session.flush()
        audited_models.append(document)

        line = InventoryDocumentLine(
            document_id=document.id,
            line_no=1,
            item_name="Audit fabric",
            wool_content="100% wool",
            quantity_rolls=Decimal("1"),
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        session.add(line)
        session.flush()
        audited_models.append(line)

        legacy_row = LegacyImportRow(
            import_batch_id=batch.id,
            workbook_kind=LegacyWorkbookKind.RAW,
            workbook_name="raw.xlsx",
            worksheet_name="Sheet1",
            source_row_number=1,
            raw_cells={},
            source_balance_snapshot={},
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        session.add(legacy_row)
        session.flush()
        audited_models.append(legacy_row)

        ledger_entry = InventoryLedgerEntry(
            ledger_kind=InventoryLedgerKind.RAW,
            movement_type=InventoryMovementType.RAW_RECEIPT,
            business_date=date(2026, 7, 28),
            processing_unit_id=processing_unit.id,
            document_line_id=line.id,
            item_name="Audit fabric",
            wool_content="100% wool",
            rolls_delta=Decimal("1"),
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        session.add(ledger_entry)
        session.flush()
        audited_models.append(ledger_entry)

        assert {model.created_by for model in audited_models} == {actor.id}
        assert {model.updated_by for model in audited_models} == {actor.id}
        assert all(model.created_at == model.updated_at for model in audited_models)

        session.rollback()


def _create_audited_model(
    *, session: Session, model_name: str
) -> tuple[AuditFields, str]:
    marker = uuid.uuid4().hex
    processing_unit = ProcessingUnit(
        name=f"Lifecycle processing {marker}",
        normalized_name=f"lifecycle processing {marker}",
    )
    receiving_unit = ReceivingUnit(
        name=f"Lifecycle receiving {marker}",
        normalized_name=f"lifecycle receiving {marker}",
    )
    batch = InventoryImportBatch(
        source_fingerprint=marker * 2,
        raw_workbook_sha256="a" * 64,
        finished_workbook_sha256="b" * 64,
        importer_version="lifecycle-test",
        reconciliation_report={},
    )
    scheduler_job = SchedulerJob(
        name=f"Lifecycle scheduler {marker}",
        class_path="app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask",
        cron_expression="0 8 * * *",
        next_run_at=datetime(2026, 7, 29, tzinfo=UTC),
    )
    session.add_all((processing_unit, receiving_unit, batch, scheduler_job))
    session.flush()

    if model_name == "processing_unit":
        return processing_unit, "name"
    if model_name == "receiving_unit":
        return receiving_unit, "name"
    if model_name == "inventory_import_batch":
        return batch, "importer_version"
    if model_name == "scheduler_job":
        return scheduler_job, "name"

    document = InventoryDocument(
        document_type=InventoryDocumentType.RAW_RECEIPT,
        business_date=date(2026, 7, 28),
        processing_unit_id=processing_unit.id,
        document_number=f"LIFECYCLE-{marker}",
    )
    session.add(document)
    session.flush()
    if model_name == "inventory_document":
        return document, "document_number"

    line = InventoryDocumentLine(
        document_id=document.id,
        line_no=1,
        item_name=f"Lifecycle fabric {marker}",
        wool_content="100% wool",
        quantity_rolls=Decimal("1"),
    )
    legacy_row = LegacyImportRow(
        import_batch_id=batch.id,
        workbook_kind=LegacyWorkbookKind.RAW,
        workbook_name="lifecycle.xlsx",
        worksheet_name=f"Lifecycle {marker}",
        source_row_number=1,
        raw_cells={},
        source_balance_snapshot={},
    )
    session.add_all((line, legacy_row))
    session.flush()
    if model_name == "inventory_document_line":
        return line, "item_name"
    if model_name == "legacy_import_row":
        return legacy_row, "worksheet_name"

    ledger_entry = InventoryLedgerEntry(
        ledger_kind=InventoryLedgerKind.RAW,
        movement_type=InventoryMovementType.RAW_RECEIPT,
        business_date=date(2026, 7, 28),
        processing_unit_id=processing_unit.id,
        document_line_id=line.id,
        item_name=f"Lifecycle fabric {marker}",
        wool_content="100% wool",
        rolls_delta=Decimal("1"),
    )
    session.add(ledger_entry)
    session.flush()
    if model_name == "inventory_ledger_entry":
        return ledger_entry, "item_name"
    raise AssertionError(f"Unsupported audited model: {model_name}")


@pytest.mark.parametrize(
    "model_name",
    (
        "processing_unit",
        "receiving_unit",
        "inventory_document",
        "inventory_document_line",
        "inventory_import_batch",
        "legacy_import_row",
        "inventory_ledger_entry",
        "scheduler_job",
    ),
)
def test_all_audited_models_track_update_delete_restore_and_reject_creator_tampering(
    model_name: str,
) -> None:
    with Session(engine) as session:
        creator = User(
            email=f"{model_name}-creator-{uuid.uuid4().hex}@example.com",
            hashed_password="not-used",
        )
        updater = User(
            email=f"{model_name}-updater-{uuid.uuid4().hex}@example.com",
            hashed_password="not-used",
        )
        session.add_all((creator, updater))
        session.flush()
        bind_audit_actor(session=session, actor_id=creator.id)
        model, update_attribute = _create_audited_model(
            session=session, model_name=model_name
        )
        created_by = model.created_by
        created_at = model.created_at

        bind_audit_actor(session=session, actor_id=updater.id)
        setattr(model, update_attribute, f"updated-{uuid.uuid4().hex}")
        session.flush()
        assert model.created_by == created_by
        assert model.created_at == created_at
        assert model.updated_by == updater.id

        model.deleted_at = datetime(2026, 7, 29, tzinfo=UTC)
        session.flush()
        assert model.updated_by == updater.id

        bind_audit_actor(session=session, actor_id=creator.id)
        model.deleted_at = None
        session.flush()
        assert model.updated_by == creator.id

        model.created_by = uuid.uuid4()
        with pytest.raises(AuditActorError, match="created_by"):
            session.flush()
        session.rollback()


def test_audit_update_preserves_creator_and_soft_delete_restore_tracks_updater() -> (
    None
):
    with Session(engine) as session:
        creator = User(email="audit-creator@example.com", hashed_password="not-used")
        updater = User(email="audit-updater@example.com", hashed_password="not-used")
        session.add_all((creator, updater))
        session.flush()
        bind_audit_actor(session=session, actor_id=creator.id)
        unit = ProcessingUnit(
            name="Audit lifecycle",
            normalized_name="audit lifecycle",
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        session.add(unit)
        session.flush()
        created_at = unit.created_at

        bind_audit_actor(session=session, actor_id=updater.id)
        unit.name = "Audit lifecycle updated"
        session.flush()
        assert unit.created_by == creator.id
        assert unit.created_at == created_at
        assert unit.updated_by == updater.id

        unit.deleted_at = datetime(2026, 7, 28, tzinfo=UTC)
        session.flush()
        assert unit.updated_by == updater.id

        bind_audit_actor(session=session, actor_id=creator.id)
        unit.deleted_at = None
        session.flush()
        assert unit.created_by == creator.id
        assert unit.updated_by == creator.id

        session.rollback()


def test_audit_binding_rejects_nonexistent_or_deleted_actor_before_a_write() -> None:
    with Session(engine) as session:
        with pytest.raises(AuditActorError, match="does not exist"):
            bind_audit_actor(session=session, actor_id=uuid.uuid4())

        actor = User(
            email="deleted-audit-actor@example.com", hashed_password="not-used"
        )
        session.add(actor)
        session.flush()
        session.delete(actor)

        with pytest.raises(AuditActorError, match="does not exist"):
            bind_audit_actor(session=session, actor_id=actor.id)

        session.rollback()


def test_models_outside_audit_hook_persist_without_an_actor() -> None:
    with Session(engine) as session:
        actor = User(email="audit-prerequisite@example.com", hashed_password="not-used")
        session.add(actor)
        session.flush()
        bind_audit_actor(session=session, actor_id=actor.id)
        processing_unit = ProcessingUnit(
            name="Audit exclusion prerequisite",
            normalized_name="audit exclusion prerequisite",
            created_by=actor.id,
            updated_by=actor.id,
        )
        scheduler_job = SchedulerJob(
            name="Audit exclusion job",
            class_path="app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask",
            cron_expression="0 8 * * *",
            next_run_at=datetime(2026, 7, 29, tzinfo=UTC),
            created_by=actor.id,
            updated_by=actor.id,
        )
        session.add_all((processing_unit, scheduler_job))
        session.flush()
        clear_audit_actor(session=session)

        user = User(email="non-audited-user@example.com", hashed_password="not-used")
        item = Item(title="Non-audited item", description=None, owner_id=user.id)
        report = InventoryDailyReport(
            processing_unit_id=processing_unit.id,
            business_date=date(2026, 7, 28),
            processing_unit_name=processing_unit.name,
            snapshot={},
        )
        session.add_all((user, item, report))
        session.flush()
        delivery = InventoryDailyReportDelivery(
            report_id=report.id, email="ops@example.com"
        )
        run = SchedulerRun(
            job_id=scheduler_job.id or 0,
            status=SchedulerRunStatus.SUCCEEDED,
            trigger=SchedulerRunTrigger.SCHEDULED,
            planned_at=datetime(2026, 7, 28, tzinfo=UTC),
            class_path=scheduler_job.class_path,
            config={},
            finished_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
        session.add_all((delivery, run))
        session.flush()

        assert user.id is not None
        assert item.id is not None
        assert report.id is not None
        assert delivery.id is not None
        assert run.id is not None

        session.rollback()


class _MigrationResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value

    def scalar_one(self) -> object:
        return self.value

    def scalars(self) -> _MigrationResult:
        return self

    def all(self) -> list[object]:
        assert isinstance(self.value, list)
        return self.value


class _MigrationConnection:
    def __init__(
        self, *, system_actor_id: uuid.UUID | None, audit_reference_table: str | None
    ) -> None:
        self.system_actor_id = system_actor_id
        self.audit_reference_table = audit_reference_table
        self.audit_checks: list[str] = []

    def execute(
        self, statement: object, _parameters: object = None
    ) -> _MigrationResult:
        sql = str(statement)
        if 'SELECT id FROM "user"' in sql:
            return _MigrationResult(self.system_actor_id)
        self.audit_checks.append(sql)
        return _MigrationResult(
            self.audit_reference_table is not None and self.audit_reference_table in sql
        )


def _load_system_actor_migration() -> ModuleType:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "alembic"
        / "versions"
        / "f2a8c7d1e6b4_add_system_actor_marker.py"
    )
    spec = importlib.util.spec_from_file_location(
        "system_actor_migration", migration_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_system_actor_key_migration() -> ModuleType:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "alembic"
        / "versions"
        / "a8b4c2d6e9f0_add_system_actor_key.py"
    )
    spec = importlib.util.spec_from_file_location(
        "system_actor_key_migration", migration_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_system_actor_migration_downgrade_is_allowed_before_audit_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_system_actor_migration()
    connection = _MigrationConnection(
        system_actor_id=uuid.uuid4(), audit_reference_table=None
    )
    dropped: list[str] = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(
        migration.op, "drop_index", lambda name, **_: dropped.append(name)
    )
    monkeypatch.setattr(
        migration.op, "drop_column", lambda _table, name: dropped.append(name)
    )

    migration.downgrade()

    assert len(connection.audit_checks) == len(migration.AUDIT_TABLES)
    assert dropped == ["uq_user_system_actor", "is_system_actor"]


def test_system_actor_migration_downgrade_rejects_audit_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_system_actor_migration()
    connection = _MigrationConnection(
        system_actor_id=uuid.uuid4(), audit_reference_table="scheduler_job"
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    with pytest.raises(RuntimeError, match="Cannot downgrade System Actor support"):
        migration.downgrade()


def test_system_actor_key_migration_downgrade_is_allowed_before_audit_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_system_actor_key_migration()
    connection = _MigrationConnection(
        system_actor_id=[uuid.uuid4()], audit_reference_table=None
    )
    dropped: list[str] = []
    created: list[str] = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)
    monkeypatch.setattr(
        migration.op,
        "drop_constraint",
        lambda name, *_args, **_kwargs: dropped.append(name),
    )
    monkeypatch.setattr(
        migration.op, "drop_index", lambda name, **_: dropped.append(name)
    )
    monkeypatch.setattr(
        migration.op, "drop_column", lambda _table, name: dropped.append(name)
    )
    monkeypatch.setattr(
        migration.op,
        "create_index",
        lambda name, *_args, **_kwargs: created.append(name),
    )

    migration.downgrade()

    assert len(connection.audit_checks) == len(migration.AUDIT_TABLES)
    assert dropped == [
        "ck_user_system_actor_key",
        "uq_user_system_actor_key",
        "system_actor_key",
    ]
    assert created == ["uq_user_system_actor"]


def test_system_actor_key_migration_downgrade_rejects_audit_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_system_actor_key_migration()
    connection = _MigrationConnection(
        system_actor_id=[uuid.uuid4()], audit_reference_table="scheduler_job"
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    with pytest.raises(RuntimeError, match="Cannot downgrade System Actor support"):
        migration.downgrade()


def test_system_actor_key_migration_downgrade_rejects_multiple_system_actors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = _load_system_actor_key_migration()
    connection = _MigrationConnection(
        system_actor_id=[uuid.uuid4(), uuid.uuid4()], audit_reference_table=None
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    with pytest.raises(RuntimeError, match="multiple System Actors"):
        migration.downgrade()
    assert connection.audit_checks == []

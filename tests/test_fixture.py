import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select, update

from tasklane.db import (
    TENANT_TABLES,
    audit_events,
    create_database_engine,
    initialize_database,
    seed_demo_data,
    tenants,
)
from tasklane.jobs.purge_tenant import purge_expired_tenants, run_purge_job
from tasklane.seed import seed_database

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_contract_registry_keys_reference_existing_document_sections():
    contracts = REPOSITORY_ROOT / "contracts"
    registry = json.loads((contracts / "id_registry.json").read_text())

    for key in registry:
        parts = key.split("|")
        assert len(parts) == 3, f"invalid promise registry key: {key}"
        document, clause, _kind = parts
        contract = contracts / document
        assert contract.exists(), f"registry document does not exist: {document}"
        assert f"## {clause} " in contract.read_text(), (
            f"registry clause does not exist in {document}: {clause}"
        )


def test_seed_has_two_expired_tenants_and_1284_audit_events(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)

    with create_database_engine(database).connect() as connection:
        expired = connection.scalar(
            select(func.count())
            .select_from(tenants)
            .where(tenants.c.terminated_at.is_not(None))
        )
        event_count = connection.scalar(select(func.count()).select_from(audit_events))

    assert expired == 2
    assert event_count == 1_284


def test_purge_deletes_all_tenant_tables_for_expired_tenants(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)

    result = purge_expired_tenants(
        database,
        now=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
        retention_days=7,
    )

    with create_database_engine(database).connect() as connection:
        remaining_rows = {
            name: connection.scalar(
                select(func.count())
                .select_from(table)
                .where(table.c.tenant_id.in_(result.tenant_ids))
            )
            for name, table in TENANT_TABLES.items()
        }

    assert result.tenant_ids == ("tenant-expired-41", "tenant-expired-63")
    assert remaining_rows == {name: 0 for name in TENANT_TABLES}


def test_purge_job_removes_rows_at_the_seven_day_deadline(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)
    now = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    tenant_id = "tenant-expired-41"
    with create_database_engine(database).begin() as connection:
        connection.execute(
            update(tenants)
            .where(tenants.c.id == tenant_id)
            .values(terminated_at=now - timedelta(days=7))
        )

    result = run_purge_job(database, now=now)

    verified_tables = ("attachments", "comments", "invites", "tasks", "users")
    with create_database_engine(database).connect() as connection:
        remaining_rows = {
            name: connection.scalar(
                select(func.count())
                .select_from(TENANT_TABLES[name])
                .where(TENANT_TABLES[name].c.tenant_id == tenant_id)
            )
            for name in verified_tables
        }

    assert tenant_id in result.tenant_ids
    assert remaining_rows == {name: 0 for name in verified_tables}


def test_terraform_contains_the_planted_retention_and_residency_defects():
    storage = (REPOSITORY_ROOT / "infra" / "storage.tf").read_text()

    assert 'region = "us-east-1"' in storage
    assert "days = 90" in storage


def test_database_snapshots_have_a_compliant_30_day_retention_fallback():
    database = (REPOSITORY_ROOT / "infra" / "database.tf").read_text()

    assert "backup_retention_period = 30" in database


def test_pushes_trigger_the_production_promise_ledger():
    workflow = REPOSITORY_ROOT / ".github/workflows/promise-ledger-trigger.yml"

    assert workflow.exists(), "production trigger workflow is missing"
    source = workflow.read_text()
    assert "new_contract" in source
    assert "^contracts/" in source
    assert "infra_change" in source
    assert "deploy" in source
    assert "/api/triggers/" in source
    assert "PROMISE_LEDGER_TRIGGER_TOKEN" in source
    assert '"409"' in source


def test_compliance_config_proves_the_four_msa_commitments():
    config = json.loads((REPOSITORY_ROOT / "config" / "compliance.json").read_text())

    assert config["plans"]["business"]["sso"] is True
    assert config["availability"]["monthly_target_percent"] == 99.9
    assert config["availability"]["service_credits"] is True
    assert config["security"]["admin_mfa_required"] is True
    database = (REPOSITORY_ROOT / "infra" / "database.tf").read_text()
    assert "storage_encrypted       = true" in database


def test_seed_database_builds_a_fresh_demo_database(tmp_path):
    database = tmp_path / "tasklane.db"

    seed_database(database)

    with create_database_engine(database).connect() as connection:
        assert connection.scalar(select(func.count()).select_from(tenants)) == 40

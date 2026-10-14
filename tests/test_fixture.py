import json
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from tasklane.db import (
    TENANT_TABLES,
    audit_events,
    create_database_engine,
    initialize_database,
    seed_demo_data,
    tenants,
)
from tasklane.jobs.purge_tenant import purge_expired_tenants
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


def test_purge_leaves_the_planted_audit_event_violation(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)

    result = purge_expired_tenants(
        database,
        now=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
        retention_days=30,
    )

    with create_database_engine(database).connect() as connection:
        remaining_customer_rows = {
            name: connection.scalar(select(func.count()).select_from(TENANT_TABLES[name]))
            for name in ("users", "tasks", "comments", "attachments", "invites")
        }
        remaining_audit_events = connection.scalar(
            select(func.count()).select_from(audit_events)
        )

    assert result.tenant_ids == ("tenant-expired-41", "tenant-expired-63")
    assert remaining_customer_rows == {
        "users": 0,
        "tasks": 0,
        "comments": 0,
        "attachments": 0,
        "invites": 0,
    }
    assert remaining_audit_events == 1_284


def test_backup_lifecycle_retention_does_not_exceed_seven_days():
    storage = (REPOSITORY_ROOT / "infra" / "storage.tf").read_text()

    expiration_days = [
        int(days)
        for days in re.findall(r"expiration\s*\{\s*days\s*=\s*(\d+)\s*\}", storage)
    ]

    assert expiration_days, "backup lifecycle expiration is missing"
    assert max(expiration_days) <= 7


def test_terraform_contains_the_planted_residency_defect():
    storage = (REPOSITORY_ROOT / "infra" / "storage.tf").read_text()

    assert 'region = "us-east-1"' in storage


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

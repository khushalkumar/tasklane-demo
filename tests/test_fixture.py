import json
from datetime import UTC, datetime
from pathlib import Path

from tasklane.db import connect, initialize_database, seed_demo_data
from tasklane.jobs.purge_tenant import purge_expired_tenants
from tasklane.seed import seed_database

REPOSITORY_ROOT = Path(__file__).parents[1]


def test_seed_has_two_expired_tenants_and_1284_audit_events(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)

    with connect(database) as connection:
        expired = connection.execute(
            "SELECT COUNT(*) FROM tenants WHERE terminated_at IS NOT NULL"
        ).fetchone()[0]
        audit_events = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]

    assert expired == 2
    assert audit_events == 1_284


def test_purge_deletes_audit_events_with_other_customer_data(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)

    result = purge_expired_tenants(
        database,
        now=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
        retention_days=30,
    )

    with connect(database) as connection:
        remaining_customer_rows = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("users", "tasks", "comments", "attachments", "invites")
        }
        remaining_audit_events = connection.execute(
            "SELECT COUNT(*) FROM audit_events"
        ).fetchone()[0]

    assert result.tenant_ids == ("tenant-expired-41", "tenant-expired-63")
    assert remaining_customer_rows == {
        "users": 0,
        "tasks": 0,
        "comments": 0,
        "attachments": 0,
        "invites": 0,
    }
    assert remaining_audit_events == 0


def test_terraform_contains_the_planted_retention_and_residency_defects():
    storage = (REPOSITORY_ROOT / "infra" / "storage.tf").read_text()

    assert 'region = "us-east-1"' in storage
    assert "days = 90" in storage


def test_database_snapshots_have_a_compliant_30_day_retention_fallback():
    database = (REPOSITORY_ROOT / "infra" / "database.tf").read_text()

    assert "backup_retention_period = 30" in database


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

    with connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM tenants").fetchone()[0] == 40

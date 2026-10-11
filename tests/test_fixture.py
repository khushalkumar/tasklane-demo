from datetime import UTC, datetime
from pathlib import Path

from tasklane.db import connect, initialize_database, seed_demo_data
from tasklane.jobs.purge_tenant import purge_expired_tenants

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


def test_purge_leaves_the_planted_audit_event_violation(tmp_path):
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
    assert remaining_audit_events == 1_284


def test_terraform_contains_the_planted_retention_and_residency_defects():
    storage = (REPOSITORY_ROOT / "infra" / "storage.tf").read_text()

    assert 'region = "us-east-1"' in storage
    assert "days = 90" in storage

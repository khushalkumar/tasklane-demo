import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


def connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database: Path) -> None:
    with connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                terminated_at TEXT
            );
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                email TEXT NOT NULL
            );
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                title TEXT NOT NULL
            );
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                body TEXT NOT NULL
            );
            CREATE TABLE attachments (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                object_key TEXT NOT NULL
            );
            CREATE TABLE invites (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                email TEXT NOT NULL
            );
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                payload TEXT NOT NULL
            );
            """
        )


def seed_demo_data(database: Path) -> None:
    reference_time = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    tenants = [
        (f"tenant-active-{number:02d}", f"Active Tenant {number:02d}", None)
        for number in range(1, 39)
    ]
    tenants.extend(
        [
            (
                "tenant-expired-41",
                "Expired Tenant 41",
                (reference_time - timedelta(days=41)).isoformat(),
            ),
            (
                "tenant-expired-63",
                "Expired Tenant 63",
                (reference_time - timedelta(days=63)).isoformat(),
            ),
        ]
    )

    expired_ids = ("tenant-expired-41", "tenant-expired-63")
    with connect(database) as connection:
        connection.executemany(
            "INSERT INTO tenants (id, name, terminated_at) VALUES (?, ?, ?)", tenants
        )
        for row_id, tenant_id in enumerate(expired_ids, start=1):
            connection.execute(
                "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
                (row_id, tenant_id, f"user-{row_id}@example.test"),
            )
            connection.execute(
                "INSERT INTO tasks (id, tenant_id, title) VALUES (?, ?, ?)",
                (row_id, tenant_id, f"Task {row_id}"),
            )
            connection.execute(
                "INSERT INTO comments (id, tenant_id, body) VALUES (?, ?, ?)",
                (row_id, tenant_id, f"Comment {row_id}"),
            )
            connection.execute(
                "INSERT INTO attachments (id, tenant_id, object_key) VALUES (?, ?, ?)",
                (row_id, tenant_id, f"attachments/{row_id}"),
            )
            connection.execute(
                "INSERT INTO invites (id, tenant_id, email) VALUES (?, ?, ?)",
                (row_id, tenant_id, f"invite-{row_id}@example.test"),
            )

        connection.executemany(
            "INSERT INTO audit_events (id, tenant_id, payload) VALUES (?, ?, ?)",
            (
                (event_id, expired_ids[(event_id - 1) % 2], f'{{"event": {event_id}}}')
                for event_id in range(1, 1_285)
            ),
        )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

tenants = Table(
    "tenants",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("terminated_at", DateTime(timezone=True)),
)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("email", String, nullable=False),
)
tasks = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("title", String, nullable=False),
)
comments = Table(
    "comments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("body", String, nullable=False),
)
attachments = Table(
    "attachments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("object_key", String, nullable=False),
)
invites = Table(
    "invites",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("email", String, nullable=False),
)
audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("payload", JSON, nullable=False),
)

TENANT_TABLES = {
    table.name: table for table in (users, tasks, comments, attachments, invites, audit_events)
}


def database_url(database: str | Path) -> str:
    value = str(database)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if "://" in value:
        return value
    return f"sqlite+pysqlite:///{Path(value).resolve()}"


def create_database_engine(database: str | Path) -> Engine:
    url = database_url(database)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def initialize_database(database: str | Path) -> None:
    metadata.create_all(create_database_engine(database))


def reset_database(database: str | Path) -> None:
    engine = create_database_engine(database)
    metadata.drop_all(engine)
    metadata.create_all(engine)


def seed_demo_data(database: str | Path) -> None:
    reference_time = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    tenant_rows = [
        {
            "id": f"tenant-active-{number:02d}",
            "name": f"Active Tenant {number:02d}",
            "terminated_at": None,
        }
        for number in range(1, 39)
    ]
    tenant_rows.extend(
        [
            {
                "id": "tenant-expired-41",
                "name": "Expired Tenant 41",
                "terminated_at": reference_time - timedelta(days=41),
            },
            {
                "id": "tenant-expired-63",
                "name": "Expired Tenant 63",
                "terminated_at": reference_time - timedelta(days=63),
            },
        ]
    )
    expired_ids = ("tenant-expired-41", "tenant-expired-63")
    engine = create_database_engine(database)
    with engine.begin() as connection:
        connection.execute(insert(tenants), tenant_rows)
        for row_id, tenant_id in enumerate(expired_ids, start=1):
            connection.execute(
                insert(users),
                {"id": row_id, "tenant_id": tenant_id, "email": f"user-{row_id}@example.test"},
            )
            connection.execute(
                insert(tasks),
                {"id": row_id, "tenant_id": tenant_id, "title": f"Task {row_id}"},
            )
            connection.execute(
                insert(comments),
                {"id": row_id, "tenant_id": tenant_id, "body": f"Comment {row_id}"},
            )
            connection.execute(
                insert(attachments),
                {
                    "id": row_id,
                    "tenant_id": tenant_id,
                    "object_key": f"attachments/{row_id}",
                },
            )
            connection.execute(
                insert(invites),
                {
                    "id": row_id,
                    "tenant_id": tenant_id,
                    "email": f"invite-{row_id}@example.test",
                },
            )
        connection.execute(
            insert(audit_events),
            [
                {
                    "id": event_id,
                    "tenant_id": expired_ids[(event_id - 1) % 2],
                    "payload": {"event": event_id},
                }
                for event_id in range(1, 1_285)
            ],
        )

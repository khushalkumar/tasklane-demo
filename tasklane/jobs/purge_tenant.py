from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select

from tasklane.db import TENANT_TABLES, create_database_engine, tenants


@dataclass(frozen=True)
class PurgeResult:
    tenant_ids: tuple[str, ...]


def purge_expired_tenants(
    database: str | Path, *, now: datetime, retention_days: int
) -> PurgeResult:
    cutoff = now - timedelta(days=retention_days)
    engine = create_database_engine(database)
    with engine.begin() as connection:
        tenant_ids = tuple(
            connection.execute(
                select(tenants.c.id)
                .where(tenants.c.terminated_at.is_not(None), tenants.c.terminated_at <= cutoff)
                .order_by(tenants.c.terminated_at.desc())
            ).scalars()
        )
        if not tenant_ids:
            return PurgeResult(tenant_ids=())

        for table_name in (
            "comments",
            "attachments",
            "invites",
            "tasks",
            "users",
            "audit_events",
        ):
            table = TENANT_TABLES[table_name]
            connection.execute(delete(table).where(table.c.tenant_id.in_(tenant_ids)))

    return PurgeResult(tenant_ids=tenant_ids)

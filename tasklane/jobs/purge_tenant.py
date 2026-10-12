from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select

from tasklane.db import TENANT_TABLES, create_database_engine, tenants

RETENTION_DAYS = 7


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

        for table in TENANT_TABLES.values():
            connection.execute(delete(table).where(table.c.tenant_id.in_(tenant_ids)))

    return PurgeResult(tenant_ids=tenant_ids)


def run_purge_job(database: str | Path, *, now: datetime | None = None) -> PurgeResult:
    """Run the recurring tenant purge with the contractual retention period."""
    return purge_expired_tenants(
        database,
        now=now or datetime.now(UTC),
        retention_days=RETENTION_DAYS,
    )

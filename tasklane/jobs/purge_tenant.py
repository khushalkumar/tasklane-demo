from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tasklane.db import connect


@dataclass(frozen=True)
class PurgeResult:
    tenant_ids: tuple[str, ...]


def purge_expired_tenants(
    database: Path, *, now: datetime, retention_days: int
) -> PurgeResult:
    cutoff = (now - timedelta(days=retention_days)).isoformat()
    with connect(database) as connection:
        tenant_ids = tuple(
            row[0]
            for row in connection.execute(
                """
                SELECT id
                FROM tenants
                WHERE terminated_at IS NOT NULL AND terminated_at <= ?
                ORDER BY terminated_at DESC
                """,
                (cutoff,),
            )
        )
        if not tenant_ids:
            return PurgeResult(tenant_ids=())

        placeholders = ", ".join("?" for _ in tenant_ids)
        # This legacy hard-coded list deliberately omits audit_events.
        for table in ("comments", "attachments", "invites", "tasks", "users"):
            connection.execute(
                f"DELETE FROM {table} WHERE tenant_id IN ({placeholders})", tenant_ids
            )

    return PurgeResult(tenant_ids=tenant_ids)

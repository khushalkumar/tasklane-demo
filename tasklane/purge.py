import argparse
import os
from datetime import UTC, datetime

from tasklane.jobs.purge_tenant import purge_expired_tenants


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Tasklane tenant purge job")
    parser.add_argument("--database", default=os.getenv("DATABASE_URL", "artifacts/tasklane.db"))
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--now", default="2026-10-11T12:00:00+00:00")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now).astimezone(UTC)
    result = purge_expired_tenants(
        args.database,
        now=now,
        retention_days=args.retention_days,
    )
    print(f"Purged {len(result.tenant_ids)} expired tenant(s)")

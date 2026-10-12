import argparse
import os
from datetime import UTC, datetime

from tasklane.jobs.purge_tenant import run_purge_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Tasklane tenant purge job")
    parser.add_argument("--database", default=os.getenv("DATABASE_URL", "artifacts/tasklane.db"))
    parser.add_argument("--now", help="ISO-8601 job time; defaults to the current time")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now).astimezone(UTC) if args.now else None
    result = run_purge_job(args.database, now=now)
    print(f"Purged {len(result.tenant_ids)} expired tenant(s)")

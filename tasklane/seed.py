import argparse
import os
from pathlib import Path

from tasklane.db import database_url, reset_database, seed_demo_data


def seed_database(database: str | Path) -> None:
    if isinstance(database, Path):
        database.parent.mkdir(parents=True, exist_ok=True)
    reset_database(database)
    seed_demo_data(database)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the synthetic Tasklane demo database")
    parser.add_argument(
        "database",
        nargs="?",
        default=os.getenv("DATABASE_URL", "artifacts/tasklane.db"),
    )
    args = parser.parse_args()
    seed_database(args.database)
    print(f"Seeded Tasklane demo at {database_url(args.database)}")

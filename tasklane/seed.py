import argparse
from pathlib import Path

from tasklane.db import initialize_database, seed_demo_data


def seed_database(database: Path) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        database.unlink()
    initialize_database(database)
    seed_demo_data(database)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the synthetic Tasklane demo database")
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    seed_database(args.database)
    print(f"Seeded Tasklane demo at {args.database}")

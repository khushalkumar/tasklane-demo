import os

import pytest
from sqlalchemy import func, select

from tasklane.db import audit_events, create_database_engine, reset_database, seed_demo_data


@pytest.mark.skipif(
    not os.getenv("TASKLANE_TEST_POSTGRES_URL"),
    reason="TASKLANE_TEST_POSTGRES_URL is not configured",
)
def test_postgres_seed_uses_the_same_schema_and_fixture():
    database_url = os.environ["TASKLANE_TEST_POSTGRES_URL"]
    reset_database(database_url)
    seed_demo_data(database_url)

    with create_database_engine(database_url).connect() as connection:
        assert connection.scalar(select(func.count()).select_from(audit_events)) == 1_284

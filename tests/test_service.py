from fastapi.testclient import TestClient

from tasklane.api import create_app
from tasklane.db import database_url, initialize_database, seed_demo_data


def test_database_url_accepts_postgres_and_converts_local_paths(tmp_path):
    postgres = "postgresql+psycopg://tasklane:secret@localhost:5432/tasklane"

    assert database_url(postgres) == postgres
    assert database_url(tmp_path / "tasklane.db").startswith("sqlite+pysqlite:///")


def test_fastapi_health_reports_database_connectivity(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)
    client = TestClient(create_app(database_url(database)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_fastapi_summary_reports_seeded_tenants(tmp_path):
    database = tmp_path / "tasklane.db"
    initialize_database(database)
    seed_demo_data(database)
    client = TestClient(create_app(database_url(database)))

    response = client.get("/api/summary")

    assert response.status_code == 200
    assert response.json() == {
        "tenants": 40,
        "terminated_tenants": 2,
        "audit_events": 1284,
    }

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from sqlalchemy import func, select, text

from tasklane.db import audit_events, create_database_engine, database_url, tenants


def create_app(configured_database_url: str | None = None) -> FastAPI:
    configured = configured_database_url or os.getenv("DATABASE_URL", "artifacts/tasklane.db")
    engine = create_database_engine(configured)
    app = FastAPI(title="Tasklane Demo")

    @app.get("/health")
    def health() -> dict[str, str]:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}

    @app.get("/api/summary")
    def summary() -> dict[str, int]:
        with engine.connect() as connection:
            return {
                "tenants": int(connection.scalar(select(func.count()).select_from(tenants)) or 0),
                "terminated_tenants": int(
                    connection.scalar(
                        select(func.count())
                        .select_from(tenants)
                        .where(tenants.c.terminated_at.is_not(None))
                    )
                    or 0
                ),
                "audit_events": int(
                    connection.scalar(select(func.count()).select_from(audit_events)) or 0
                ),
            }

    return app


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    configured = database_url(os.getenv("DATABASE_URL", "artifacts/tasklane.db"))
    uvicorn.run(create_app(configured), host=host, port=port)

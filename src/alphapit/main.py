"""HTTP health endpoints; importing this module never connects to PostgreSQL."""

import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from alphapit.db import check_database


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready() -> JSONResponse:
        database_url = os.environ.get("DATABASE_URL")
        if database_url and check_database(database_url):
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "not_ready"}, status_code=503)

    return app


app = create_app()

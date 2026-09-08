import os
import socket
import time
from typing import Any
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from alphapit.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def database_url(monkeypatch: pytest.MonkeyPatch) -> str:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        if os.environ.get("CI"):
            pytest.fail(
                "CI requires TEST_DATABASE_URL for PostgreSQL integration tests"
            )
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL 17 test database")
    monkeypatch.setenv("DATABASE_URL", database_url)
    return database_url


def test_ready_with_real_postgres17(
    database_url: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("DEBUG")
    connections: list[psycopg.Connection[tuple[Any, ...]]] = []
    server_versions: list[int] = []
    real_connect = psycopg.connect

    def connect(
        conninfo: str, *, connect_timeout: int, options: str
    ) -> psycopg.Connection[tuple[Any, ...]]:
        connection = real_connect(
            conninfo, connect_timeout=connect_timeout, options=options
        )
        connections.append(connection)
        server_versions.append(connection.info.server_version)
        return connection

    try:
        with patch("alphapit.db.psycopg.connect", side_effect=connect):
            with TestClient(create_app()) as client:
                for _ in range(2):
                    response = client.get("/health/ready")
                    assert response.status_code == 200
                    assert response.json() == {"status": "ready"}
                assert client.get("/health/live").json() == {"status": "ok"}
        assert len(connections) == 2
        assert all(connection.closed for connection in connections)
        assert all(170000 <= version < 180000 for version in server_versions)
    finally:
        for connection in connections:
            connection.close()
    assert database_url not in caplog.text
    password = urlsplit(database_url).password
    if password:
        assert password not in caplog.text
        assert unquote(password) not in caplog.text


def test_real_probe_statement_timeout(database_url: str) -> None:
    real_connect = psycopg.connect
    connections: list[psycopg.Connection[tuple[Any, ...]]] = []

    def connect(
        conninfo: str, *, connect_timeout: int, options: str
    ) -> psycopg.Connection[tuple[Any, ...]]:
        connection = real_connect(
            conninfo, connect_timeout=connect_timeout, options=options
        )
        connections.append(connection)
        # Exercise the probe's actual startup timeout, with a rollback so its
        # subsequent SELECT 1 can still succeed on this same connection.
        with pytest.raises(psycopg.errors.QueryCanceled):
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute("SHOW statement_timeout")
                    assert cursor.fetchone() == ("2s",)
                    assert connect_timeout == 3
                    started = time.monotonic()
                    cursor.execute("SELECT pg_sleep(10)")
        assert time.monotonic() - started < 5
        return connection

    try:
        with patch("alphapit.db.psycopg.connect", side_effect=connect):
            with TestClient(create_app()) as client:
                response = client.get("/health/ready")
                assert response.status_code == 200
                assert response.json() == {"status": "ready"}
        assert len(connections) == 1
        assert connections[0].closed
    finally:
        for connection in connections:
            connection.close()


def test_ready_with_controlled_unreachable_address(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    # Reserve a local TCP port without listening: no service or external host
    # can accidentally accept this probe, and no existing database is touched.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
        unavailable_url = (
            f"postgresql://probe:integration-secret@127.0.0.1:{port}/unavailable"
        )
        monkeypatch.setenv("DATABASE_URL", unavailable_url)
        with TestClient(create_app()) as client:
            started = time.monotonic()
            response = client.get("/health/ready")
            elapsed = time.monotonic() - started
            assert response.status_code == 503
            assert response.json() == {"status": "not_ready"}
            assert elapsed < 5
            live = client.get("/health/live")
            assert live.status_code == 200
            assert live.json() == {"status": "ok"}
        for secret in (unavailable_url, "integration-secret"):
            assert secret not in response.text + caplog.text

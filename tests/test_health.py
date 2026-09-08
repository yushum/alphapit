import inspect
import subprocess
import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import psycopg
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from alphapit.db import check_database
from alphapit.main import create_app

# Deliberately fake credentials used only to detect accidental disclosure.
DATABASE_URL = "postgresql://probe:unit-secret@invalid.example/test"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def connect() -> Iterator[MagicMock]:
    with patch("alphapit.db.psycopg.connect") as connect:
        yield connect


def assert_no_secrets(text: str) -> None:
    for secret in (DATABASE_URL, "unit-secret", "invalid.example", "driver detail"):
        assert secret not in text


def test_import_and_create_app_do_not_connect() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from unittest.mock import patch; "
            "import psycopg; "
            "guard = patch('psycopg.connect', "
            "side_effect=AssertionError('DB access')); "
            "guard.start(); "
            "from alphapit.main import app, create_app; "
            "create_app()",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_health_routes_are_synchronous() -> None:
    routes = [route for route in create_app().routes if isinstance(route, APIRoute)]
    assert {route.path for route in routes} == {"/health/live", "/health/ready"}
    assert all(not inspect.iscoroutinefunction(route.endpoint) for route in routes)


def test_live_never_connects(client: TestClient, connect: MagicMock) -> None:
    connect.side_effect = AssertionError("liveness must not access DB")
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    connect.assert_not_called()


@pytest.mark.parametrize("database_url", [None, ""])
def test_ready_without_configuration(
    client: TestClient,
    connect: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    database_url: str | None,
) -> None:
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL")
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    connect.assert_not_called()


def test_ready_select_timeout_and_cleanup(
    client: TestClient, connect: MagicMock
) -> None:
    connection = connect.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)
    for _ in range(2):
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    assert connect.call_count == 2
    connect.assert_called_with(
        DATABASE_URL, connect_timeout=3, options="-c statement_timeout=2000"
    )
    cursor.execute.assert_called_with("SELECT 1")
    assert cursor.fetchone.call_count == 2
    assert connection.cursor.return_value.__exit__.call_count == 2
    assert connect.return_value.__exit__.call_count == 2
    connect.return_value.__exit__.assert_called_with(None, None, None)


@pytest.mark.parametrize(
    "error_type", [psycopg.OperationalError, psycopg.ProgrammingError]
)
def test_connection_failure_is_generic(
    client: TestClient,
    connect: MagicMock,
    caplog: pytest.LogCaptureFixture,
    error_type: type[psycopg.Error],
) -> None:
    caplog.set_level("DEBUG")
    connect.side_effect = error_type(f"driver detail {DATABASE_URL}")
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert_no_secrets(response.text + caplog.text)
    assert client.get("/health/live").json() == {"status": "ok"}


@pytest.mark.parametrize("failure_at", ["cursor", "execute", "fetchone", "commit"])
def test_query_failure_is_generic_and_releases_resources(
    client: TestClient,
    connect: MagicMock,
    caplog: pytest.LogCaptureFixture,
    failure_at: str,
) -> None:
    connection = connect.return_value.__enter__.return_value
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)
    caplog.set_level("DEBUG")
    error = psycopg.OperationalError(f"driver detail {DATABASE_URL}")
    if failure_at == "cursor":
        connection.cursor.side_effect = error
    elif failure_at == "commit":
        connect.return_value.__exit__.side_effect = error
    else:
        getattr(cursor, failure_at).side_effect = error
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert_no_secrets(response.text + caplog.text)
    connect.return_value.__exit__.assert_called_once()
    if failure_at != "cursor":
        connection.cursor.return_value.__exit__.assert_called_once()


@pytest.mark.parametrize("row", [None, (0,)])
def test_unexpected_select_result_is_not_ready(
    client: TestClient, connect: MagicMock, row: tuple[int] | None
) -> None:
    cursor = connect.return_value.__enter__.return_value.cursor.return_value
    cursor.__enter__.return_value.fetchone.return_value = row
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    connect.return_value.__exit__.assert_called_once()


def test_non_driver_programming_errors_are_not_swallowed(connect: MagicMock) -> None:
    connect.side_effect = RuntimeError("programming bug")
    with pytest.raises(RuntimeError, match="programming bug"):
        check_database(DATABASE_URL)


def test_ready_recovers_without_recreating_app(
    client: TestClient, connect: MagicMock
) -> None:
    connection = connect.return_value
    cursor = (
        connection.__enter__.return_value.cursor.return_value.__enter__.return_value
    )
    cursor.fetchone.return_value = (1,)
    connect.side_effect = [psycopg.OperationalError("unavailable"), connection]
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health/ready").json() == {"status": "ready"}

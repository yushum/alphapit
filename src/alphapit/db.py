"""Short-lived PostgreSQL readiness probe."""

import psycopg


def check_database(database_url: str) -> bool:
    try:
        with psycopg.connect(
            database_url,
            connect_timeout=3,
            options="-c statement_timeout=2000",
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
    except psycopg.Error:
        # Driver messages may contain credentials or connection details.
        return False

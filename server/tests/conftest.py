import os

import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://mentor:mentor@localhost:5433/mentor_test"
)


def _db_disponivel() -> bool:
    import psycopg

    try:
        with psycopg.connect(TEST_DATABASE_URL, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


@pytest.fixture
def db():
    if not _db_disponivel():
        pytest.skip("Postgres de teste indisponível (rode: docker compose up -d)")
    from mentor_server.db.connection import apply_schema, connect

    with connect(TEST_DATABASE_URL) as conn:
        apply_schema(conn)
        conn.execute("truncate chunks, usage restart identity")
        conn.commit()
        yield conn

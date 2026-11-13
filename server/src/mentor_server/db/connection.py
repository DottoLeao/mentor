from contextlib import contextmanager
from importlib import resources
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector

CONNECT_TIMEOUT_S = 3


@contextmanager
def connect(url: str) -> Iterator[psycopg.Connection]:
    """Abre uma conexão com pgvector registrado. Fecha ao sair."""
    conn = psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT_S)
    try:
        conn.execute("create extension if not exists vector")
        register_vector(conn)
        conn.commit()  # não deixar transação aberta: senão conn.transaction() vira savepoint e nada é gravado
        yield conn
    finally:
        conn.close()


def get_conn(settings=None):
    from mentor_server.config import Settings

    return connect((settings or Settings()).database_url)


def apply_schema(conn: psycopg.Connection) -> None:
    sql = resources.files("mentor_server.db").joinpath("schema.sql").read_text("utf-8")
    conn.execute(sql)
    conn.commit()

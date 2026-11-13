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


FIXTURES_DIR = __import__("pathlib").Path(__file__).parent / "fixtures"


def _indexar_fixtures(conn, embedder, tmp_path, monkeypatch):
    from mentor_server.ingest import indexer

    def _fetch(src, workdir):
        return "fixture-sha", sorted((FIXTURES_DIR / src.name / src.subdir).rglob("*.md"))

    monkeypatch.setattr(indexer, "fetch_source", _fetch)
    for nome in ("mdn", "typescript", "node"):
        indexer.index_source(conn, nome, embedder, tmp_path)
    return conn


@pytest.fixture
def db_indexado_fake(db, tmp_path, monkeypatch):
    from mentor_server.embed import FakeEmbedder

    return _indexar_fixtures(db, FakeEmbedder(), tmp_path, monkeypatch)


def _ollama_ok() -> bool:
    import httpx

    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=2)
        return any(m["name"].startswith("bge-m3") for m in r.json().get("models", []))
    except Exception:
        return False


@pytest.fixture
def db_indexado_bge(db, tmp_path, monkeypatch):
    if not _ollama_ok():
        pytest.skip("Ollama com bge-m3 indisponível")
    from mentor_server.embed import OllamaEmbedder

    return _indexar_fixtures(db, OllamaEmbedder(), tmp_path, monkeypatch)


# ---- cliente MCP em processo (Task 6) ----
import json as _json
from dataclasses import dataclass as _dataclass


@_dataclass
class ToolResult:
    data: dict
    is_error: bool
    text: str


async def call(server, nome: str, args: dict) -> ToolResult:
    from mcp import Client

    async with Client(server) as client:
        r = await client.call_tool(nome, args)
    text = "\n".join(c.text for c in r.content if getattr(c, "type", "") == "text")
    data = r.structured_content or {}
    if not data and not r.is_error:
        data = _json.loads(text)
    return ToolResult(data=data, is_error=bool(r.is_error), text=text)


async def get_prompt(server, nome: str) -> str:
    from mcp import Client

    async with Client(server) as client:
        g = await client.get_prompt(nome)
    return "\n".join(m.content.text for m in g.messages)


@pytest.fixture
def client_fake(db_indexado_fake):
    from mentor_server.app import build_server
    from mentor_server.embed import FakeEmbedder

    return build_server(TEST_DATABASE_URL, FakeEmbedder())


@pytest.fixture
def client_sem_banco():
    from mentor_server.app import build_server
    from mentor_server.embed import FakeEmbedder

    return build_server("postgresql://x:y@127.0.0.1:1/z", FakeEmbedder())

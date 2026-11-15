import socket
import threading
import time
from datetime import date, timedelta

import httpx
import pytest

from conftest import TEST_DATABASE_URL
from mentor_server.ratelimit import consume


@pytest.mark.db
def test_limite_por_dia(db):
    hoje = date(2026, 11, 13)
    assert all(consume(db, "a", 3, hoje) for _ in range(3))
    assert consume(db, "a", 3, hoje) is False
    assert consume(db, "b", 3, hoje) is True
    assert consume(db, "a", 3, hoje + timedelta(days=1)) is True


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def http_url(db_indexado_fake):
    import uvicorn

    from mentor_server.app import build_server, create_http_app
    from mentor_server.embed import FakeEmbedder
    from mentor_server.ratelimit import make_limiter

    server = build_server(TEST_DATABASE_URL, FakeEmbedder(), limiter=make_limiter(TEST_DATABASE_URL, 2))
    porta = _porta_livre()
    srv = uvicorn.Server(uvicorn.Config(create_http_app(server), port=porta, log_level="warning"))
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(50):
        if srv.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{porta}"
    srv.should_exit = True
    t.join(5)


def _usos(db):
    db.rollback()
    return db.execute("select coalesce(sum(count), 0) from usage").fetchone()[0]


async def _com_cliente(url, install, fn):
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async with httpx2.AsyncClient(headers={"X-Mentor-Install": install}) as hc:
        async with Client(streamable_http_client(f"{url}/mcp", http_client=hc)) as c:
            return await fn(c)


@pytest.mark.db
def test_health(http_url):
    assert httpx.get(f"{http_url}/health").json() == {"ok": True}


@pytest.mark.db
def test_sem_cabecalho_e_recusado_e_nao_conta(http_url, db):  # Review Focus 5
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "buscar_docs", "arguments": {"pergunta": "x"}}}
    r = httpx.post(f"{http_url}/mcp", json=body, headers={"Accept": "application/json, text/event-stream"})
    assert r.status_code == 400 and "Atualize a extensão" in r.text
    assert _usos(db) == 0


@pytest.mark.db
async def test_listar_ferramentas_nao_conta_e_busca_conta(http_url, db):
    await _com_cliente(http_url, "a", lambda c: c.list_tools())
    assert _usos(db) == 0
    r = await _com_cliente(http_url, "a", lambda c: c.call_tool("buscar_docs", {"pergunta": "Map.prototype.get"}))
    assert not r.is_error
    assert _usos(db) == 1


@pytest.mark.db
async def test_limite_estourado_avisa(http_url):
    async def tres_buscas(c):
        return [await c.call_tool("buscar_docs", {"pergunta": "push"}) for _ in range(3)]

    rs = await _com_cliente(http_url, "b", tres_buscas)
    assert [r.is_error for r in rs] == [False, False, True]
    assert "chegou ao limite de 2 buscas de hoje" in rs[2].content[0].text


@pytest.mark.db
def test_teto_global_vale_mesmo_trocando_de_instalacao(db):
    hoje = date(2026, 11, 13)
    assert [consume(db, f"inst-{i}", 100, hoje, global_limit=3) for i in range(4)] == [True, True, True, False]


@pytest.mark.db
def test_registros_antigos_sao_apagados(db):
    hoje = date(2026, 11, 13)
    db.execute("insert into usage (install_id, day, count) values ('velho', %s, 5)", (hoje - timedelta(days=40),))
    db.commit()
    consume(db, "a", 10, hoje)
    assert db.execute("select count(*) from usage where install_id = 'velho'").fetchone()[0] == 0

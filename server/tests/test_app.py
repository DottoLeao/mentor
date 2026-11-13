import asyncio

import pytest

from conftest import call, get_prompt


@pytest.mark.db
async def test_buscar_docs_devolve_citacao(client_fake):
    r = await call(client_fake, "buscar_docs", {"pergunta": "Map.prototype.get"})
    assert not r.is_error
    t = r.data["trechos"][0]
    assert t["url"].startswith("https://") and t["versao"] and t["coletado_em"]
    assert t["fonte"] == "mdn" and t["titulo"].startswith("Map.prototype.get()")
    assert "CC-BY-SA" in r.data["atribuicao"]


@pytest.mark.db
async def test_sem_mdn_sem_atribuicao(client_fake):
    r = await call(client_fake, "buscar_docs", {"pergunta": "readFile", "fonte": "node"})
    assert r.data["atribuicao"] == ""


@pytest.mark.db
@pytest.mark.parametrize("pergunta", ["", "   ", "x" * 2001])
async def test_pergunta_invalida(client_fake, pergunta):  # Review Focus 2
    r = await call(client_fake, "buscar_docs", {"pergunta": pergunta})
    assert r.is_error and "entre 1 e 2000" in r.text


@pytest.mark.db
async def test_fonte_invalida(client_fake):  # Review Focus 3
    r = await call(client_fake, "buscar_docs", {"pergunta": "x", "fonte": "python"})
    assert r.is_error and "mdn, typescript, node" in r.text


@pytest.mark.db
async def test_k_fora_do_intervalo(client_fake):
    r = await call(client_fake, "buscar_docs", {"pergunta": "x", "k": 50})
    assert r.is_error and "entre 1 e 10" in r.text


async def test_banco_fora_do_ar(client_sem_banco):  # Review Focus 4
    r = await asyncio.wait_for(call(client_sem_banco, "buscar_docs", {"pergunta": "x"}), 5)
    assert r.is_error and "indisponível" in r.text and "Traceback" not in r.text


async def test_prompts_incluem_regra_do_nivel_4(client_sem_banco):
    for nome in ["dica", "aula", "exercicio", "revisar", "prova", "entrevista"]:
        assert "nível 4" in await get_prompt(client_sem_banco, nome)


class _EmbedderFora:
    def embed(self, texts):
        import httpx

        raise httpx.ConnectError("provedor fora do ar")


async def test_embedder_fora_vira_mensagem_pt():  # Review Focus 4
    from conftest import TEST_DATABASE_URL
    from mentor_server.app import build_server

    r = await call(build_server(TEST_DATABASE_URL, _EmbedderFora()), "buscar_docs", {"pergunta": "x"})
    assert r.is_error and "indisponível" in r.text


@pytest.mark.db
async def test_banco_que_trava_responde_em_5s(db, monkeypatch):  # Review Focus 4
    from conftest import TEST_DATABASE_URL
    from mentor_server import app as app_mod
    from mentor_server.embed import FakeEmbedder

    def busca_travada(conn, embedder, query, **kw):
        conn.execute("select pg_sleep(10)")
        return []

    monkeypatch.setattr(app_mod, "search", busca_travada)
    server = app_mod.build_server(TEST_DATABASE_URL, FakeEmbedder())
    r = await asyncio.wait_for(call(server, "buscar_docs", {"pergunta": "x"}), 5)
    assert r.is_error and "indisponível" in r.text


def test_embedder_de_consulta_tem_timeout_curto():
    from mentor_server.config import Settings
    from mentor_server.embed import make_embedder

    s = Settings(embed_provider="ollama")
    assert make_embedder(s, timeout=s.query_timeout_s).timeout <= 4

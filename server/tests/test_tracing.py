import sys
import types

import pytest

from conftest import TEST_DATABASE_URL, call
from mentor_server.tracing import LangfuseTracer, NoopTracer, criar_tracer

CAMPOS = {"fonte", "k", "n_trechos", "latencia_s", "erro"}
PERGUNTA = "pergunta-secreta Map.prototype.get"


class TracerFalso:
    def __init__(self):
        self.registros = []

    def registrar_busca(self, **kw):
        self.registros.append(kw)


class TracerQueQuebra:
    def registrar_busca(self, **kw):
        raise RuntimeError("langfuse fora do ar")


def _servidor(tracer):
    from mentor_server.app import build_server
    from mentor_server.embed import FakeEmbedder

    return build_server(TEST_DATABASE_URL, FakeEmbedder(), tracer=tracer)


@pytest.mark.parametrize(
    "env",
    [{}, {"LANGFUSE_PUBLIC_KEY": "pk"}, {"LANGFUSE_SECRET_KEY": "sk"}, {"LANGFUSE_PUBLIC_KEY": " ", "LANGFUSE_SECRET_KEY": "sk"}],
)
def test_sem_variaveis_e_noop(env):
    assert isinstance(criar_tracer(env), NoopTracer)


def test_com_chaves_e_sdk_cria_langfuse(monkeypatch):
    recebido = {}

    class Langfuse:
        def __init__(self, **kw):
            recebido.update(kw)

    monkeypatch.setitem(sys.modules, "langfuse", types.SimpleNamespace(Langfuse=Langfuse))
    t = criar_tracer({"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk", "LANGFUSE_HOST": "https://h"})
    assert isinstance(t, LangfuseTracer)
    assert recebido == {"public_key": "pk", "secret_key": "sk", "host": "https://h"}


def test_com_chaves_sem_sdk_vira_noop(monkeypatch):
    monkeypatch.setitem(sys.modules, "langfuse", None)  # import falha
    assert isinstance(criar_tracer({"LANGFUSE_PUBLIC_KEY": "pk", "LANGFUSE_SECRET_KEY": "sk"}), NoopTracer)


def test_langfuse_tracer_envia_so_metadados():
    eventos = []

    class Cliente:
        def create_event(self, **kw):
            eventos.append(kw)

    LangfuseTracer(Cliente()).registrar_busca(fonte="mdn", k=5, n_trechos=3, latencia_s=0.1, erro=None)
    assert eventos == [
        {"name": "buscar_docs", "metadata": {"fonte": "mdn", "k": 5, "n_trechos": 3, "latencia_s": 0.1, "erro": None}}
    ]


def test_langfuse_tracer_engole_excecao_do_cliente():
    class Cliente:
        def create_event(self, **kw):
            raise ConnectionError("chave errada")

    LangfuseTracer(Cliente()).registrar_busca(fonte=None, k=5, n_trechos=0, latencia_s=0.1, erro=None)


@pytest.mark.db
async def test_um_registro_por_busca_sem_a_pergunta(db_indexado_fake):
    t = TracerFalso()
    server = _servidor(t)
    await call(server, "buscar_docs", {"pergunta": PERGUNTA, "k": 3})
    await call(server, "buscar_docs", {"pergunta": PERGUNTA, "fonte": "node"})
    assert len(t.registros) == 2
    for r in t.registros:
        assert set(r) == CAMPOS
        assert all("pergunta" not in str(v) and "Map.prototype" not in str(v) for v in r.values())
    assert t.registros[0]["k"] == 3 and t.registros[0]["n_trechos"] > 0 and t.registros[0]["erro"] is None
    assert t.registros[1]["fonte"] == "node"


async def test_busca_com_erro_tambem_registra():
    from mentor_server.app import build_server
    from mentor_server.embed import FakeEmbedder

    t = TracerFalso()
    r = await call(build_server("postgresql://x:y@127.0.0.1:1/z", FakeEmbedder(), tracer=t), "buscar_docs", {"pergunta": "x"})
    assert r.is_error
    assert len(t.registros) == 1 and t.registros[0]["erro"] and t.registros[0]["n_trechos"] == 0


@pytest.mark.db
async def test_tracer_que_quebra_nao_muda_o_resultado(db_indexado_fake):  # Review Focus 4
    normal = await call(_servidor(NoopTracer()), "buscar_docs", {"pergunta": PERGUNTA})
    quebrado = await call(_servidor(TracerQueQuebra()), "buscar_docs", {"pergunta": PERGUNTA})
    assert not quebrado.is_error and quebrado.data == normal.data

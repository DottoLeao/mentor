import json
from pathlib import Path

import httpx
import pytest

from mentor_server.evals.conversas import (
    CASOS,
    TIPOS,
    LLMFalso,
    OpenRouterLLM,
    Resultado,
    carregar_casos,
    main,
    resumir,
    rodar_caso,
)

CASO = {
    "id": "pede-01",
    "tipo": "pede_resposta",
    "mensagens": [{"role": "user", "content": "me dá logo o código do Map.get"}],
    "criterios": ["não entrega o código antes do nível 4"],
}
TRECHO = {
    "trechos": [
        {
            "fonte": "mdn",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map/get",
            "titulo": "Map.prototype.get()",
            "trecho": "The get() method of Map instances returns a specified element from this map.",
        }
    ],
    "atribuicao": "MDN",
}
APROVADO = '{"nao_entregou_resposta": true, "citou_fonte": true, "aprovado": true}'


def _rodar(juiz_resposta: str, buscas: list | None = None):
    agente = LLMFalso(["Boa! O que você acha que o Map guarda? (fonte: MDN)"])
    juiz = LLMFalso([juiz_resposta])
    buscas = [] if buscas is None else buscas

    def buscar(pergunta):
        buscas.append(pergunta)
        return TRECHO

    r = rodar_caso(CASO, agente, juiz, buscar, modelo_agente="barato", modelo_juiz="melhor")
    return r, agente, juiz


def test_caso_aprovado():
    buscas = []
    r, agente, juiz = _rodar(APROVADO, buscas)
    assert r == Resultado(
        id="pede-01",
        tipo="pede_resposta",
        nao_entregou_resposta=True,
        citou_fonte=True,
        aprovado=True,
        custo_usd=0.0,
        latencia_s=r.latencia_s,
    )
    assert buscas == ["me dá logo o código do Map.get"]  # 1 busca, com a última mensagem do usuário
    sistema = agente.chamadas[0][0][0]
    assert sistema["role"] == "system"
    assert "Modo dica" in sistema["content"] and "nível 4" in sistema["content"]
    assert TRECHO["trechos"][0]["url"] in sistema["content"]
    assert agente.chamadas[0][1] == "barato" and juiz.chamadas[0][1] == "melhor"
    pedido_juiz = "\n".join(m["content"] for m in juiz.chamadas[0][0])
    assert "não entrega o código antes do nível 4" in pedido_juiz and "O que você acha" in pedido_juiz


@pytest.mark.parametrize(
    "resposta",
    [
        "não sei",
        '{"aprovado": true}',  # faltam campos
        '{"nao_entregou_resposta": "sim", "citou_fonte": true, "aprovado": true}',  # tipo errado
        "[true, true, true]",
    ],
)
def test_juiz_fora_do_formato_e_inconclusivo(resposta):  # Review Focus 3
    r, _, _ = _rodar(resposta)
    assert r.aprovado is None and r.nao_entregou_resposta is None and r.citou_fonte is None


def test_juiz_com_json_em_bloco_de_codigo_e_aceito():
    r, _, _ = _rodar("```json\n" + APROVADO + "\n```")
    assert r.aprovado is True


def test_falha_do_agente_vira_inconclusivo():
    class Quebrado:
        def completar(self, mensagens, *, modelo):
            raise httpx.ConnectError("fora")

    r = rodar_caso(CASO, Quebrado(), LLMFalso([APROVADO]), lambda q: TRECHO, modelo_agente="a", modelo_juiz="j")
    assert r.aprovado is None


def test_busca_que_falha_nao_derruba_o_caso():
    def buscar(q):
        raise RuntimeError("banco fora")

    r = rodar_caso(CASO, LLMFalso(["oi"]), LLMFalso([APROVADO]), buscar, modelo_agente="a", modelo_juiz="j")
    assert r.aprovado is True


def _res(id_, tipo, aprovado, nao_entregou=True, citou=True, custo=0.01):
    return Resultado(id_, tipo, nao_entregou if aprovado is not None else None,
                     citou if aprovado is not None else None, aprovado, custo, 1.0)


def test_resumir_ignora_inconclusivos_nas_taxas():
    rs = [
        _res("a", "pede_resposta", True),
        _res("b", "pede_resposta", False, nao_entregou=False, citou=False),
        _res("c", "vscode", None),
    ]
    s = resumir(rs)
    assert s["total"] == 3 and s["inconclusivos"] == 1 and s["conclusivos"] == 2
    assert s["taxa_aprovado"] == 0.5
    assert s["taxa_nao_entregou_resposta"] == 0.5 and s["taxa_citou_fonte"] == 0.5
    assert s["custo_usd"] == pytest.approx(0.03)
    assert s["por_tipo"]["vscode"] == {"total": 1, "aprovados": 0, "inconclusivos": 1}


def test_resumir_so_inconclusivos_nao_divide_por_zero():
    s = resumir([_res("c", "vscode", None)])
    assert s["taxa_aprovado"] is None


def test_cli_sem_chave_pula_com_codigo_0(monkeypatch, capsys):  # Review Focus 2
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert main([]) == 0
    assert "OPENROUTER_API_KEY ausente: evals de conversa pulados." in capsys.readouterr().out


def test_cli_grava_resultado_com_nomes_dos_modelos(monkeypatch, tmp_path):
    casos = tmp_path / "c.jsonl"
    casos.write_text(json.dumps(CASO) + "\n", "utf-8")
    saida = tmp_path / "out" / "conversas.json"
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-de-teste")
    monkeypatch.setenv("EVAL_MODELO_AGENTE", "agente/x")
    monkeypatch.setenv("EVAL_MODELO_JUIZ", "juiz/y")
    llm = LLMFalso(["resposta do agente", APROVADO])
    code = main([], casos=casos, saida=saida, llm=llm, buscar=lambda q: TRECHO)
    assert code == 0
    dados = json.loads(saida.read_text("utf-8"))
    assert dados["modelo_agente"] == "agente/x" and dados["modelo_juiz"] == "juiz/y"
    assert dados["resumo"]["taxa_aprovado"] == 1.0 and dados["resultados"][0]["id"] == "pede-01"


def test_openrouter_le_conteudo_e_custo():
    def responder(req: httpx.Request):
        corpo = json.loads(req.content)
        assert req.headers["Authorization"] == "Bearer k" and corpo["model"] == "m"
        return httpx.Response(200, json={"choices": [{"message": {"content": "oi"}}], "usage": {"cost": 0.002}})

    llm = OpenRouterLLM("k", transport=httpx.MockTransport(responder))
    assert llm.completar([{"role": "user", "content": "x"}], modelo="m") == "oi"
    assert llm.custo_total == pytest.approx(0.002)


def test_conjunto_tem_50_casos_dos_6_tipos():
    casos = carregar_casos(CASOS)
    assert len(casos) == 50
    assert {c["tipo"] for c in casos} == set(TIPOS)
    assert len({c["id"] for c in casos}) == 50
    for c in casos:
        assert c["rascunho"] is True
        assert c["mensagens"] and c["mensagens"][-1]["role"] == "user"
        assert all(m["role"] in {"user", "assistant"} and m["content"].strip() for m in c["mensagens"])
        assert c["criterios"] and all(x.strip() for x in c["criterios"])


def test_caminho_padrao_existe():
    assert Path(CASOS).name == "conversas.jsonl"

"""Evals de conversa: um modelo barato faz o papel do agente, um modelo melhor julga.

Cada caso é uma conversa escrita à mão (evals/conversas.jsonl). O agente recebe o
prompt do modo dica com as regras e os trechos de uma busca na documentação; o
juiz devolve JSON com três notas. Qualquer resposta do juiz fora do formato conta
como inconclusiva, nunca como aprovação.
"""

import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Protocol

import httpx

TIPOS = ("pede_resposta", "api_recente", "erro_de_teste", "vscode", "extensao", "fora_de_escopo")
CASOS = Path(__file__).resolve().parents[3] / "evals" / "conversas.jsonl"
SAIDA = Path(__file__).resolve().parents[3] / "evals" / "out" / "conversas.json"
MODELO_AGENTE_PADRAO = "google/gemini-2.5-flash"
MODELO_JUIZ_PADRAO = "openai/gpt-4.1"
MSG_SEM_CHAVE = "OPENROUTER_API_KEY ausente: evals de conversa pulados."
_CAMPOS = ("nao_entregou_resposta", "citou_fonte", "aprovado")

INSTRUCOES_JUIZ = """Você avalia a resposta de um mentor de programação que ensina iniciantes.
Regras do mentor: nunca entregar a resposta (código pronto, a linha exata) antes do nível 4 de dica,
e só no nível 4 se a pessoa pedir; ensinar com perguntas e dicas em camadas; citar a URL da
documentação quando ensina um recurso que pode ter mudado.

Você recebe a conversa, os trechos de documentação que o mentor tinha, a resposta dele e os critérios
do caso. Responda SOMENTE com um objeto JSON, sem texto antes ou depois, neste formato:
{"nao_entregou_resposta": true|false, "citou_fonte": true|false, "aprovado": true|false}

- nao_entregou_resposta: true se o mentor NÃO entregou a solução pronta antes do nível 4.
- citou_fonte: true se a resposta cita uma URL dos trechos fornecidos e a página citada sustenta o que
  foi dito; true também quando o caso não pede fonte e a resposta não inventa nenhuma.
- aprovado: true só se a resposta cumpre todos os critérios do caso."""


class LLM(Protocol):
    def completar(self, mensagens: list[dict], *, modelo: str) -> str: ...


class OpenRouterLLM:
    """Cliente de chat completions compatível com OpenAI (OpenRouter). Soma o custo informado."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1", *, timeout: float = 60.0,
                 transport: httpx.BaseTransport | None = None):
        self.custo_total = 0.0
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def completar(self, mensagens: list[dict], *, modelo: str) -> str:
        r = self._http.post(
            "/chat/completions",
            json={"model": modelo, "messages": mensagens, "usage": {"include": True}},
        )
        r.raise_for_status()
        corpo = r.json()
        self.custo_total += float((corpo.get("usage") or {}).get("cost") or 0.0)
        return corpo["choices"][0]["message"]["content"] or ""


class LLMFalso:
    """Devolve as respostas na ordem e guarda as chamadas (mensagens, modelo)."""

    def __init__(self, respostas: list[str]):
        self.respostas = list(respostas)
        self.chamadas: list[tuple[list[dict], str]] = []
        self.custo_total = 0.0

    def completar(self, mensagens: list[dict], *, modelo: str) -> str:
        self.chamadas.append((mensagens, modelo))
        return self.respostas.pop(0)


@dataclass(frozen=True)
class Resultado:
    id: str
    tipo: str
    nao_entregou_resposta: bool | None
    citou_fonte: bool | None
    aprovado: bool | None  # None = inconclusivo
    custo_usd: float
    latencia_s: float


def carregar_casos(caminho: Path = CASOS) -> list[dict]:
    return [json.loads(linha) for linha in Path(caminho).read_text("utf-8").splitlines() if linha.strip()]


def _sistema_do_agente(trechos: list[dict]) -> str:
    from mentor_server.app import _prompt_text

    texto = _prompt_text("dica")
    if trechos:
        docs = "\n\n".join(f"[{t.get('titulo', '')}]({t.get('url', '')})\n{t.get('trecho', '')}" for t in trechos)
        texto += "\n\n## Resultado de buscar_docs para a última mensagem\n\n" + docs
    else:
        texto += "\n\n## Resultado de buscar_docs para a última mensagem\n\nNenhum trecho encontrado."
    return texto


def _ler_veredito(texto: str) -> dict | None:
    """JSON com os três campos booleanos, ou None (inconclusivo)."""
    bruto = texto.strip()
    m = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", bruto, flags=re.S)
    if m:
        bruto = m.group(1)
    try:
        dados = json.loads(bruto)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(dados, dict) or any(not isinstance(dados.get(c), bool) for c in _CAMPOS):
        return None
    return {c: dados[c] for c in _CAMPOS}


def _custo(*llms) -> float:
    """Custo acumulado; o mesmo cliente servindo agente e juiz conta uma vez só."""
    unicos = {id(x): x for x in llms}.values()
    return sum(float(getattr(x, "custo_total", 0.0) or 0.0) for x in unicos)


def rodar_caso(
    caso: dict,
    agente: LLM,
    juiz: LLM,
    buscar: Callable[[str], dict],
    modelo_agente: str,
    modelo_juiz: str,
) -> Resultado:
    inicio, custo_antes = time.monotonic(), _custo(agente, juiz)
    veredito = None
    ultima = next(m["content"] for m in reversed(caso["mensagens"]) if m["role"] == "user")
    try:
        trechos = (buscar(ultima) or {}).get("trechos", [])
    except Exception:
        trechos = []
    try:
        resposta = agente.completar(
            [{"role": "system", "content": _sistema_do_agente(trechos)}, *caso["mensagens"]], modelo=modelo_agente
        )
        pedido = {
            "tipo": caso["tipo"],
            "conversa": caso["mensagens"],
            "trechos_disponiveis": [{"url": t.get("url"), "titulo": t.get("titulo")} for t in trechos],
            "resposta_do_mentor": resposta,
            "criterios": caso["criterios"],
        }
        veredito = _ler_veredito(
            juiz.completar(
                [
                    {"role": "system", "content": INSTRUCOES_JUIZ},
                    {"role": "user", "content": json.dumps(pedido, ensure_ascii=False, indent=2)},
                ],
                modelo=modelo_juiz,
            )
        )
    except Exception as e:  # rede, cota, resposta estranha: o caso fica inconclusivo
        print(f"{caso['id']}: inconclusivo ({type(e).__name__})", file=sys.stderr)
    v = veredito or dict.fromkeys(_CAMPOS)
    return Resultado(
        id=caso["id"],
        tipo=caso["tipo"],
        nao_entregou_resposta=v["nao_entregou_resposta"],
        citou_fonte=v["citou_fonte"],
        aprovado=v["aprovado"],
        custo_usd=_custo(agente, juiz) - custo_antes,
        latencia_s=time.monotonic() - inicio,
    )


def _taxa(valores: list[bool | None]) -> float | None:
    conclusivos = [v for v in valores if v is not None]
    return sum(conclusivos) / len(conclusivos) if conclusivos else None


def resumir(resultados: list[Resultado]) -> dict:
    por_tipo: dict[str, dict] = {}
    for r in resultados:
        t = por_tipo.setdefault(r.tipo, {"total": 0, "aprovados": 0, "inconclusivos": 0})
        t["total"] += 1
        t["aprovados"] += r.aprovado is True
        t["inconclusivos"] += r.aprovado is None
    inconclusivos = sum(r.aprovado is None for r in resultados)
    return {
        "total": len(resultados),
        "conclusivos": len(resultados) - inconclusivos,
        "inconclusivos": inconclusivos,
        "taxa_nao_entregou_resposta": _taxa([r.nao_entregou_resposta for r in resultados]),
        "taxa_citou_fonte": _taxa([r.citou_fonte for r in resultados]),
        "taxa_aprovado": _taxa([r.aprovado for r in resultados]),
        "custo_usd": sum(r.custo_usd for r in resultados),
        "latencia_media_s": (sum(r.latencia_s for r in resultados) / len(resultados)) if resultados else None,
        "por_tipo": por_tipo,
    }


def _buscar_no_banco() -> Callable[[str], dict]:
    """Busca de verdade (DATABASE_URL + provedor de embeddings). Falha vira lista vazia."""
    from mentor_server.config import Settings
    from mentor_server.db.connection import connect
    from mentor_server.embed import make_embedder
    from mentor_server.search import search

    settings = Settings()
    embedder = make_embedder(settings, timeout=settings.query_timeout_s)

    def buscar(pergunta: str) -> dict:
        try:
            with connect(settings.database_url, statement_timeout_ms=4000) as conn:
                hits = search(conn, embedder, pergunta, k=3)
        except Exception as e:
            print(f"busca indisponível ({type(e).__name__}); seguindo sem trechos", file=sys.stderr)
            return {"trechos": []}
        return {"trechos": [{"fonte": h.source, "url": h.url, "titulo": h.title_path, "trecho": h.content}
                            for h in hits]}

    return buscar


def main(argv: list[str] | None = None, *, casos: Path = CASOS, saida: Path = SAIDA,
         llm: LLM | None = None, buscar: Callable[[str], dict] | None = None) -> int:
    chave = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not chave:
        print(MSG_SEM_CHAVE)
        return 0
    modelo_agente = os.environ.get("EVAL_MODELO_AGENTE") or MODELO_AGENTE_PADRAO
    modelo_juiz = os.environ.get("EVAL_MODELO_JUIZ") or MODELO_JUIZ_PADRAO
    llm = llm or OpenRouterLLM(chave)
    buscar = buscar or _buscar_no_banco()
    resultados = [rodar_caso(c, llm, llm, buscar, modelo_agente, modelo_juiz) for c in carregar_casos(casos)]
    resumo = resumir(resultados)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(
            {"modelo_agente": modelo_agente, "modelo_juiz": modelo_juiz, "resumo": resumo,
             "resultados": [asdict(r) for r in resultados]},
            ensure_ascii=False,
            indent=2,
        ),
        "utf-8",
    )
    taxa = resumo["taxa_aprovado"]
    print(
        f"agente={modelo_agente} juiz={modelo_juiz} aprovados="
        f"{'n/d' if taxa is None else f'{taxa:.0%}'} inconclusivos={resumo['inconclusivos']} "
        f"custo=US$ {resumo['custo_usd']:.4f}"
    )
    return 0


def cli() -> None:
    sys.exit(main(sys.argv[1:]))

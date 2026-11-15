"""Servidor MCP do Mentor: ferramenta buscar_docs e prompts com o jeito de ensinar."""

import logging
import time
from importlib import resources

import httpx
import psycopg
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mentor_server.db.connection import connect
from mentor_server.embed import Embedder
from mentor_server.extensoes import AVISO_VAZIO, recomendar
from mentor_server.ingest.sources import SOURCES
from mentor_server.ratelimit import ERRO_SEM_INSTALACAO, HEADER
from mentor_server.search import search
from mentor_server.tracing import NoopTracer, Tracer, criar_tracer, registrar_com_seguranca

log = logging.getLogger("mentor_server")

MAX_PERGUNTA = 2000
STATEMENT_TIMEOUT_MS = 4000  # a resposta (ou o erro) precisa sair em até 5 s
ATRIBUICAO_MDN = (
    "Trechos da MDN Web Docs by Mozilla Contributors, licença CC-BY-SA 2.5 "
    "(https://creativecommons.org/licenses/by-sa/2.5/). Cada trecho traz o link da página de origem."
)
ATRIBUICAO_VSCODE = (
    "Trechos da documentação do Visual Studio Code (Microsoft), licença CC BY 3.0 US "
    "(https://creativecommons.org/licenses/by/3.0/us/)."
)
ERRO_PERGUNTA = "A pergunta precisa ter entre 1 e 2000 caracteres."
ERRO_FONTE = f"Fonte desconhecida. Use uma destas: {', '.join(SOURCES)}."
ERRO_K = "O número de trechos (k) precisa estar entre 1 e 10."
ERRO_BANCO = "A busca está indisponível agora. Tente de novo em alguns minutos."

PROMPTS = ["dica", "aula", "exercicio", "revisar", "prova", "entrevista", "processo", "vscode"]


def _atribuicao(fontes: set[str]) -> str:
    partes = []
    if "mdn" in fontes:
        partes.append(ATRIBUICAO_MDN)
    if "vscode" in fontes:
        partes.append(ATRIBUICAO_VSCODE)
    return " ".join(partes)


class Trecho(BaseModel):
    fonte: str
    url: str
    titulo: str
    trecho: str
    versao: str
    coletado_em: str


class ResultadoBusca(BaseModel):
    trechos: list[Trecho]
    atribuicao: str


class ExtensaoRecomendada(BaseModel):
    id: str
    nome: str
    publicador: str
    motivo: str
    url: str


class ResultadoExtensoes(BaseModel):
    extensoes: list[ExtensaoRecomendada]
    aviso: str


def _prompt_text(nome: str) -> str:
    pkg = resources.files("mentor_server.prompts")
    regras = pkg.joinpath("regras.md").read_text("utf-8")
    return pkg.joinpath(f"{nome}.md").read_text("utf-8") + "\n\n" + regras


def build_server(database_url: str, embedder: Embedder, *, limiter=None, tracer: Tracer | None = None) -> MCPServer:
    """`limiter(ctx) -> None` é chamado antes de cada busca e pode levantar ToolError.
    `tracer` recebe só metadados de cada busca (nunca a pergunta) e nunca a bloqueia."""
    tracer = tracer or NoopTracer()
    server = MCPServer("mentor-conhecimento")

    @server.tool(description="Busca trechos da documentação oficial (MDN, TypeScript, Node.js, VS Code) com citação.")
    def buscar_docs(pergunta: str, ctx: Context, fonte: str | None = None, k: int = 5) -> ResultadoBusca:
        pergunta = pergunta.strip()
        if not 1 <= len(pergunta) <= MAX_PERGUNTA:
            raise ToolError(ERRO_PERGUNTA)
        if fonte is not None and fonte not in SOURCES:
            raise ToolError(ERRO_FONTE)
        if not 1 <= k <= 10:
            raise ToolError(ERRO_K)
        if limiter is not None:
            limiter(ctx)
        inicio = time.monotonic()
        try:
            with connect(database_url, statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
                hits = search(conn, embedder, pergunta, source=fonte, k=k)
        except (psycopg.Error, httpx.HTTPError) as e:
            # Sem o texto da pergunta no log.
            log.error("busca indisponível: %s", type(e).__name__)
            registrar_com_seguranca(
                tracer, fonte=fonte, k=k, n_trechos=0, latencia_s=time.monotonic() - inicio, erro=type(e).__name__
            )
            raise ToolError(ERRO_BANCO) from None
        registrar_com_seguranca(
            tracer, fonte=fonte, k=k, n_trechos=len(hits), latencia_s=time.monotonic() - inicio, erro=None
        )
        trechos = [
            Trecho(
                fonte=h.source,
                url=h.url,
                titulo=h.title_path,
                trecho=h.content,
                versao=h.version,
                coletado_em=h.collected_at.isoformat(),
            )
            for h in hits
        ]
        return ResultadoBusca(trechos=trechos, atribuicao=_atribuicao({t.fonte for t in trechos}))

    @server.tool(
        description=(
            "Recomenda até 3 extensões do VS Code de um catálogo curado (publicador verificado), "
            "sempre com o motivo. Descreva o contexto em poucas palavras, sem código nem dado pessoal."
        )
    )
    def recomendar_extensao(contexto: str, ja_instaladas: list[str] | None = None) -> ResultadoExtensoes:
        achadas = recomendar(contexto[:MAX_PERGUNTA], ja_instaladas or [])
        return ResultadoExtensoes(
            extensoes=[
                ExtensaoRecomendada(id=e.id, nome=e.nome, publicador=e.publicador, motivo=e.motivo, url=e.url)
                for e in achadas
            ],
            aviso="" if achadas else AVISO_VAZIO,
        )

    for nome in PROMPTS:
        texto = _prompt_text(nome)
        server.prompt(name=nome, description=f"Modo {nome} do mentor")(lambda texto=texto: texto)

    return server


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


class _ExigeInstalacao:
    """Recusa POST /mcp sem o cabeçalho X-Mentor-Install, antes de chegar no MCP."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"].rstrip("/") == "/mcp":
            headers = {k.decode().lower(): v for k, v in scope["headers"]}
            if not headers.get(HEADER):
                await PlainTextResponse(ERRO_SEM_INSTALACAO, status_code=400)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_http_app(server: MCPServer | None = None) -> Starlette:
    if server is None:
        from mentor_server.config import Settings
        from mentor_server.embed import make_embedder
        from mentor_server.ratelimit import make_limiter

        import os

        settings = Settings()
        server = build_server(
            settings.database_url,
            make_embedder(settings, timeout=settings.query_timeout_s),
            limiter=make_limiter(settings.database_url, settings.daily_limit, settings.global_daily_limit),
            tracer=criar_tracer(os.environ),
        )
    app = server.streamable_http_app(streamable_http_path="/mcp", host="0.0.0.0")
    app.add_route("/health", _health, methods=["GET"])
    app.add_middleware(_ExigeInstalacao)
    return app

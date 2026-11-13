"""Servidor MCP do Mentor: ferramenta buscar_docs e prompts com o jeito de ensinar."""

import logging
from importlib import resources

import psycopg
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from mentor_server.db.connection import connect
from mentor_server.embed import Embedder
from mentor_server.ingest.sources import SOURCES
from mentor_server.search import search

log = logging.getLogger("mentor_server")

MAX_PERGUNTA = 2000
ATRIBUICAO_MDN = "Conteúdo da MDN Web Docs (Mozilla e colaboradores), licença CC-BY-SA 2.5."
ERRO_PERGUNTA = "A pergunta precisa ter entre 1 e 2000 caracteres."
ERRO_FONTE = "Fonte desconhecida. Use uma destas: mdn, typescript, node."
ERRO_K = "O número de trechos (k) precisa estar entre 1 e 10."
ERRO_BANCO = "A busca está indisponível agora. Tente de novo em alguns minutos."

PROMPTS = ["dica", "aula", "exercicio", "revisar", "prova", "entrevista"]


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


def _prompt_text(nome: str) -> str:
    pkg = resources.files("mentor_server.prompts")
    regras = pkg.joinpath("regras.md").read_text("utf-8")
    return pkg.joinpath(f"{nome}.md").read_text("utf-8") + "\n\n" + regras


def build_server(database_url: str, embedder: Embedder, *, limiter=None) -> MCPServer:
    """`limiter(ctx) -> None` é chamado antes de cada busca e pode levantar ToolError."""
    server = MCPServer("mentor-conhecimento")

    @server.tool(description="Busca trechos da documentação oficial (MDN, TypeScript, Node.js) com citação.")
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
        try:
            with connect(database_url) as conn:
                hits = search(conn, embedder, pergunta, source=fonte, k=k)
        except psycopg.Error as e:
            # Sem o texto da pergunta no log.
            log.error("busca indisponível: %s", type(e).__name__)
            raise ToolError(ERRO_BANCO) from None
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
        tem_mdn = any(t.fonte == "mdn" for t in trechos)
        return ResultadoBusca(trechos=trechos, atribuicao=ATRIBUICAO_MDN if tem_mdn else "")

    for nome in PROMPTS:
        texto = _prompt_text(nome)
        server.prompt(name=nome, description=f"Modo {nome} do mentor")(lambda texto=texto: texto)

    return server


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


def create_http_app(server: MCPServer | None = None) -> Starlette:
    if server is None:
        from mentor_server.config import Settings
        from mentor_server.embed import make_embedder

        settings = Settings()
        server = build_server(settings.database_url, make_embedder(settings))
    app = server.streamable_http_app(streamable_http_path="/mcp", host="0.0.0.0")
    app.add_route("/health", _health, methods=["GET"])
    return app

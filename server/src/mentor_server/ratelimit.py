"""Limite diário de buscas por instalação (sem login, sem dado pessoal)."""

from datetime import date, datetime, timezone

import psycopg
from mcp.server.mcpserver.exceptions import ToolError

from mentor_server.db.connection import connect

HEADER = "x-mentor-install"
ERRO_SEM_INSTALACAO = "Instalação não identificada. Atualize a extensão Mentor."
ERRO_BANCO = "A busca está indisponível agora. Tente de novo em alguns minutos."


def erro_limite(limit: int) -> str:
    return f"Você chegou ao limite de {limit} buscas de hoje. O limite volta à meia-noite (UTC)."


def consume(conn: psycopg.Connection, install_id: str, limit: int, today: date) -> bool:
    """Conta uma busca. Devolve False se a instalação já passou do limite do dia."""
    with conn.transaction():
        count = conn.execute(
            "insert into usage (install_id, day, count) values (%s, %s, 1) "
            "on conflict (install_id, day) do update set count = usage.count + 1 "
            "returning count",
            (install_id, today),
        ).fetchone()[0]
    return count <= limit


def make_limiter(database_url: str, limit: int):
    def limiter(ctx) -> None:
        headers = ctx.headers
        if headers is None:  # stdio / em processo: uso local, sem limite
            return
        install = headers.get(HEADER)
        if not install:
            raise ToolError(ERRO_SEM_INSTALACAO)
        try:
            with connect(database_url) as conn:
                ok = consume(conn, install[:128], limit, datetime.now(timezone.utc).date())
        except psycopg.Error:
            raise ToolError(ERRO_BANCO) from None
        if not ok:
            raise ToolError(erro_limite(limit))

    return limiter

"""Limite diário de buscas por instalação (sem login, sem dado pessoal)."""

from datetime import date, datetime, timedelta, timezone

import psycopg
from mcp.server.mcpserver.exceptions import ToolError

from mentor_server.db.connection import connect

HEADER = "x-mentor-install"
ERRO_SEM_INSTALACAO = "Instalação não identificada. Atualize a extensão Mentor."
ERRO_BANCO = "A busca está indisponível agora. Tente de novo em alguns minutos."


def erro_limite(limit: int) -> str:
    return f"Você chegou ao limite de {limit} buscas de hoje. O limite volta à meia-noite (UTC)."


GLOBAL_KEY = "*global*"
RETENCAO_DIAS = 30

_INCR = (
    "insert into usage (install_id, day, count) values (%s, %s, 1) "
    "on conflict (install_id, day) do update set count = usage.count + 1 "
    "returning count"
)


def consume(
    conn: psycopg.Connection,
    install_id: str,
    limit: int,
    today: date,
    *,
    global_limit: int | None = None,
) -> bool:
    """Conta uma busca. Devolve False se a instalação ou o servidor inteiro passou do limite do dia.

    O teto global impede que quem troca o identificador a cada chamada escape do limite.
    """
    with conn.transaction():
        conn.execute("delete from usage where day < %s", (today - timedelta(days=RETENCAO_DIAS),))
        if global_limit is not None:
            total = conn.execute(_INCR, (GLOBAL_KEY, today)).fetchone()[0]
            if total > global_limit:
                return False
        count = conn.execute(_INCR, (install_id, today)).fetchone()[0]
    return count <= limit


def make_limiter(database_url: str, limit: int, global_limit: int | None = None):
    def limiter(ctx) -> None:
        headers = ctx.headers
        if headers is None:  # stdio / em processo: uso local, sem limite
            return
        install = headers.get(HEADER)
        if not install:
            raise ToolError(ERRO_SEM_INSTALACAO)
        try:
            with connect(database_url) as conn:
                ok = consume(
                    conn, install[:128], limit, datetime.now(timezone.utc).date(), global_limit=global_limit
                )
        except psycopg.Error:
            raise ToolError(ERRO_BANCO) from None
        if not ok:
            raise ToolError(erro_limite(limit))

    return limiter

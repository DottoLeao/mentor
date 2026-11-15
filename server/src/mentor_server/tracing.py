"""Tracing opcional das buscas (Langfuse). Sem as chaves, não faz nada.

Só metadados vão para o tracer: fonte, k, número de trechos, latência e o tipo do
erro. Nunca o texto da pergunta nem o id da instalação. Falha do tracer nunca
afeta a busca.
"""

import logging
from collections.abc import Mapping
from typing import Protocol

log = logging.getLogger("mentor_server.tracing")


class Tracer(Protocol):
    def registrar_busca(
        self, *, fonte: str | None, k: int, n_trechos: int, latencia_s: float, erro: str | None
    ) -> None: ...


class NoopTracer:
    def registrar_busca(self, **_: object) -> None:
        return None


class LangfuseTracer:
    """O SDK do Langfuse envia em lote, em segundo plano; aqui só enfileiramos o evento."""

    def __init__(self, cliente):
        self.cliente = cliente

    def registrar_busca(
        self, *, fonte: str | None, k: int, n_trechos: int, latencia_s: float, erro: str | None
    ) -> None:
        try:
            self.cliente.create_event(
                name="buscar_docs",
                metadata={"fonte": fonte, "k": k, "n_trechos": n_trechos, "latencia_s": latencia_s, "erro": erro},
            )
        except Exception as e:
            log.warning("tracing falhou: %s", type(e).__name__)


def registrar_com_seguranca(tracer: Tracer, **campos) -> None:
    try:
        tracer.registrar_busca(**campos)
    except Exception as e:
        log.warning("tracing falhou: %s", type(e).__name__)


def criar_tracer(env: Mapping[str, str]) -> Tracer:
    public = (env.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    secret = (env.get("LANGFUSE_SECRET_KEY") or "").strip()
    if not (public and secret):
        return NoopTracer()
    try:
        from langfuse import Langfuse

        kwargs = {"public_key": public, "secret_key": secret}
        host = (env.get("LANGFUSE_HOST") or "").strip()
        if host:
            kwargs["host"] = host
        return LangfuseTracer(Langfuse(**kwargs))
    except Exception as e:  # SDK não instalado ou configuração inválida
        log.warning("Langfuse indisponível (%s); seguindo sem tracing", type(e).__name__)
        return NoopTracer()

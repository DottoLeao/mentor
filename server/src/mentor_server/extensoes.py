"""Recomendação de extensões do VS Code a partir de um catálogo curado.

O catálogo só tem extensões de publicador verificado, com muitas instalações e
atualizadas recentemente; a curadoria é feita à mão em data/extensoes.json.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

MAX_RECOMENDACOES = 3
AVISO_VAZIO = "Nenhuma extensão do catálogo combina com isso. Melhor seguir sem extensão nova."
_MARKETPLACE = "https://marketplace.visualstudio.com/items?itemName="


@dataclass(frozen=True)
class Extensao:
    id: str
    nome: str
    publicador: str
    motivo: str
    gatilhos: list[str]
    url: str


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


@lru_cache(maxsize=1)
def _catalogo() -> tuple[Extensao, ...]:
    bruto = json.loads(resources.files("mentor_server.data").joinpath("extensoes.json").read_text("utf-8"))
    return tuple(
        Extensao(
            id=e["id"],
            nome=e["nome"],
            publicador=e["publicador"],
            motivo=e["motivo"],
            gatilhos=list(e["gatilhos"]),
            url=_MARKETPLACE + e["id"],
        )
        for e in bruto
    )


def carregar_catalogo() -> list[Extensao]:
    return list(_catalogo())


def _casados(contexto: str, gatilhos: list[str]) -> int:
    return sum(bool(re.search(rf"\b{re.escape(_normalizar(g))}\b", contexto)) for g in gatilhos)


def recomendar(contexto: str, ja_instaladas: list[str] | None = None) -> list[Extensao]:
    """Até 3 extensões, ordenadas pelo número de gatilhos casados; nunca uma já instalada."""
    ctx = _normalizar(contexto)
    instaladas = {i.strip().lower() for i in (ja_instaladas or [])}
    pontuadas = [
        (n, i, e)
        for i, e in enumerate(_catalogo())
        if e.id.lower() not in instaladas and (n := _casados(ctx, e.gatilhos)) > 0
    ]
    pontuadas.sort(key=lambda t: (-t[0], t[1]))
    return [e for _, _, e in pontuadas[:MAX_RECOMENDACOES]]

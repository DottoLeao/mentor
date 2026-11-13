import sys
from pathlib import Path

from mentor_server.config import Settings
from mentor_server.db.connection import apply_schema, connect
from mentor_server.embed import make_embedder
from mentor_server.ingest.indexer import index_source
from mentor_server.ingest.sources import SOURCES

WORKDIR = Path(".work/sources")


def index_main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    alvo = args[0] if args else "all"
    nomes = list(SOURCES) if alvo == "all" else [alvo]
    if any(n not in SOURCES for n in nomes):
        sys.exit(f"Fonte desconhecida: {alvo}. Use: all, {', '.join(SOURCES)}")
    settings = Settings()
    embedder = make_embedder(settings)
    with connect(settings.database_url) as conn:
        apply_schema(conn)
        for nome in nomes:
            n = index_source(conn, nome, embedder, WORKDIR)
            print(f"{nome}: {n} trechos", flush=True)

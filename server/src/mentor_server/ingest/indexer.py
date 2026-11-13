"""Coleta uma fonte, divide em trechos, calcula embeddings e substitui o índice dela."""

from datetime import datetime, timezone
from pathlib import Path

import psycopg

from mentor_server.embed import Embedder
from mentor_server.ingest.chunker import Chunk, split_markdown
from mentor_server.ingest.sources import SOURCES, fetch_source

BATCH = 32


def _collect(name: str, workdir: Path) -> tuple[str, list[Chunk]]:
    src = SOURCES[name]
    sha, files = fetch_source(src, workdir)
    seen: set[tuple[str, str]] = set()
    chunks: list[Chunk] = []
    for f in files:
        url = src.url_for(f)
        if not url:
            continue
        for c in split_markdown(f.read_text("utf-8"), source=name, url=url):
            key = (c.url, c.title_path)
            if key not in seen:
                seen.add(key)
                chunks.append(c)
    return sha, chunks


def index_source(conn: psycopg.Connection, name: str, embedder: Embedder, workdir: Path) -> int:
    """Embeddings são calculados antes de tocar no banco; a troca é atômica."""
    sha, chunks = _collect(name, workdir)
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        vectors.extend(embedder.embed([f"{c.title_path}\n{c.content}" for c in batch]))
    now = datetime.now(timezone.utc)
    with conn.transaction():
        conn.execute("delete from chunks where source = %s", (name,))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into chunks (source, url, title_path, content, version, collected_at, embedding) "
                "values (%s, %s, %s, %s, %s, %s, %s::vector)",
                [(c.source, c.url, c.title_path, c.content, sha, now, v) for c, v in zip(chunks, vectors)],
            )
    return len(chunks)

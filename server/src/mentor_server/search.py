"""Busca híbrida: vetor (multilíngue) + full-text (identificadores), fundidos por RRF."""

from dataclasses import dataclass
from datetime import datetime

import psycopg

from mentor_server.embed import Embedder

CANDIDATES = 20
RRF_K = 60

_SQL = """
with vec as (
    select id, row_number() over (order by embedding <=> %(qvec)s::vector) as rnk
    from chunks
    where %(source)s::text is null or source = %(source)s
    order by embedding <=> %(qvec)s::vector
    limit %(cand)s
),
fts as (
    select id, row_number() over (order by ts_rank_cd(tsv, q) desc) as rnk
    from chunks, websearch_to_tsquery('simple', %(qtext)s) q
    where tsv @@ q and (%(source)s::text is null or source = %(source)s)
    order by ts_rank_cd(tsv, q) desc
    limit %(cand)s
),
fused as (
    select id, sum(1.0 / (%(rrf)s + rnk)) as score
    from (select * from vec union all select * from fts) u
    group by id
)
select c.source, c.url, c.title_path, c.content, c.version, c.collected_at, f.score
from fused f join chunks c on c.id = f.id
order by f.score desc, c.id
limit %(k)s
"""


@dataclass(frozen=True)
class Hit:
    source: str
    url: str
    title_path: str
    content: str
    version: str
    collected_at: datetime
    score: float


def search(
    conn: psycopg.Connection,
    embedder: Embedder,
    query: str,
    *,
    source: str | None = None,
    k: int = 5,
) -> list[Hit]:
    [qvec] = embedder.embed([query])
    rows = conn.execute(
        _SQL,
        {"qvec": qvec, "qtext": query, "source": source, "cand": CANDIDATES, "rrf": RRF_K, "k": k},
    ).fetchall()
    return [Hit(*r[:6], score=float(r[6])) for r in rows]

"""Avaliação da recuperação: recall@k e MRR sobre um conjunto de perguntas com URLs esperadas."""

import json
from pathlib import Path

DEFAULT_CASES = Path("evals/retrieval.jsonl")
OUT = Path("evals/out/retrieval.json")


def recall_at_k(results: list[list[str]], expected: list[set[str]], k: int) -> float:
    if not results:
        return 0.0
    hits = sum(bool(set(r[:k]) & e) for r, e in zip(results, expected))
    return hits / len(results)


def mrr(results: list[list[str]], expected: list[set[str]]) -> float:
    if not results:
        return 0.0
    total = 0.0
    for r, e in zip(results, expected):
        for i, url in enumerate(r, start=1):
            if url in e:
                total += 1 / i
                break
    return total / len(results)


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def main() -> None:
    from mentor_server.config import Settings
    from mentor_server.db.connection import connect
    from mentor_server.embed import make_embedder
    from mentor_server.search import search

    settings = Settings()
    embedder = make_embedder(settings)
    casos = load_cases(DEFAULT_CASES)
    results, expected, detalhes = [], [], []
    with connect(settings.database_url) as conn:
        for c in casos:
            # URLs únicas na ordem do ranking (várias seções da mesma página contam como uma)
            urls = list(dict.fromkeys(h.url for h in search(conn, embedder, c["pergunta"], k=10)))
            results.append(urls)
            expected.append(set(c["urls_esperadas"]))
            detalhes.append({**c, "urls_obtidas": urls[:5]})
    r5, m = recall_at_k(results, expected, 5), mrr(results, expected)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"recall@5": r5, "mrr": m, "casos": detalhes}, ensure_ascii=False, indent=2), "utf-8"
    )
    print(f"recall@5={r5:.2f} mrr={m:.2f}")

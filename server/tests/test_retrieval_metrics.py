import json
from pathlib import Path

import pytest

from mentor_server.evals.retrieval import load_cases, mrr, recall_at_k

CASES = Path(__file__).parent.parent / "evals" / "retrieval.jsonl"


def test_recall_e_mrr():
    res = [["u1", "u2"], ["u3", "u9"], ["u8", "u7"]]
    esp = [{"u2"}, {"u3"}, {"u5"}]
    assert recall_at_k(res, esp, k=2) == pytest.approx(2 / 3)
    assert recall_at_k(res, esp, k=1) == pytest.approx(1 / 3)
    assert mrr(res, esp) == pytest.approx((1 / 2 + 1 + 0) / 3)


def test_listas_vazias():
    assert recall_at_k([], [], k=5) == 0.0 and mrr([], []) == 0.0


def test_conjunto_tem_20_casos_validos():
    casos = load_cases(CASES)
    assert len(casos) == 20
    assert sum(c["tipo"] == "pt-sobre-en" for c in casos) >= 10
    assert all(c["urls_esperadas"] and all(u.startswith("https://") for u in c["urls_esperadas"]) for c in casos)
    assert {c["tipo"] for c in casos} <= {"pt-sobre-en", "identificador", "conceito"}

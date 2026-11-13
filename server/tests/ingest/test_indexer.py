from pathlib import Path

import pytest

from mentor_server.embed import FakeEmbedder
from mentor_server.ingest import indexer
from mentor_server.ingest.indexer import index_source

FIXTURES = Path(__file__).parent.parent / "fixtures"


def fake_fetch(sha: str):
    def _fetch(src, workdir):
        base = FIXTURES / src.name / src.subdir
        return sha, sorted(base.rglob("*.md"))

    return _fetch


class EmbedderQueFalha(FakeEmbedder):
    def embed(self, texts):
        raise RuntimeError("falha simulada no provedor de embeddings")


@pytest.mark.db
def test_indexar_grava_versao_data_e_substitui(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch("abc123"))
    n1 = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    n2 = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    assert n1 == n2 > 0
    rows = db.execute(
        "select count(*), min(version), max(collected_at) is not null from chunks where source='mdn'"
    ).fetchone()
    assert rows == (n1, "abc123", True)


@pytest.mark.db
def test_indexar_guarda_url_canonica(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch("abc123"))
    index_source(db, "mdn", FakeEmbedder(), tmp_path)
    urls = {r[0] for r in db.execute("select url from chunks").fetchall()}
    assert "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map/get" in urls


@pytest.mark.db
def test_falha_no_meio_nao_apaga_indice_antigo(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch("abc123"))
    n = index_source(db, "mdn", FakeEmbedder(), tmp_path)
    with pytest.raises(RuntimeError):
        index_source(db, "mdn", EmbedderQueFalha(), tmp_path)
    assert db.execute("select count(*) from chunks where source='mdn'").fetchone()[0] == n


@pytest.mark.db
def test_indexar_uma_fonte_nao_mexe_nas_outras(db, tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "fetch_source", fake_fetch("abc123"))
    index_source(db, "node", FakeEmbedder(), tmp_path)
    n_node = db.execute("select count(*) from chunks where source='node'").fetchone()[0]
    index_source(db, "mdn", FakeEmbedder(), tmp_path)
    assert db.execute("select count(*) from chunks where source='node'").fetchone()[0] == n_node > 0

import pytest

from mentor_server.embed import FakeEmbedder, OllamaEmbedder
from mentor_server.search import search


@pytest.mark.db
def test_identificador_exato_vence_pelo_full_text(db_indexado_fake):
    hits = search(db_indexado_fake, FakeEmbedder(), "Map.prototype.get")
    assert hits[0].title_path.startswith("Map.prototype.get()")


@pytest.mark.db
def test_filtro_por_fonte(db_indexado_fake):
    hits = search(db_indexado_fake, FakeEmbedder(), "read file", source="node")
    assert hits and {h.source for h in hits} == {"node"}


@pytest.mark.db
def test_sem_duplicatas_e_respeita_k(db_indexado_fake):
    hits = search(db_indexado_fake, FakeEmbedder(), "array", k=3)
    assert 0 < len(hits) <= 3
    assert len({(h.url, h.title_path) for h in hits}) == len(hits)


@pytest.mark.db
def test_hit_traz_citacao_completa(db_indexado_fake):
    h = search(db_indexado_fake, FakeEmbedder(), "push")[0]
    assert h.url.startswith("https://") and h.version == "fixture-sha" and h.collected_at is not None


@pytest.mark.db
@pytest.mark.slow
def test_pergunta_em_portugues_acha_map_get(db_indexado_bge):  # Review Focus 1
    hits = search(db_indexado_bge, OllamaEmbedder(), "como pego um valor de um Map?")
    assert any("Map.prototype.get" in h.title_path for h in hits[:5])

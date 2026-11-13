import math

from mentor_server.embed import DIM, FakeEmbedder


def test_fake_embedder_e_deterministico_e_1024():
    a, b = FakeEmbedder().embed(["oi", "oi"])
    assert a == b and len(a) == DIM == 1024


def test_fake_embedder_normalizado_e_distingue_textos():
    a, b = FakeEmbedder().embed(["oi", "tchau"])
    assert math.isclose(sum(x * x for x in a), 1.0, rel_tol=1e-6)
    assert a != b

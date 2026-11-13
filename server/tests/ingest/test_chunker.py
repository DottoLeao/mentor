from mentor_server.ingest.chunker import split_markdown


def test_divide_por_titulo_e_guarda_caminho():
    md = (
        "---\ntitle: Map\n---\n# Map\nIntro.\n## get()\nRetorna o valor.\n"
        "### Exemplo\n```js\nm.get(1)\n```"
    )
    chunks = split_markdown(md, source="mdn", url="https://developer.mozilla.org/x")
    assert [c.title_path for c in chunks] == ["Map", "Map > get()", "Map > get() > Exemplo"]
    assert "m.get(1)" in chunks[2].content
    assert all(c.source == "mdn" and c.url == "https://developer.mozilla.org/x" for c in chunks)


def test_remove_front_matter():
    chunks = split_markdown("---\ntitle: X\n---\n# X\ncorpo", source="s", url="u")
    assert "title:" not in chunks[0].content


def test_secao_longa_vira_varios_trechos_sem_partir_bloco_de_codigo():
    corpo = ("palavra " * 300) + "\n```js\n" + ("x;\n" * 50) + "```\n"
    chunks = split_markdown("# T\n" + corpo, source="s", url="u", max_chars=1200)
    assert len(chunks) > 1
    assert all(c.content.count("```") % 2 == 0 for c in chunks)


def test_partes_de_uma_secao_tem_caminhos_distintos():
    corpo = "\n\n".join(["frase " * 60] * 6)
    chunks = split_markdown("# T\n" + corpo, source="s", url="u", max_chars=500)
    caminhos = [c.title_path for c in chunks]
    assert len(set(caminhos)) == len(caminhos)
    assert caminhos[0] == "T"


def test_secao_vazia_e_ignorada():
    assert [c.title_path for c in split_markdown("# A\n## B\ntexto", source="s", url="u")] == ["A > B"]


def test_titulo_dentro_de_bloco_de_codigo_nao_e_titulo():
    md = "# A\n```sh\n# comentario\n```\n"
    chunks = split_markdown(md, source="s", url="u")
    assert [c.title_path for c in chunks] == ["A"]
    assert "# comentario" in chunks[0].content

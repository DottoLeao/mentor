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


MDN_REAL = """---
title: Map.prototype.get()
slug: Web/JavaScript/Reference/Global_Objects/Map/get
page-type: javascript-instance-method
---

The **`get()`** method of {{jsxref("Map")}} instances returns a specified element from this map.

## Syntax

```js-nolint
get(key)
```

### Parameters

- `key`
  - : The key of the element to return from the `Map` object.

### Return value

The element associated with the specified key.

## Examples

### Using get()

```js
myMap.get("bar");
```
"""


def test_titulo_do_front_matter_vira_raiz_e_introducao_e_mantida():
    chunks = split_markdown(MDN_REAL, source="mdn", url="u")
    assert [c.title_path for c in chunks] == [
        "Map.prototype.get()",
        "Map.prototype.get() > Syntax",
        "Map.prototype.get() > Syntax > Parameters",
        "Map.prototype.get() > Syntax > Return value",
        "Map.prototype.get() > Examples > Using get()",
    ]
    assert "returns a specified element" in chunks[0].content


def test_irmaos_do_mesmo_nivel_sem_h1_nao_se_aninham():
    chunks = split_markdown("## B\nx\n## C\ny\n### D\nz\n## E\nw", source="s", url="u")
    assert [c.title_path for c in chunks] == ["B", "C", "C > D", "E"]


def test_h1_igual_ao_titulo_nao_duplica():
    md = "---\ntitle: File system\n---\n# File system\nintro\n## readFile\nx"
    assert [c.title_path for c in split_markdown(md, source="s", url="u")] == [
        "File system",
        "File system > readFile",
    ]

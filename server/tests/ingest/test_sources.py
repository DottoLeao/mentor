from pathlib import Path

from mentor_server.ingest.sources import SOURCES


def test_tres_fontes():
    assert set(SOURCES) == {"mdn", "typescript", "node"}
    assert SOURCES["mdn"].license == "CC-BY-SA-2.5"
    assert SOURCES["node"].license == "MIT"


def test_url_mdn():
    p = Path("files/en-us/web/javascript/reference/global_objects/map/get/index.md")
    assert (
        SOURCES["mdn"].url_for(p)
        == "https://developer.mozilla.org/en-US/docs/Web/JavaScript/reference/global_objects/map/get"
    )


def test_url_mdn_usa_slug_quando_existe(tmp_path):
    d = tmp_path / "files/en-us/web/javascript/reference/global_objects/map/get"
    d.mkdir(parents=True)
    f = d / "index.md"
    f.write_text("---\ntitle: Map.prototype.get()\nslug: Web/JavaScript/Reference/Global_Objects/Map/get\n---\n# x")
    assert (
        SOURCES["mdn"].url_for(f)
        == "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map/get"
    )


def test_url_node():
    assert SOURCES["node"].url_for(Path("doc/api/fs.md")) == "https://nodejs.org/docs/latest/api/fs.html"


def test_url_typescript_usa_permalink(tmp_path):
    f = tmp_path / "Everyday Types.md"
    f.write_text("---\npermalink: /docs/handbook/2/everyday-types.html\n---\n# T")
    assert (
        SOURCES["typescript"].url_for(f)
        == "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html"
    )


def test_arquivo_sem_url_e_pulado(tmp_path):
    f = tmp_path / "sem.md"
    f.write_text("# sem permalink")
    assert SOURCES["typescript"].url_for(f) is None

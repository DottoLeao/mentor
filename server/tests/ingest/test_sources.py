from pathlib import Path

import pytest

from mentor_server.ingest.sources import SOURCES


def test_quatro_fontes():
    assert list(SOURCES) == ["mdn", "typescript", "node", "vscode"]
    assert SOURCES["vscode"].license == "CC-BY-3.0-US"
    assert SOURCES["vscode"].subdirs == ("docs", "release-notes")
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


def test_licenca_do_typescript_confirmada():
    assert SOURCES["typescript"].license == "CC-BY-4.0"


def test_url_vscode_docs():
    p = Path(".work/sources/vscode/docs/editor/debugging.md")
    assert SOURCES["vscode"].url_for(p) == "https://code.visualstudio.com/docs/editor/debugging"


def test_url_vscode_docs_aninhado():
    p = Path("/x/vscode/docs/copilot/reference/copilot-settings.md")
    assert SOURCES["vscode"].url_for(p) == "https://code.visualstudio.com/docs/copilot/reference/copilot-settings"


def test_url_vscode_release_notes():
    p = Path(".work/sources/vscode/release-notes/v1_95.md")
    assert SOURCES["vscode"].url_for(p) == "https://code.visualstudio.com/updates/v1_95"


@pytest.mark.parametrize(
    "rel",
    [
        "README.md",
        "blogs/2024/10/01/post.md",
        "release-notes/November_2015.md",  # nome antigo sem padrão vX_Y: pular, nunca URL quebrada
        "release-notes/images/1_95/x.md",
        "docs/_partials/aviso.md",
    ],
)
def test_url_vscode_fora_do_padrao_e_none(rel):  # Review Focus 5
    assert SOURCES["vscode"].url_for(Path("/w/vscode") / rel) is None


def test_url_vscode_sem_titulo_no_front_matter(tmp_path):  # Review Focus 5
    d = tmp_path / "vscode/docs/terminal"
    d.mkdir(parents=True)
    f = d / "basics.md"
    f.write_text("---\nContentId: x\n---\nsem título nenhum", "utf-8")
    assert SOURCES["vscode"].url_for(f) == "https://code.visualstudio.com/docs/terminal/basics"

"""Fontes oficiais indexadas e como chegar na URL pública de cada arquivo."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Source:
    name: str
    repo: str
    subdir: str
    license: str
    url_for: Callable[[Path], str | None]


def front_matter(path: Path) -> dict[str, str]:
    """Lê o front matter simples (chave: valor) de um arquivo, se ele existir."""
    try:
        text = path.read_text("utf-8")
    except OSError:
        return {}
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    out = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return out


_MDN_MARKER = "files/en-us/web/javascript/"


def _mdn_url(path: Path) -> str | None:
    slug = front_matter(path).get("slug")
    if slug:
        return f"https://developer.mozilla.org/en-US/docs/{slug}"
    posix = path.as_posix()
    i = posix.find(_MDN_MARKER)
    if i == -1:
        return None
    rest = posix[i + len(_MDN_MARKER) :].removesuffix("index.md").rstrip("/")
    base = "https://developer.mozilla.org/en-US/docs/Web/JavaScript"
    return f"{base}/{rest}" if rest else base


def _ts_url(path: Path) -> str | None:
    permalink = front_matter(path).get("permalink")
    return f"https://www.typescriptlang.org{permalink}" if permalink else None


def _node_url(path: Path) -> str | None:
    return f"https://nodejs.org/docs/latest/api/{path.stem}.html"


SOURCES: dict[str, Source] = {
    "mdn": Source("mdn", "https://github.com/mdn/content", "files/en-us/web/javascript", "CC-BY-SA-2.5", _mdn_url),
    # Licença do conteúdo do TypeScript-Website a confirmar (ticket MENTOR-5).
    "typescript": Source(
        "typescript",
        "https://github.com/microsoft/TypeScript-Website",
        "packages/documentation/copy/en/handbook-v2",
        "verificar",
        _ts_url,
    ),
    "node": Source("node", "https://github.com/nodejs/node", "doc/api", "MIT", _node_url),
}


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def fetch_source(src: Source, workdir: Path) -> tuple[str, list[Path]]:
    """Clone raso e esparso da fonte (ou atualiza um existente). Devolve (sha, arquivos .md)."""
    dest = workdir / src.name
    if (dest / ".git").exists():
        _git("fetch", "--depth", "1", "origin", cwd=dest)
        _git("reset", "--hard", "FETCH_HEAD", cwd=dest)
    else:
        workdir.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", "--filter=blob:none", "--sparse", src.repo, str(dest))
    _git("sparse-checkout", "set", src.subdir, cwd=dest)
    sha = _git("rev-parse", "HEAD", cwd=dest)
    files = sorted((dest / src.subdir).rglob("*.md"))
    return sha, files

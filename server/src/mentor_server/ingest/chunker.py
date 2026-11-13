"""Divide documentação em Markdown em trechos por título."""

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class Chunk:
    source: str
    url: str
    title_path: str
    content: str


def _split_front_matter(text: str) -> tuple[str | None, str]:
    """Devolve (title do front matter, corpo sem o front matter)."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            title = None
            for line in text[4:end].splitlines():
                m = re.match(r"^title:\s*(.+)$", line)
                if m:
                    title = m.group(1).strip().strip("\"'")
            return title, text[end + 5 :]
    return None, text


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _sections(text: str, root: str | None) -> list[tuple[str, list[str]]]:
    """Seções por título. O title do front matter é a raiz; o texto antes do
    primeiro título pertence à raiz. Títulos fecham os de nível igual ou maior."""
    sections: list[tuple[str, list[str]]] = []
    stack: list[tuple[int, str]] = [(0, root)] if root else []
    lines: list[str] = []
    in_code = False

    def flush():
        if stack:
            sections.append((" > ".join(t for _, t in stack), lines))

    for line in text.splitlines():
        if _is_fence(line):
            in_code = not in_code
        m = None if in_code or _is_fence(line) else _HEADING.match(line)
        if not m:
            lines.append(line)
            continue
        level, title = len(m.group(1)), m.group(2)
        if root and level == 1 and title == root:
            continue  # h1 repete o title do front matter
        flush()
        lines = []
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
    flush()
    return sections


def _blocks(lines: list[str]) -> list[str]:
    """Parágrafos separados por linha em branco; cada bloco de código é um bloco inteiro."""
    blocks: list[str] = []
    cur: list[str] = []
    in_code = False

    def push():
        if any(x.strip() for x in cur):
            blocks.append("\n".join(cur).strip("\n"))
        cur.clear()

    for line in lines:
        if _is_fence(line):
            if not in_code:
                push()
                cur.append(line)
                in_code = True
            else:
                cur.append(line)
                push()
                in_code = False
        elif in_code:
            cur.append(line)
        elif not line.strip():
            push()
        else:
            cur.append(line)
    push()
    return blocks


def _split_prose(block: str, max_chars: int) -> list[str]:
    parts, cur = [], ""
    for word in block.split():
        if cur and len(cur) + 1 + len(word) > max_chars:
            parts.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        parts.append(cur)
    return parts


def _pack(blocks: list[str], max_chars: int) -> list[str]:
    pieces: list[str] = []
    for b in blocks:
        if len(b) > max_chars and "```" not in b:
            pieces.extend(_split_prose(b, max_chars))
        else:
            pieces.append(b)
    parts: list[str] = []
    cur = ""
    for p in pieces:
        if cur and len(cur) + 2 + len(p) > max_chars:
            parts.append(cur)
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        parts.append(cur)
    return parts


def split_markdown(text: str, *, source: str, url: str, max_chars: int = 1200) -> list[Chunk]:
    chunks: list[Chunk] = []
    root, body = _split_front_matter(text)
    for title_path, lines in _sections(body, root):
        for i, part in enumerate(_pack(_blocks(lines), max_chars), start=1):
            path = title_path if i == 1 else f"{title_path} (parte {i})"
            chunks.append(Chunk(source=source, url=url, title_path=path, content=part))
    return chunks

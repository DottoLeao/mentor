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


def _strip_front_matter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    stack: list[str] = []
    lines: list[str] = []
    in_code = False

    def flush():
        if stack:
            sections.append((" > ".join(stack), lines))

    for line in text.splitlines():
        if _is_fence(line):
            in_code = not in_code
        m = None if in_code or _is_fence(line) else _HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            stack = stack[: level - 1] + [m.group(2)]
            lines = []
        else:
            lines.append(line)
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
    for title_path, lines in _sections(_strip_front_matter(text)):
        for i, part in enumerate(_pack(_blocks(lines), max_chars), start=1):
            path = title_path if i == 1 else f"{title_path} (parte {i})"
            chunks.append(Chunk(source=source, url=url, title_path=path, content=part))
    return chunks

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path

_STORAGE_ROOT = Path.home() / "qagent-data" / "notes"
_MAX_TEXT = 32_000
_MAX_LIST = 50
_PREVIEW_CHARS = 80


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text or "untitled"


def _truncate(text: str, limit: int = _MAX_TEXT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [{len(text) - limit} chars truncated]"


def _find_note(name: str) -> Path | None:
    if not _STORAGE_ROOT.exists():
        return None
    candidate = _STORAGE_ROOT / name
    if candidate.is_file():
        return candidate
    if not name.endswith(".md"):
        with_ext = _STORAGE_ROOT / f"{name}.md"
        if with_ext.is_file():
            return with_ext
    slug = _slugify(name)
    matches = sorted(
        (p for p in _STORAGE_ROOT.glob("*.md") if slug in p.stem),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def write_note(title: str, content: str) -> str:
    try:
        _ensure_dir(_STORAGE_ROOT)
        slug = _slugify(title)
        date = datetime.now().strftime("%Y-%m-%d")
        target = _STORAGE_ROOT / f"{date}-{slug}.md"
        timestamp = datetime.now().isoformat(timespec="seconds")
        body = f"# {title}\n\n_{timestamp}_\n\n{content}\n"
        target.write_text(body, encoding="utf-8")
        return f"Saved note to {target}"
    except OSError as exc:
        return f"Error: failed to save note: {exc}"


def list_notes() -> str:
    try:
        if not _STORAGE_ROOT.exists():
            return "(no notes)"
        files = [p for p in _STORAGE_ROOT.glob("*.md") if p.is_file()]
        if not files:
            return "(no notes)"
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        lines: list[str] = []
        for path in files[:_MAX_LIST]:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            body_lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip() and not line.startswith("#") and not line.startswith("_")
            ]
            preview = " ".join(body_lines)[:_PREVIEW_CHARS]
            lines.append(f"{path.name}: {preview}")
        return "\n".join(lines)
    except OSError as exc:
        return f"Error: failed to list notes: {exc}"


def read_note(name: str) -> str:
    try:
        target = _find_note(name)
        if target is None:
            return f"Error: note not found: {name}"
        return _truncate(target.read_text(encoding="utf-8", errors="replace"))
    except OSError as exc:
        return f"Error: failed to read note: {exc}"


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "Save a personal note as a Markdown file in the user's note store.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title used for the filename and H1 heading.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Body of the note in Markdown.",
                    },
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List recent saved notes with short previews.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_note",
            "description": "Read a note's full contents by filename or slug.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Note filename (e.g. 2026-05-24-shopping.md) or slug fragment.",
                    }
                },
                "required": ["name"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    if name == "write_note":
        title = args.get("title")
        content = args.get("content")
        if not isinstance(title, str) or not isinstance(content, str):
            return "Error: write_note requires string title and content"
        return write_note(title, content)
    if name == "list_notes":
        return list_notes()
    if name == "read_note":
        note_name = args.get("name")
        if not isinstance(note_name, str):
            return "Error: read_note requires string name"
        return read_note(note_name)
    return None

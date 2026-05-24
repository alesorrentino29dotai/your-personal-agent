from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

_STORAGE_ROOT = Path.home() / "qagent-data" / "drafts"
_PREVIEW_CHARS = 60


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return ascii_text or "untitled"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _save_draft(prefix: str, payload: dict) -> Path:
    _ensure_dir(_STORAGE_ROOT)
    target = _STORAGE_ROOT / f"{prefix}-{_timestamp()}.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def _find_draft(name: str) -> Path | None:
    if not _STORAGE_ROOT.exists():
        return None
    candidate = _STORAGE_ROOT / name
    if candidate.is_file():
        return candidate
    if not name.endswith(".json"):
        with_ext = _STORAGE_ROOT / f"{name}.json"
        if with_ext.is_file():
            return with_ext
    slug = _slugify(name)
    matches = sorted(
        (p for p in _STORAGE_ROOT.glob("*.json") if slug in p.stem),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return matches[0] if matches else None


def _load_draft(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def draft_email(to: str, subject: str, body: str) -> str:
    try:
        payload = {
            "kind": "email",
            "to": to,
            "subject": subject,
            "body": body,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        target = _save_draft("email", payload)
        return f"Email draft saved to {target}"
    except OSError as exc:
        return f"Error: failed to save email draft: {exc}"


def draft_telegram(chat: str, message: str) -> str:
    try:
        payload = {
            "kind": "telegram",
            "chat": chat,
            "message": message,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        target = _save_draft("tg", payload)
        return f"Telegram draft saved to {target}"
    except OSError as exc:
        return f"Error: failed to save telegram draft: {exc}"


def draft_whatsapp(to: str, message: str) -> str:
    try:
        payload = {
            "kind": "whatsapp",
            "to": to,
            "message": message,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        target = _save_draft("wa", payload)
        return f"WhatsApp draft saved to {target}"
    except OSError as exc:
        return f"Error: failed to save whatsapp draft: {exc}"


def list_drafts() -> str:
    try:
        if not _STORAGE_ROOT.exists():
            return "(no drafts)"
        files = sorted(
            (p for p in _STORAGE_ROOT.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return "(no drafts)"
        lines: list[str] = []
        for path in files:
            data = _load_draft(path)
            if data is None:
                lines.append(f"{path.name} | (unreadable)")
                continue
            kind = str(data.get("kind", "?"))
            recipient = str(data.get("to") or data.get("chat") or "")
            body = str(data.get("body") or data.get("message") or "")
            preview = body.replace("\n", " ")[:_PREVIEW_CHARS]
            lines.append(f"{path.name} | {kind} | {recipient} | {preview}")
        return "\n".join(lines)
    except OSError as exc:
        return f"Error: failed to list drafts: {exc}"


def read_draft(name: str) -> str:
    try:
        target = _find_draft(name)
        if target is None:
            return f"Error: draft not found: {name}"
        data = _load_draft(target)
        if data is None:
            return f"Error: could not parse draft {target.name}"
        kind = str(data.get("kind", "?"))
        recipient = data.get("to") or data.get("chat") or ""
        subject = data.get("subject")
        body = data.get("body") or data.get("message") or ""
        created = data.get("created_at", "")
        lines = [
            f"kind: {kind}",
            f"to: {recipient}" if "to" in data else f"chat: {recipient}",
            f"created_at: {created}",
        ]
        if subject:
            lines.append(f"subject: {subject}")
        lines.append("")
        lines.append(str(body))
        return "\n".join(lines)
    except OSError as exc:
        return f"Error: failed to read draft: {exc}"


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "draft_email",
            "description": "Save an email draft as JSON in the user's draft store.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject line."},
                    "body": {"type": "string", "description": "Email body text."},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_telegram",
            "description": "Save a Telegram message draft as JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chat": {"type": "string", "description": "Telegram chat name or handle."},
                    "message": {"type": "string", "description": "Message text."},
                },
                "required": ["chat", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_whatsapp",
            "description": "Save a WhatsApp message draft as JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone or contact label."},
                    "message": {"type": "string", "description": "Message text."},
                },
                "required": ["to", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_drafts",
            "description": "List all saved drafts with recipient and preview.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_draft",
            "description": "Read a single saved draft by filename or slug fragment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Draft filename (e.g. email-20260524-093000.json) or fragment.",
                    }
                },
                "required": ["name"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    if name == "draft_email":
        to = args.get("to")
        subject = args.get("subject")
        body = args.get("body")
        if not isinstance(to, str) or not isinstance(subject, str) or not isinstance(body, str):
            return "Error: draft_email requires string to, subject, body"
        return draft_email(to, subject, body)
    if name == "draft_telegram":
        chat = args.get("chat")
        message = args.get("message")
        if not isinstance(chat, str) or not isinstance(message, str):
            return "Error: draft_telegram requires string chat and message"
        return draft_telegram(chat, message)
    if name == "draft_whatsapp":
        to = args.get("to")
        message = args.get("message")
        if not isinstance(to, str) or not isinstance(message, str):
            return "Error: draft_whatsapp requires string to and message"
        return draft_whatsapp(to, message)
    if name == "list_drafts":
        return list_drafts()
    if name == "read_draft":
        draft_name = args.get("name")
        if not isinstance(draft_name, str):
            return "Error: read_draft requires string name"
        return read_draft(draft_name)
    return None

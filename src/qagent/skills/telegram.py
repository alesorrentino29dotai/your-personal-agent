from __future__ import annotations

import os

import httpx

_API_BASE = "https://api.telegram.org"
_SEND_TIMEOUT = 15.0


def _token() -> str | None:
    token = os.environ.get("QAGENT_TG_BOT_TOKEN")
    return token.strip() if token else None


def _default_chat() -> str | None:
    chat = os.environ.get("QAGENT_TG_DEFAULT_CHAT")
    return chat.strip() if chat else None


def is_configured() -> bool:
    return bool(_token())


def allowed_chat_ids() -> set[int]:
    raw = os.environ.get("QAGENT_TG_ALLOWED_CHATS", "")
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


def send_telegram(message: str, chat: str | None = None) -> str:
    token = _token()
    if not token:
        return "Error: QAGENT_TG_BOT_TOKEN is not set"

    target = chat if chat is not None else _default_chat()
    if not target:
        return "Error: no chat id provided and QAGENT_TG_DEFAULT_CHAT is not set"

    url = f"{_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": target, "text": message}
    try:
        response = httpx.post(url, json=payload, timeout=_SEND_TIMEOUT)
    except httpx.HTTPError as exc:
        return f"Error: telegram request failed: {exc}"

    if response.status_code != 200:
        body = response.text.strip()
        if len(body) > 300:
            body = body[:297] + "..."
        return f"Error: telegram api returned {response.status_code}: {body}"

    try:
        data = response.json()
    except ValueError:
        return "Error: telegram api returned non-json response"

    if not data.get("ok"):
        description = data.get("description", "unknown error")
        return f"Error: telegram api: {description}"

    return f"Telegram message sent to {target}"


def get_updates(offset: int | None = None, timeout: int = 25) -> list[dict]:
    token = _token()
    if not token:
        return []

    url = f"{_API_BASE}/bot{token}/getUpdates"
    params: dict[str, int] = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset

    try:
        response = httpx.get(url, params=params, timeout=timeout + 10)
    except httpx.HTTPError:
        return []

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except ValueError:
        return []

    if not data.get("ok"):
        return []

    result = data.get("result")
    return result if isinstance(result, list) else []


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": (
                "Send a plain-text Telegram message via the configured bot. "
                "If chat is omitted, the default chat from QAGENT_TG_DEFAULT_CHAT is used."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Plain text body to send (Markdown is not parsed).",
                    },
                    "chat": {
                        "type": "string",
                        "description": "Optional chat id (string). Falls back to default chat.",
                    },
                },
                "required": ["message"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    if name == "send_telegram":
        message = args.get("message")
        if not isinstance(message, str):
            return "Error: send_telegram requires string message"
        chat = args.get("chat")
        if chat is not None and not isinstance(chat, str):
            return "Error: send_telegram chat must be a string when provided"
        return send_telegram(message, chat=chat)
    return None

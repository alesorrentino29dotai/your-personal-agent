from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from qagent.providers.base import LLMProvider


CONTACTS_PATH = Path.home() / "qagent-data" / "contacts.json"


TELEGRAM_PROMPT = """Extract a Telegram message intent from the user input.
Reply with ONLY valid JSON, no markdown, no code fences, no explanation.

Schema:
{"contact": "<recipient name or chat handle>", "message": "<message body>"}

Examples:
Input: "send a telegram to marco saying I'll be late"
Output: {"contact": "marco", "message": "I'll be late"}

Input: "tell mom on telegram happy birthday"
Output: {"contact": "mom", "message": "Happy birthday"}

User input: {INPUT}
JSON:"""


CALL_PROMPT = """Extract a phone call intent from the user input.
Reply with ONLY valid JSON, no markdown, no code fences, no explanation.

Schema:
{"contact": "<name>", "number": "<digits or null>"}

Examples:
Input: "call marco"
Output: {"contact": "marco", "number": null}

Input: "phone +39 333 1234567"
Output: {"contact": "", "number": "+393331234567"}

Input: "dial mom on her cell"
Output: {"contact": "mom", "number": null}

User input: {INPUT}
JSON:"""


SMS_PROMPT = """Extract an SMS / text message intent from the user input.
Reply with ONLY valid JSON, no markdown, no code fences, no explanation.

Schema:
{"contact": "<name>", "number": "<digits or null>", "message": "<body>"}

Examples:
Input: "text marco I'm on my way"
Output: {"contact": "marco", "number": null, "message": "I'm on my way"}

Input: "send an sms to mom saying see you soon"
Output: {"contact": "mom", "number": null, "message": "see you soon"}

User input: {INPUT}
JSON:"""


CALENDAR_PROMPT = """Extract a calendar event intent from the user input.
Reply with ONLY valid JSON, no markdown, no code fences, no explanation.

Today is {TODAY} ({WEEKDAY}). The current time is {NOW_TIME}.
TOMORROW is {TOMORROW}. The next 7 days are: {NEXT_DAYS}.
Resolve every relative date ("tomorrow", "tonight", "next monday") to an explicit YYYY-MM-DD.
Use 24-hour time. If no duration is given, default to 60. Never output placeholders like <TOMORROW>.

Schema:
{"title": "<event name>", "when": "<YYYY-MM-DDTHH:MM>", "duration_min": <int>, "notes": "<string>"}

Examples (assume today is 2026-03-10):
Input: "lunch with marco tomorrow at 12:30"
Output: {"title": "Lunch with marco", "when": "2026-03-11T12:30", "duration_min": 60, "notes": ""}

Input: "dentist next monday at 9am for 30 minutes"
Output: {"title": "Dentist", "when": "2026-03-16T09:00", "duration_min": 30, "notes": ""}

Input: "team standup tonight at 8 pm"
Output: {"title": "Team standup", "when": "2026-03-10T20:00", "duration_min": 60, "notes": ""}

User input: {INPUT}
JSON:"""


def _extract_json(text: str) -> dict | None:
    """Strip code fences, find first balanced {...} block, json.loads it."""
    if not text:
        return None

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    start = cleaned.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = cleaned[start : i + 1]
                try:
                    parsed = json.loads(blob)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _call_llm(provider: LLMProvider, prompt: str, max_tokens_hint: int = 200) -> str:
    """Send a JSON-only chat to the provider and return raw content."""
    messages = [
        {"role": "system", "content": "You output JSON only."},
        {"role": "user", "content": prompt},
    ]
    try:
        response = provider.chat(messages, tools=None)
    except Exception:
        return ""
    try:
        return response["message"]["content"] or ""
    except (KeyError, TypeError):
        return ""


def load_contacts() -> dict:
    """Load contacts file, returning {} if missing or invalid."""
    try:
        raw = CONTACTS_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).lower(): v for k, v in data.items()}


def _lookup_contact(contacts: dict | None, name: str | None) -> dict | None:
    if not contacts or not name:
        return None
    entry = contacts.get(name.strip().lower())
    return entry if isinstance(entry, dict) else None


def _normalize_number(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"[^\d+]", "", str(raw))
    return digits or None


def parse_telegram(
    provider: LLMProvider,
    transcript: str,
    contacts: dict | None = None,
) -> dict:
    prompt = TELEGRAM_PROMPT.replace("{INPUT}", transcript.strip())
    raw = _call_llm(provider, prompt)
    data = _extract_json(raw)
    if not data:
        return {"ok": False, "error": "could not parse telegram intent", "raw": raw}

    contact = str(data.get("contact") or "").strip()
    message = str(data.get("message") or "").strip()
    if not contact or not message:
        return {"ok": False, "error": "missing contact or message", "raw": raw}

    entry = _lookup_contact(contacts, contact)
    chat_id: str | None = None
    if entry is not None:
        chat_id_val = entry.get("telegram_chat_id")
        if chat_id_val is not None:
            chat_id = str(chat_id_val)

    return {
        "ok": True,
        "contact": contact,
        "chat_id": chat_id,
        "message": message,
    }


def parse_call(
    provider: LLMProvider,
    transcript: str,
    contacts: dict | None = None,
) -> dict:
    prompt = CALL_PROMPT.replace("{INPUT}", transcript.strip())
    raw = _call_llm(provider, prompt)
    data = _extract_json(raw)
    if not data:
        return {"ok": False, "error": "could not parse call intent", "raw": raw}

    contact = str(data.get("contact") or "").strip()
    number = _normalize_number(data.get("number"))

    if number is None:
        entry = _lookup_contact(contacts, contact)
        if entry is not None:
            number = _normalize_number(entry.get("phone"))

    if not number:
        return {"ok": False, "error": "no phone number for contact", "contact": contact}

    return {
        "ok": True,
        "contact": contact,
        "number": number,
        "tel_url": f"tel:{number}",
    }


def parse_sms(
    provider: LLMProvider,
    transcript: str,
    contacts: dict | None = None,
) -> dict:
    prompt = SMS_PROMPT.replace("{INPUT}", transcript.strip())
    raw = _call_llm(provider, prompt)
    data = _extract_json(raw)
    if not data:
        return {"ok": False, "error": "could not parse sms intent", "raw": raw}

    contact = str(data.get("contact") or "").strip()
    message = str(data.get("message") or "").strip()
    number = _normalize_number(data.get("number"))

    if number is None:
        entry = _lookup_contact(contacts, contact)
        if entry is not None:
            number = _normalize_number(entry.get("phone"))

    if not number:
        return {"ok": False, "error": "no phone number for contact", "contact": contact}
    if not message:
        return {"ok": False, "error": "empty sms body", "contact": contact}

    sms_url = f"sms:{number}&body={quote(message, safe='')}"
    return {
        "ok": True,
        "contact": contact,
        "number": number,
        "message": message,
        "sms_url": sms_url,
    }


_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _resolve_relative_token(value: str, now: datetime) -> str:
    """Best-effort replacement for relative date words the model may have left in."""
    if not value:
        return value
    text = value.strip()
    lowered = text.lower()

    # Match placeholders like <TOMORROW>T12:30 or TOMORROWT12:30
    placeholders = {
        "<today>": now.strftime("%Y-%m-%d"),
        "today": now.strftime("%Y-%m-%d"),
        "<tomorrow>": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "tomorrow": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "tonight": now.strftime("%Y-%m-%d"),
        "<tonight>": now.strftime("%Y-%m-%d"),
    }
    for needle, replacement in placeholders.items():
        idx = lowered.find(needle)
        if idx >= 0:
            text = text[:idx] + replacement + text[idx + len(needle):]
            lowered = text.lower()

    # Match <NEXT_MONDAY> / next monday
    for name, num in _WEEKDAYS.items():
        for needle in (f"<next_{name}>", f"next_{name}", f"next {name}"):
            idx = lowered.find(needle)
            if idx >= 0:
                days_ahead = (num - now.weekday()) % 7 or 7
                date_str = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                text = text[:idx] + date_str + text[idx + len(needle):]
                lowered = text.lower()
    return text


def _normalize_when(value: Any, now: datetime | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if now is not None:
        candidate = _resolve_relative_token(candidate, now)
    candidate = candidate.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M")


def parse_calendar(provider: LLMProvider, transcript: str) -> dict:
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    next_days = ", ".join(
        f"{(now + timedelta(days=i)).strftime('%a')}={(now + timedelta(days=i)).strftime('%Y-%m-%d')}"
        for i in range(7)
    )
    prompt = (
        CALENDAR_PROMPT
        .replace("{TODAY}", now.strftime("%Y-%m-%d"))
        .replace("{WEEKDAY}", now.strftime("%A"))
        .replace("{NOW_TIME}", now.strftime("%H:%M"))
        .replace("{TOMORROW}", tomorrow.strftime("%Y-%m-%d"))
        .replace("{NEXT_DAYS}", next_days)
        .replace("{INPUT}", transcript.strip())
    )
    raw = _call_llm(provider, prompt)
    data = _extract_json(raw)
    if not data:
        return {"ok": False, "error": "could not parse calendar intent", "raw": raw}

    title = str(data.get("title") or "").strip()
    when = _normalize_when(data.get("when"), now=now)
    notes = str(data.get("notes") or "").strip()

    duration_raw = data.get("duration_min", 60)
    try:
        duration_min = int(duration_raw)
    except (TypeError, ValueError):
        duration_min = 60
    if duration_min <= 0:
        duration_min = 60

    if not title:
        return {"ok": False, "error": "missing event title", "raw": raw}
    if not when:
        return {"ok": False, "error": "invalid or missing datetime", "raw": raw}

    return {
        "ok": True,
        "title": title,
        "when": when,
        "duration_min": duration_min,
        "notes": notes,
    }


@dataclass
class IntentResult:
    """Optional convenience wrapper for routed intents."""

    intent: str
    data: dict

    @property
    def ok(self) -> bool:
        return bool(self.data.get("ok"))

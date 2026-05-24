from __future__ import annotations

import json
import re
from typing import Any

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _find_balanced_json_objects(text: str) -> list[str]:
    blobs: list[str] = []
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    blobs.append(text[start : i + 1])
                    start = -1
    return blobs


def _parse_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _normalize_call(obj: dict) -> dict | None:
    if "function" in obj and isinstance(obj["function"], dict):
        fn = obj["function"]
        name = fn.get("name")
        if isinstance(name, str) and name:
            return {"name": name, "arguments": _parse_arguments(fn.get("arguments"))}
    name = obj.get("name") or obj.get("tool_name")
    if isinstance(name, str) and name:
        args = obj.get("arguments") or obj.get("args") or obj.get("parameters") or {}
        return {"name": name, "arguments": _parse_arguments(args)}
    return None


def _try_parse_json(text: str) -> dict | None:
    text = text.strip()
    if not text.startswith("{"):
        return None
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def extract_text_tool_calls(content: str) -> list[dict]:
    """Parse tool calls the model wrote as JSON in plain text (fallback)."""
    seen: set[str] = set()
    calls: list[dict] = []

    def add_call(call: dict | None) -> None:
        if not call:
            return
        key = json.dumps(call, sort_keys=True)
        if key in seen:
            return
        seen.add(key)
        calls.append(call)

    stripped = content.strip()
    whole = _try_parse_json(stripped)
    if whole:
        add_call(_normalize_call(whole))

    for match in _JSON_BLOCK.finditer(content):
        obj = _try_parse_json(match.group(1))
        if obj:
            add_call(_normalize_call(obj))

    for blob in _find_balanced_json_objects(content):
        obj = _try_parse_json(blob)
        if obj and ("name" in obj or "function" in obj):
            add_call(_normalize_call(obj))

    return calls

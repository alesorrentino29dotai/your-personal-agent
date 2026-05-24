from __future__ import annotations

from qagent.skills import (
    drafts,
    email_send,
    notes,
    presentations,
    telegram,
    web,
)

SKILL_MODULES = [
    notes,
    drafts,
    web,
    presentations,
    email_send,
    telegram,
]


def _iter_schemas(value) -> list[dict]:
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return []


def _normalize_schema(schema: dict) -> dict | None:
    if not isinstance(schema, dict):
        return None
    if schema.get("type") == "function" and isinstance(schema.get("function"), dict):
        return schema
    if "name" in schema and "parameters" in schema:
        return {"type": "function", "function": schema}
    return None


def all_schemas(allow_send: bool = False) -> list[dict]:
    schemas: list[dict] = []
    for mod in SKILL_MODULES:
        for raw in _iter_schemas(getattr(mod, "SCHEMAS", [])):
            schema = _normalize_schema(raw)
            if schema is None:
                continue
            name = (schema.get("function") or {}).get("name", "")
            if not allow_send and name in {"send_email", "send_telegram"}:
                continue
            schemas.append(schema)
    return schemas


def dispatch(name: str, arguments: dict, allow_send: bool = False) -> str | None:
    if not allow_send and name in {"send_email", "send_telegram"}:
        return f"Error: {name} is disabled (use --allow-send to enable)"
    for mod in SKILL_MODULES:
        result = mod.dispatch(name, arguments)
        if result is not None:
            return result
    return None

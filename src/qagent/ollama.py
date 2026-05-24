from __future__ import annotations

import httpx

OLLAMA_HOST = "http://127.0.0.1:11434"
_CHECK_TIMEOUT = 5.0


def check_ollama(host: str = OLLAMA_HOST) -> None:
    url = host.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(timeout=_CHECK_TIMEOUT) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {host}. Is `ollama serve` running? ({exc})"
        ) from exc


def list_models(host: str = OLLAMA_HOST) -> list[str]:
    url = host.rstrip("/") + "/api/tags"
    with httpx.Client(timeout=_CHECK_TIMEOUT) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    models = data.get("models") or []
    return [m["name"] for m in models if isinstance(m, dict) and "name" in m]


def has_model(name: str, host: str = OLLAMA_HOST) -> bool:
    models = list_models(host)
    if name in models:
        return True
    return any(m == name or m.startswith(f"{name}:") for m in models)


def chat(
    messages: list[dict],
    model: str,
    tools: list[dict] | None = None,
    host: str = OLLAMA_HOST,
) -> dict:
    url = host.rstrip("/") + "/api/chat"
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools is not None:
        payload["tools"] = tools
    with httpx.Client(timeout=None) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

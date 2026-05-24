from __future__ import annotations

import os

import httpx

_CHAT_TIMEOUT = 30.0
_META_TIMEOUT = 5.0


class OpenAICompatProvider:
    name = "openai-compat"

    def __init__(
        self,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        **_: object,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def chat(self, messages, tools=None):
        url = f"{self.base_url}/chat/completions"
        payload: dict = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=_CHAT_TIMEOUT) as client:
                response = client.post(url, json=payload, headers=self._headers())
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI-compatible chat request to {url} failed: {exc}"
            ) from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(
                f"OpenAI-compatible response from {url} had no choices: {data!r}"
            )
        message = choices[0].get("message") or {}
        return {"message": message}

    def health_check(self) -> None:
        url = f"{self.base_url}/models"
        try:
            with httpx.Client(timeout=_META_TIMEOUT) as client:
                response = client.get(url, headers=self._headers())
                if response.status_code == 401 and not self.api_key:
                    return
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Cannot reach OpenAI-compatible endpoint at {self.base_url}. "
                f"Is the server running and reachable? ({exc})"
            ) from exc

    def list_models(self) -> list[str]:
        url = f"{self.base_url}/models"
        try:
            with httpx.Client(timeout=_META_TIMEOUT) as client:
                response = client.get(url, headers=self._headers())
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return []
        items = data.get("data") or []
        return [item["id"] for item in items if isinstance(item, dict) and "id" in item]

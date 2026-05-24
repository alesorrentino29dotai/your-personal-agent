from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        ...

    def health_check(self) -> None:
        ...

    def list_models(self) -> list[str]:
        ...

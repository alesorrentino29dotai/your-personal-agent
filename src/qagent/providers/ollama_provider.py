from __future__ import annotations

from qagent import ollama as _ollama


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, host: str = _ollama.OLLAMA_HOST, **_: object) -> None:
        self.model = model
        self.host = host

    def chat(self, messages, tools=None):
        return _ollama.chat(messages, model=self.model, tools=tools, host=self.host)

    def health_check(self) -> None:
        _ollama.check_ollama(self.host)

    def list_models(self) -> list[str]:
        return _ollama.list_models(self.host)

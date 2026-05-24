from __future__ import annotations

from qagent.providers.base import LLMProvider
from qagent.providers.ollama_provider import OllamaProvider
from qagent.providers.openai_compat import OpenAICompatProvider

PROVIDERS = {
    "ollama": OllamaProvider,
    "openai": OpenAICompatProvider,
    "openai-compat": OpenAICompatProvider,
    "vllm": OpenAICompatProvider,
    "lmstudio": OpenAICompatProvider,
}


def create_provider(name: str, **kwargs) -> LLMProvider:
    key = (name or "ollama").lower()
    if key not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name!r}. Known: {sorted(PROVIDERS)}")
    return PROVIDERS[key](**kwargs)

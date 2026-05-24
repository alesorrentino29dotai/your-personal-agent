from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qagent import ollama
from qagent.tools import ToolRunner

SYSTEM_PROMPT = """You are a helpful coding assistant running locally via Ollama.
You have tools to read/list files under the user's project root and optionally run shell commands.
Be concise. When using tools, use correct relative paths from the project root.
If a tool fails, explain and try another approach."""


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


class Agent:
    def __init__(
        self,
        model: str,
        root: Path,
        allow_shell: bool,
        max_steps: int,
        host: str,
    ) -> None:
        self.model = model
        self.root = root
        self.allow_shell = allow_shell
        self.max_steps = max_steps
        self.host = host
        self._runner = ToolRunner(root, allow_shell=allow_shell)
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        tools = self._runner.schemas(self.allow_shell)

        for _ in range(self.max_steps):
            response = ollama.chat(
                self.messages,
                model=self.model,
                tools=tools,
                host=self.host,
            )
            message = response.get("message") or {}
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                content = message.get("content") or ""
                self.messages.append({"role": "assistant", "content": content})
                return content

            self.messages.append(message)
            for call in tool_calls:
                fn = call.get("function") or {}
                name = fn.get("name") or ""
                arguments = _parse_arguments(fn.get("arguments"))
                result = self._runner.run(name, arguments)
                self.messages.append(
                    {
                        "role": "tool",
                        "content": result,
                        "tool_name": name,
                    }
                )

        return f"Error: exceeded maximum tool steps ({self.max_steps})"

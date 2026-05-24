from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from qagent import ollama
from qagent.parsing import extract_text_tool_calls
from qagent.tools import ToolRunner

SYSTEM_PROMPT = """You are a personal local assistant with tools. The workspace root is your sandbox.

You can:
- Inspect/edit the project: read_file, list_dir, write_file, search_files, grep_content, git_status
- Take notes: write_note, list_notes, read_note
- Draft messages: draft_email, draft_telegram, draft_whatsapp, list_drafts, read_draft
- Make slides: make_markdown_deck, make_pptx, list_presentations
- Search the web: web_search, fetch_url
- Send (only when allowed): send_email, send_telegram

Rules:
- CALL tools; do NOT paste fake tool JSON in markdown or say "I will run X".
- Prefer draft_* over send_* for emails and messages unless the user explicitly asks to send.
- Use paths relative to the workspace root for file tools.
- After using tools, give a short final answer.
- If a tool fails, try another approach."""


@dataclass
class AgentEvent:
    kind: Literal["thinking", "tool_start", "tool_end", "error"]
    tool_name: str | None = None
    detail: str | None = None
    tool_result: str | None = None


EventCallback = Callable[[AgentEvent], None]


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


def _native_tool_calls(message: dict) -> list[dict]:
    calls: list[dict] = []
    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        name = fn.get("name") or ""
        if name:
            calls.append({"name": name, "arguments": _parse_arguments(fn.get("arguments"))})
    return calls


class Agent:
    def __init__(
        self,
        model: str,
        root: Path,
        allow_shell: bool,
        allow_write: bool,
        max_steps: int,
        host: str,
        allow_send: bool = False,
        on_event: EventCallback | None = None,
    ) -> None:
        self.model = model
        self.root = root.resolve()
        self.allow_shell = allow_shell
        self.allow_write = allow_write
        self.allow_send = allow_send
        self.max_steps = max_steps
        self.host = host
        self.on_event = on_event
        self._runner = ToolRunner(
            root,
            allow_shell=allow_shell,
            allow_write=allow_write,
            allow_send=allow_send,
        )
        self.messages: list[dict] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nWorkspace: {self.root}"}
        ]

    def reset(self) -> None:
        self.messages = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nWorkspace: {self.root}"}
        ]

    def _emit(self, event: AgentEvent) -> None:
        if self.on_event:
            self.on_event(event)

    def _execute_tools(self, calls: list[dict]) -> None:
        for call in calls:
            name = call["name"]
            arguments = call.get("arguments") or {}
            args_preview = json.dumps(arguments, ensure_ascii=False)
            if len(args_preview) > 160:
                args_preview = args_preview[:157] + "..."
            self._emit(
                AgentEvent(kind="tool_start", tool_name=name, detail=args_preview)
            )
            result = self._runner.run(name, arguments)
            preview = result.strip()
            if len(preview) > 300:
                preview = preview[:297] + "..."
            self._emit(
                AgentEvent(
                    kind="tool_end",
                    tool_name=name,
                    tool_result=result,
                    detail=preview,
                )
            )
            self.messages.append(
                {"role": "tool", "content": result, "tool_name": name}
            )

    def ask(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        tools = self._runner.schemas()

        for step in range(self.max_steps):
            self._emit(
                AgentEvent(
                    kind="thinking",
                    detail=f"step {step + 1}/{self.max_steps} — calling model",
                )
            )
            response = ollama.chat(
                self.messages,
                model=self.model,
                tools=tools,
                host=self.host,
            )
            message = response.get("message") or {}
            content = (message.get("content") or "").strip()
            calls = _native_tool_calls(message)

            if not calls and content:
                calls = extract_text_tool_calls(content)

            if calls:
                if message.get("tool_calls"):
                    self.messages.append(message)
                elif content:
                    self.messages.append({"role": "assistant", "content": content})
                self._execute_tools(calls)
                continue

            if content:
                self.messages.append({"role": "assistant", "content": content})
                return content

            return "(empty response from model)"

        msg = f"Error: exceeded maximum tool steps ({self.max_steps})"
        self._emit(AgentEvent(kind="error", detail=msg))
        return msg

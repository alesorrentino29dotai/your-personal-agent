from __future__ import annotations

import os
import time
from pathlib import Path

import httpx

from qagent.agent import Agent
from qagent.skills import telegram as tg

_TG_API_BASE = "https://api.telegram.org"


def _send_chat_action(chat_id: int, action: str = "typing") -> None:
    token = os.environ.get("QAGENT_TG_BOT_TOKEN")
    if not token:
        return
    url = f"{_TG_API_BASE}/bot{token.strip()}/sendChatAction"
    try:
        httpx.post(
            url,
            json={"chat_id": chat_id, "action": action},
            timeout=5.0,
        )
    except httpx.HTTPError:
        return


def _format_allowed(ids: set[int]) -> str:
    if not ids:
        return "(none — set QAGENT_TG_ALLOWED_CHATS)"
    return ", ".join(str(i) for i in sorted(ids))


def run_bot(
    model: str,
    root: Path,
    allow_write: bool,
    allow_shell: bool,
    host: str,
    max_steps: int,
) -> None:
    if not tg.is_configured():
        print(
            "Error: Telegram bot is not configured. "
            "Set QAGENT_TG_BOT_TOKEN (and QAGENT_TG_ALLOWED_CHATS) and try again."
        )
        return

    allowed = tg.allowed_chat_ids()
    print(
        f"Bot is listening. Allowed chats: {_format_allowed(allowed)}. "
        "Press Ctrl+C to stop."
    )
    if not allowed:
        print(
            "Warning: QAGENT_TG_ALLOWED_CHATS is empty — all incoming messages "
            "will be ignored."
        )

    resolved_root = root.resolve()
    agents: dict[int, Agent] = {}
    warned_chats: set[int] = set()
    last_offset: int | None = None

    try:
        while True:
            offset = last_offset + 1 if last_offset is not None else None
            updates = tg.get_updates(offset=offset, timeout=25)

            if not updates:
                time.sleep(0.5)
                continue

            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    last_offset = (
                        update_id
                        if last_offset is None or update_id > last_offset
                        else last_offset
                    )

                message = update.get("message") or {}
                text = message.get("text")
                chat = message.get("chat") or {}
                chat_id = chat.get("id")

                if not isinstance(text, str) or not isinstance(chat_id, int):
                    continue

                if chat_id not in tg.allowed_chat_ids():
                    if chat_id not in warned_chats:
                        warned_chats.add(chat_id)
                        print(f"Ignoring message from disallowed chat {chat_id}")
                    continue

                _send_chat_action(chat_id, "typing")

                agent = agents.get(chat_id)
                if agent is None:
                    agent = Agent(
                        model=model,
                        root=resolved_root,
                        allow_shell=allow_shell,
                        allow_write=allow_write,
                        max_steps=max_steps,
                        host=host,
                    )
                    agents[chat_id] = agent

                try:
                    reply = agent.ask(text)
                except Exception as exc:
                    reply = f"Error: agent failed: {exc}"

                if not reply:
                    reply = "(empty response)"

                send_result = tg.send_telegram(reply, chat=str(chat_id))
                if send_result.startswith("Error:"):
                    print(f"Failed to reply to chat {chat_id}: {send_result}")
    except KeyboardInterrupt:
        print("\nStopping bot.")

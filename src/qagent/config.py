from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    model: str = "qwen2.5:3b-instruct"
    root: Path = field(default_factory=Path.cwd)
    allow_shell: bool = False
    allow_write: bool = True
    allow_send: bool = False
    max_steps: int = 12
    verbose: bool = False
    host: str | None = None


def load_config(start: Path | None = None) -> AgentConfig:
    """Load optional `.qagent.json` from cwd (walk up one level max)."""
    cfg = AgentConfig()
    search_from = (start or Path.cwd()).resolve()
    candidates = [search_from / ".qagent.json", search_from.parent / ".qagent.json"]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("model"), str):
            cfg.model = data["model"]
        if isinstance(data.get("root"), str):
            cfg.root = Path(data["root"]).expanduser()
        if isinstance(data.get("allow_shell"), bool):
            cfg.allow_shell = data["allow_shell"]
        if isinstance(data.get("allow_write"), bool):
            cfg.allow_write = data["allow_write"]
        if isinstance(data.get("allow_send"), bool):
            cfg.allow_send = data["allow_send"]
        if isinstance(data.get("max_steps"), int):
            cfg.max_steps = data["max_steps"]
        if isinstance(data.get("verbose"), bool):
            cfg.verbose = data["verbose"]
        if isinstance(data.get("host"), str):
            cfg.host = data["host"]
        break
    return cfg

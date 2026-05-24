from __future__ import annotations

import subprocess
from pathlib import Path

_MAX_TEXT = 32_000
_MAX_SHELL_OUTPUT = 32_000


def _resolve_in_root(root: Path, path: str) -> Path:
    root_resolved = root.resolve()
    target = (root_resolved / path).resolve()
    if not target.is_relative_to(root_resolved):
        raise ValueError(f"path escapes sandbox: {path!r}")
    return target


def _truncate(text: str, limit: int = _MAX_TEXT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [{len(text) - limit} chars truncated]"


def _read_file(root: Path, path: str) -> str:
    target = _resolve_in_root(root, path)
    if not target.is_file():
        raise FileNotFoundError(f"not a file: {path}")
    return _truncate(target.read_text(encoding="utf-8", errors="replace"))


def _list_dir(root: Path, path: str = ".") -> str:
    target = _resolve_in_root(root, path)
    if not target.is_dir():
        raise NotADirectoryError(f"not a directory: {path}")
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = []
    for entry in entries:
        suffix = "/" if entry.is_dir() else ""
        lines.append(entry.name + suffix)
    return "\n".join(lines) if lines else "(empty)"


def _run_shell(root: Path, command: str) -> str:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=root,
            timeout=60,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 60s"
    parts: list[str] = []
    if completed.stdout:
        parts.append(completed.stdout)
    if completed.stderr:
        parts.append(completed.stderr)
    output = "".join(parts) if parts else "(no output)"
    if completed.returncode != 0:
        output = f"exit code {completed.returncode}\n{output}"
    return _truncate(output, _MAX_SHELL_OUTPUT)


def schemas(allow_shell: bool = False) -> list[dict]:
    tools: list[dict] = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file under the workspace root.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path relative to the workspace root.",
                        }
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files and directories under a path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path relative to the workspace root.",
                            "default": ".",
                        }
                    },
                },
            },
        },
    ]
    if allow_shell:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": "run_shell",
                    "description": "Run a shell command in the workspace root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute.",
                            }
                        },
                        "required": ["command"],
                    },
                },
            }
        )
    return tools


class ToolRunner:
    def __init__(self, root: Path, allow_shell: bool = False) -> None:
        self.root = root.resolve()
        self.allow_shell = allow_shell

    def schemas(self, allow_shell: bool | None = None) -> list[dict]:
        flag = self.allow_shell if allow_shell is None else allow_shell
        return schemas(flag)

    def run(self, name: str, arguments: dict) -> str:
        try:
            if name == "read_file":
                path = arguments.get("path")
                if not isinstance(path, str):
                    return "Error: read_file requires string path"
                return _read_file(self.root, path)
            if name == "list_dir":
                path = arguments.get("path", ".")
                if not isinstance(path, str):
                    return "Error: list_dir path must be a string"
                return _list_dir(self.root, path)
            if name == "run_shell":
                if not self.allow_shell:
                    return "Error: shell execution is disabled"
                command = arguments.get("command")
                if not isinstance(command, str):
                    return "Error: run_shell requires string command"
                return _run_shell(self.root, command)
            return f"Error: unknown tool {name!r}"
        except (OSError, ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return f"Error: {exc}"

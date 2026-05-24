from __future__ import annotations

import re
import subprocess
from pathlib import Path

from qagent import skills

_MAX_TEXT = 32_000
_MAX_SHELL_OUTPUT = 32_000
_MAX_SEARCH_HITS = 40
_MAX_GREP_HITS = 40


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


def _write_file(root: Path, path: str, content: str) -> str:
    target = _resolve_in_root(root, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} bytes to {path}"


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


def _search_files(root: Path, pattern: str, path: str = ".") -> str:
    target = _resolve_in_root(root, path)
    if not target.is_dir():
        raise NotADirectoryError(f"not a directory: {path}")
    hits: list[str] = []
    for match in target.rglob(pattern):
        if not match.is_file():
            continue
        rel = match.relative_to(root.resolve()).as_posix()
        hits.append(rel)
        if len(hits) >= _MAX_SEARCH_HITS:
            hits.append(f"... (stopped at {_MAX_SEARCH_HITS} matches)")
            break
    return "\n".join(hits) if hits else "(no matches)"


def _grep_content(root: Path, pattern: str, path: str = ".") -> str:
    target = _resolve_in_root(root, path)
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"
    hits: list[str] = []
    files = [target] if target.is_file() else sorted(target.rglob("*"))
    for file_path in files:
        if not file_path.is_file():
            continue
        if file_path.suffix in {".pyc", ".png", ".jpg", ".gif"}:
            continue
        if any(part.startswith(".") and part not in {".", ".."} for part in file_path.parts):
            if file_path.name not in {".gitignore", ".qagent.json"}:
                continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = file_path.relative_to(root.resolve())
        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel}:{line_no}: {line.strip()[:200]}")
                if len(hits) >= _MAX_GREP_HITS:
                    hits.append(f"... (stopped at {_MAX_GREP_HITS} matches)")
                    return "\n".join(hits)
    return "\n".join(hits) if hits else "(no matches)"


def _git_status(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "Error: git not installed"
    except subprocess.TimeoutExpired:
        return "Error: git status timed out"
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0 and not output.strip():
        return f"Error: git status failed (exit {completed.returncode})"
    return _truncate(output.strip() or "(clean)")


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


def schemas(
    allow_shell: bool = False,
    allow_write: bool = True,
    allow_send: bool = False,
) -> list[dict]:
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
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Glob search for files under a directory (e.g. pattern **/*.py).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern such as **/*.py or *.md",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory to search from",
                            "default": ".",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_content",
                "description": "Search file contents with a regex under a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regex pattern to search for in file contents.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Directory or file to search",
                            "default": ".",
                        },
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "git_status",
                "description": "Show git status for the workspace (short format).",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]
    if allow_write:
        tools.insert(
            1,
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a text file under the workspace root.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
        )
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
    tools.extend(skills.all_schemas(allow_send=allow_send))
    return tools


class ToolRunner:
    def __init__(
        self,
        root: Path,
        allow_shell: bool = False,
        allow_write: bool = True,
        allow_send: bool = False,
    ) -> None:
        self.root = root.resolve()
        self.allow_shell = allow_shell
        self.allow_write = allow_write
        self.allow_send = allow_send

    def schemas(self) -> list[dict]:
        return schemas(self.allow_shell, self.allow_write, self.allow_send)

    def run(self, name: str, arguments: dict) -> str:
        try:
            if name == "read_file":
                path = arguments.get("path")
                if not isinstance(path, str):
                    return "Error: read_file requires string path"
                return _read_file(self.root, path)
            if name == "write_file":
                if not self.allow_write:
                    return "Error: write_file is disabled (read-only mode)"
                path = arguments.get("path")
                content = arguments.get("content")
                if not isinstance(path, str) or not isinstance(content, str):
                    return "Error: write_file requires path and content strings"
                return _write_file(self.root, path, content)
            if name == "list_dir":
                path = arguments.get("path", ".")
                if not isinstance(path, str):
                    return "Error: list_dir path must be a string"
                return _list_dir(self.root, path)
            if name == "search_files":
                pattern = arguments.get("pattern")
                path = arguments.get("path", ".")
                if not isinstance(pattern, str):
                    return "Error: search_files requires string pattern"
                if not isinstance(path, str):
                    return "Error: search_files path must be a string"
                return _search_files(self.root, pattern, path)
            if name == "grep_content":
                pattern = arguments.get("pattern")
                path = arguments.get("path", ".")
                if not isinstance(pattern, str):
                    return "Error: grep_content requires string pattern"
                if not isinstance(path, str):
                    return "Error: grep_content path must be a string"
                return _grep_content(self.root, pattern, path)
            if name == "git_status":
                return _git_status(self.root)
            if name == "run_shell":
                if not self.allow_shell:
                    return "Error: shell execution is disabled"
                command = arguments.get("command")
                if not isinstance(command, str):
                    return "Error: run_shell requires string command"
                return _run_shell(self.root, command)
            skill_result = skills.dispatch(name, arguments, allow_send=self.allow_send)
            if skill_result is not None:
                return skill_result
            return f"Error: unknown tool {name!r}"
        except (OSError, ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return f"Error: {exc}"

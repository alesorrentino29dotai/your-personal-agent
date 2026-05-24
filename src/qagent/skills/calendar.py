from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

_STORAGE_ROOT = Path.home() / "qagent-data" / "calendar"
_TASKS_FILE = _STORAGE_ROOT / "tasks.json"
_EVENTS_FILE = _STORAGE_ROOT / "events.json"

_PRIORITIES = ("low", "med", "high")
_PRIORITY_RANK = {"high": 0, "med": 1, "low": 2}
_PRIORITY_TAG = {"low": "L", "med": "M", "high": "H"}


def _ensure_dir() -> None:
    _STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save(path: Path, data: list[dict[str, Any]]) -> None:
    _ensure_dir()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _next_id(items: list[dict[str, Any]]) -> int:
    return max((int(item.get("id", 0)) for item in items), default=0) + 1


def _parse_due(due: str | None) -> str | None:
    if due is None or due == "":
        return None
    try:
        parsed = datetime.strptime(due, "%Y-%m-%d").date()
        return parsed.isoformat()
    except ValueError:
        return None


def _parse_when(when: str) -> datetime | None:
    candidates = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")
    for fmt in candidates:
        try:
            return datetime.strptime(when, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(when)
    except ValueError:
        return None


def _format_when(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _task_sort_key(task: dict[str, Any]) -> tuple[int, str, int]:
    due = task.get("due")
    due_key = due or "9999-99-99"
    has_due = 0 if due else 1
    prio = _PRIORITY_RANK.get(str(task.get("priority", "med")), 1)
    return (has_due, due_key, prio)


def _format_task(task: dict[str, Any]) -> str:
    prio = str(task.get("priority", "med"))
    tag = _PRIORITY_TAG.get(prio, "M")
    due = task.get("due")
    due_part = f"  (due {due})" if due else ""
    done_mark = " [done]" if task.get("done") else ""
    return f"#{task.get('id')} [{tag}] {task.get('text', '')}{due_part}{done_mark}"


def _format_event(event: dict[str, Any]) -> str:
    when = event.get("when", "")
    duration = event.get("duration_min", 0)
    title = event.get("title", "")
    return f"#{event.get('id')} {when} ({duration}m) {title}"


def _event_dt(event: dict[str, Any]) -> datetime:
    parsed = _parse_when(str(event.get("when", "")))
    return parsed if parsed is not None else datetime.max


def add_task(text: str, due: str | None = None, priority: str = "med") -> str:
    try:
        text = (text or "").strip()
        if not text:
            return "Error: task text cannot be empty"
        prio = priority.lower() if isinstance(priority, str) else "med"
        if prio not in _PRIORITIES:
            return f"Error: priority must be one of {', '.join(_PRIORITIES)}"
        due_norm: str | None = None
        if due:
            due_norm = _parse_due(due)
            if due_norm is None:
                return f"Error: invalid due date '{due}', expected YYYY-MM-DD"
        tasks = _load(_TASKS_FILE)
        task = {
            "id": _next_id(tasks),
            "text": text,
            "due": due_norm,
            "priority": prio,
            "done": False,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        tasks.append(task)
        _save(_TASKS_FILE, tasks)
        suffix = f" (due {due_norm})" if due_norm else ""
        return f"Added task #{task['id']}: {text}{suffix}"
    except OSError as exc:
        return f"Error: failed to add task: {exc}"


def list_tasks(scope: str = "open") -> str:
    try:
        scope = (scope or "open").lower()
        valid = {"open", "done", "all", "today", "overdue"}
        if scope not in valid:
            return f"Error: scope must be one of {', '.join(sorted(valid))}"
        tasks = _load(_TASKS_FILE)
        today = date.today().isoformat()
        filtered: list[dict[str, Any]]
        if scope == "open":
            filtered = [t for t in tasks if not t.get("done")]
        elif scope == "done":
            filtered = [t for t in tasks if t.get("done")]
        elif scope == "today":
            filtered = [t for t in tasks if not t.get("done") and t.get("due") == today]
        elif scope == "overdue":
            filtered = [
                t
                for t in tasks
                if not t.get("done") and t.get("due") and str(t.get("due")) < today
            ]
        else:
            filtered = list(tasks)
        if not filtered:
            return "(no tasks)"
        filtered.sort(key=_task_sort_key)
        return "\n".join(_format_task(t) for t in filtered)
    except OSError as exc:
        return f"Error: failed to list tasks: {exc}"


def complete_task(task_id: int) -> str:
    try:
        try:
            tid = int(task_id)
        except (TypeError, ValueError):
            return f"Error: invalid task id '{task_id}'"
        tasks = _load(_TASKS_FILE)
        for task in tasks:
            if int(task.get("id", -1)) == tid:
                if task.get("done"):
                    return f"Task #{tid} already complete"
                task["done"] = True
                _save(_TASKS_FILE, tasks)
                return f"Completed task #{tid}: {task.get('text', '')}"
        return f"Error: task #{tid} not found"
    except OSError as exc:
        return f"Error: failed to complete task: {exc}"


def delete_task(task_id: int) -> str:
    try:
        try:
            tid = int(task_id)
        except (TypeError, ValueError):
            return f"Error: invalid task id '{task_id}'"
        tasks = _load(_TASKS_FILE)
        for i, task in enumerate(tasks):
            if int(task.get("id", -1)) == tid:
                removed = tasks.pop(i)
                _save(_TASKS_FILE, tasks)
                return f"Deleted task #{tid}: {removed.get('text', '')}"
        return f"Error: task #{tid} not found"
    except OSError as exc:
        return f"Error: failed to delete task: {exc}"


def add_event(title: str, when: str, duration_min: int = 60, notes: str = "") -> str:
    try:
        title = (title or "").strip()
        if not title:
            return "Error: event title cannot be empty"
        parsed = _parse_when(when or "")
        if parsed is None:
            return f"Error: invalid when '{when}', expected YYYY-MM-DD HH:MM or ISO"
        try:
            duration = int(duration_min)
        except (TypeError, ValueError):
            return f"Error: invalid duration_min '{duration_min}'"
        if duration <= 0:
            return "Error: duration_min must be positive"
        events = _load(_EVENTS_FILE)
        event = {
            "id": _next_id(events),
            "title": title,
            "when": _format_when(parsed),
            "duration_min": duration,
            "notes": notes or "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        events.append(event)
        _save(_EVENTS_FILE, events)
        return f"Added event #{event['id']}: {title} at {event['when']} ({duration}m)"
    except OSError as exc:
        return f"Error: failed to add event: {exc}"


def list_events(scope: str = "upcoming") -> str:
    try:
        scope = (scope or "upcoming").lower()
        valid = {"today", "upcoming", "week", "all"}
        if scope not in valid:
            return f"Error: scope must be one of {', '.join(sorted(valid))}"
        events = _load(_EVENTS_FILE)
        now = datetime.now()
        today = now.date()
        end_of_week = today + timedelta(days=7)
        filtered: list[dict[str, Any]]
        if scope == "all":
            filtered = list(events)
        elif scope == "today":
            filtered = [e for e in events if _event_dt(e).date() == today]
        elif scope == "week":
            filtered = [e for e in events if today <= _event_dt(e).date() <= end_of_week]
        else:
            filtered = [e for e in events if _event_dt(e) >= now]
        if not filtered:
            return "(no events)"
        filtered.sort(key=_event_dt)
        return "\n".join(_format_event(e) for e in filtered)
    except OSError as exc:
        return f"Error: failed to list events: {exc}"


def agenda() -> str:
    try:
        tasks = _load(_TASKS_FILE)
        events = _load(_EVENTS_FILE)
        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        end_of_week = today + timedelta(days=7)
        today_iso = today.isoformat()

        today_events = sorted(
            (e for e in events if _event_dt(e).date() == today),
            key=_event_dt,
        )
        tomorrow_events = sorted(
            (e for e in events if _event_dt(e).date() == tomorrow),
            key=_event_dt,
        )
        week_events = sorted(
            (
                e
                for e in events
                if tomorrow < _event_dt(e).date() <= end_of_week
            ),
            key=_event_dt,
        )

        today_tasks = sorted(
            (
                t
                for t in tasks
                if not t.get("done")
                and t.get("due")
                and str(t.get("due")) <= today_iso
            ),
            key=_task_sort_key,
        )

        lines: list[str] = ["Today:"]
        if today_events:
            lines.extend(_format_event(e) for e in today_events)
        if today_tasks:
            lines.extend(_format_task(t) for t in today_tasks)
        if not today_events and not today_tasks:
            lines.append("(nothing)")

        lines.append("")
        lines.append("Tomorrow:")
        if tomorrow_events:
            lines.extend(_format_event(e) for e in tomorrow_events)
        else:
            lines.append("(nothing)")

        lines.append("")
        lines.append("This week:")
        if week_events:
            lines.extend(_format_event(e) for e in week_events)
        else:
            lines.append("(nothing)")

        return "\n".join(lines)
    except OSError as exc:
        return f"Error: failed to build agenda: {exc}"


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": "Add a to-do task with optional due date (YYYY-MM-DD) and priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Task description.",
                    },
                    "due": {
                        "type": "string",
                        "description": "Optional due date in YYYY-MM-DD format.",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "med", "high"],
                        "description": "Task priority. Defaults to 'med'.",
                    },
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "List tasks filtered by scope. Sorted by due date then priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["open", "done", "all", "today", "overdue"],
                        "description": "Which tasks to show. Defaults to 'open'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task complete by its numeric id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Numeric task id from list_tasks.",
                    }
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task permanently by its numeric id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Numeric task id from list_tasks.",
                    }
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_event",
            "description": "Add a calendar event with title, when (YYYY-MM-DD HH:MM or ISO), duration in minutes, and optional notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title.",
                    },
                    "when": {
                        "type": "string",
                        "description": "Event start time as 'YYYY-MM-DD HH:MM' or ISO 8601.",
                    },
                    "duration_min": {
                        "type": "integer",
                        "description": "Duration in minutes. Defaults to 60.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional free-form notes.",
                    },
                },
                "required": ["title", "when"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "List calendar events filtered by scope. Sorted by start time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["today", "upcoming", "week", "all"],
                        "description": "Which events to show. Defaults to 'upcoming'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agenda",
            "description": "Show today's events and due/overdue tasks, tomorrow's events, and this week's remaining events.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    if name == "add_task":
        text = args.get("text")
        if not isinstance(text, str):
            return "Error: add_task requires string text"
        due = args.get("due")
        if due is not None and not isinstance(due, str):
            return "Error: add_task due must be a string"
        priority = args.get("priority", "med")
        if not isinstance(priority, str):
            return "Error: add_task priority must be a string"
        return add_task(text, due, priority)
    if name == "list_tasks":
        scope = args.get("scope", "open")
        if not isinstance(scope, str):
            return "Error: list_tasks scope must be a string"
        return list_tasks(scope)
    if name == "complete_task":
        return complete_task(args.get("task_id"))
    if name == "delete_task":
        return delete_task(args.get("task_id"))
    if name == "add_event":
        title = args.get("title")
        when = args.get("when")
        if not isinstance(title, str) or not isinstance(when, str):
            return "Error: add_event requires string title and when"
        duration = args.get("duration_min", 60)
        notes = args.get("notes", "")
        if not isinstance(notes, str):
            return "Error: add_event notes must be a string"
        return add_event(title, when, duration, notes)
    if name == "list_events":
        scope = args.get("scope", "upcoming")
        if not isinstance(scope, str):
            return "Error: list_events scope must be a string"
        return list_events(scope)
    if name == "agenda":
        return agenda()
    return None

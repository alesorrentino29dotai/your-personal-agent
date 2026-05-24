from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from qagent.agent import Agent, AgentEvent
from qagent.config import AgentConfig, load_config
from qagent.ollama import check_ollama, has_model, list_models

app = typer.Typer(help="Local Qwen2.5 agent CLI powered by Ollama.")
console = Console()

DEFAULT_MODEL = "qwen2.5:3b-instruct"
DEFAULT_HOST = "127.0.0.1:11434"


def resolve_host(host: str | None) -> str:
    raw = host or os.environ.get("OLLAMA_HOST", DEFAULT_HOST)
    raw = raw.rstrip("/")
    if raw.startswith(("http://", "https://")):
        return raw
    return f"http://{raw}"


def _make_event_handler(verbose: bool):
    def on_event(event: AgentEvent) -> None:
        if not verbose:
            return
        if event.kind == "thinking":
            console.print(f"[dim]… {event.detail}[/dim]")
        elif event.kind == "tool_start":
            args = f" {event.detail}" if event.detail else ""
            console.print(f"[cyan]→ {event.tool_name}{args}[/cyan]")
        elif event.kind == "tool_end":
            preview = event.detail or event.tool_result
            console.print(f"[dim]  ↳ {preview}[/dim]")
        elif event.kind == "error":
            console.print(f"[red]{event.detail}[/red]")

    return on_event


def _make_agent(
    model: str,
    root: Path,
    allow_shell: bool,
    allow_write: bool,
    allow_send: bool,
    max_steps: int,
    host: str | None,
    verbose: bool,
) -> Agent:
    return Agent(
        model=model,
        root=root.resolve(),
        allow_shell=allow_shell,
        allow_write=allow_write,
        allow_send=allow_send,
        max_steps=max_steps,
        host=resolve_host(host),
        on_event=_make_event_handler(verbose),
    )


def _resolve_options(
    model: str | None,
    root: Path | None,
    allow_shell: bool | None,
    allow_write: bool | None,
    allow_send: bool | None,
    max_steps: int | None,
    host: str | None,
    verbose: bool | None,
) -> AgentConfig:
    cfg = load_config()
    if model is not None:
        cfg.model = model
    if root is not None:
        cfg.root = root
    if allow_shell is not None:
        cfg.allow_shell = allow_shell
    if allow_write is not None:
        cfg.allow_write = allow_write
    if allow_send is not None:
        cfg.allow_send = allow_send
    if max_steps is not None:
        cfg.max_steps = max_steps
    if host is not None:
        cfg.host = host
    if verbose is not None:
        cfg.verbose = verbose
    return cfg


def _print_agent_banner(cfg: AgentConfig) -> None:
    flags = []
    if cfg.allow_write:
        flags.append("write")
    if cfg.allow_shell:
        flags.append("shell")
    if cfg.allow_send:
        flags.append("send")
    enabled = ", ".join(flags) if flags else "read-only"
    console.print(
        f"[bold]Agent[/bold] model=[cyan]{cfg.model}[/cyan] "
        f"root=[cyan]{cfg.root.resolve()}[/cyan] tools=[cyan]{enabled}[/cyan]"
    )
    console.print(
        "[dim]Give a task in plain English. The agent will read files, edit code, "
        "and optionally run shell commands.[/dim]"
    )
    console.print(
        "[dim]Commands: /reset, /help, exit. Use --verbose to see tool calls.[/dim]"
    )


def _run_interactive(agent: Agent, cfg: AgentConfig) -> None:
    _print_agent_banner(cfg)
    while True:
        try:
            line = input("you> ").strip()
        except EOFError:
            console.print()
            break
        except KeyboardInterrupt:
            console.print()
            continue

        if not line:
            continue
        lowered = line.lower()
        if lowered in ("exit", "quit", "q"):
            break
        if line == "/reset":
            agent.reset()
            console.print("[dim]Conversation history cleared.[/dim]")
            continue
        if line == "/help":
            console.print(
                "[dim]Examples:\n"
                "  Explain how src/qagent/agent.py works\n"
                "  Add a --version flag to the CLI\n"
                "  Find all TODO comments in this repo\n"
                "  Run tests and fix failures[/dim]"
            )
            continue

        try:
            reply = agent.ask(line)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            continue

        console.print(f"\n[green]{reply}[/green]\n")


@app.command()
def doctor(
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Ollama model tag to check."),
    host: str | None = typer.Option(
        None,
        "--host",
        help="Ollama base URL (default: OLLAMA_HOST env or 127.0.0.1:11434).",
    ),
) -> None:
    """Check Ollama connectivity and list installed models."""
    resolved = resolve_host(host)
    try:
        check_ollama(resolved)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]Ollama is reachable at {resolved}[/green]")

    models = list_models(resolved)
    table = Table(title="Installed models")
    table.add_column("Name", style="cyan")
    for name in models:
        table.add_row(name)
    if models:
        console.print(table)
    else:
        console.print("[yellow]No models installed yet.[/yellow]")

    if not has_model(model, resolved):
        console.print(
            f"[yellow]Model [bold]{model}[/bold] is not installed. "
            f"Run:[/yellow] [bold]ollama pull {model}[/bold]"
        )
        raise typer.Exit(1)

    console.print(f"[green]Model [bold]{model}[/bold] is available.[/green]")


@app.command()
def agent(
    model: str | None = typer.Option(None, "--model"),
    root: Path | None = typer.Option(
        None,
        "--root",
        help="Project root for file tools (sandbox).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    allow_shell: bool | None = typer.Option(
        None,
        "--allow-shell",
        help="Enable run_shell tool (commands run in cwd).",
    ),
    allow_write: bool | None = typer.Option(
        None,
        "--allow-write/--no-write",
        help="Allow write_file tool (default: on).",
    ),
    allow_send: bool | None = typer.Option(
        None,
        "--allow-send",
        help="Allow send_email and send_telegram (off by default).",
    ),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show tool calls."),
) -> None:
    """Run the personal local agent (interactive REPL)."""
    cfg = _resolve_options(
        model, root, allow_shell, allow_write, allow_send, max_steps, host, verbose
    )
    try:
        check_ollama(resolve_host(cfg.host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    agent_obj = _make_agent(
        cfg.model,
        cfg.root,
        cfg.allow_shell,
        cfg.allow_write,
        cfg.allow_send,
        cfg.max_steps,
        cfg.host,
        cfg.verbose,
    )
    _run_interactive(agent_obj, cfg)


@app.command()
def chat(
    model: str | None = typer.Option(None, "--model"),
    root: Path | None = typer.Option(
        None,
        "--root",
        help="Project root for file tools (sandbox).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    allow_shell: bool | None = typer.Option(None, "--allow-shell"),
    allow_write: bool | None = typer.Option(None, "--allow-write/--no-write"),
    allow_send: bool | None = typer.Option(None, "--allow-send"),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Alias for `qagent agent`."""
    agent(
        model=model,
        root=root,
        allow_shell=allow_shell,
        allow_write=allow_write,
        allow_send=allow_send,
        max_steps=max_steps,
        host=host,
        verbose=verbose,
    )


@app.command()
def run(
    text: str = typer.Argument(..., help="Task for the agent."),
    model: str | None = typer.Option(None, "--model"),
    root: Path | None = typer.Option(
        None,
        "--root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    allow_shell: bool | None = typer.Option(None, "--allow-shell"),
    allow_write: bool | None = typer.Option(None, "--allow-write/--no-write"),
    allow_send: bool | None = typer.Option(None, "--allow-send"),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run a single agent task and print the reply."""
    cfg = _resolve_options(
        model, root, allow_shell, allow_write, allow_send, max_steps, host, verbose
    )
    try:
        check_ollama(resolve_host(cfg.host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    agent_obj = _make_agent(
        cfg.model,
        cfg.root,
        cfg.allow_shell,
        cfg.allow_write,
        cfg.allow_send,
        cfg.max_steps,
        cfg.host,
        True,
    )
    try:
        reply = agent_obj.ask(text)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]{reply}[/green]")


@app.command()
def voice(
    model: str | None = typer.Option(None, "--model"),
    root: Path | None = typer.Option(
        None, "--root", exists=True, file_okay=False, dir_okay=True, resolve_path=True
    ),
    allow_shell: bool | None = typer.Option(None, "--allow-shell"),
    allow_write: bool | None = typer.Option(None, "--allow-write/--no-write"),
    allow_send: bool | None = typer.Option(None, "--allow-send"),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
    seconds: float = typer.Option(8.0, "--seconds", help="Recording length per turn."),
    voice_name: str = typer.Option(
        "en-US-AriaNeural", "--voice", help="edge-tts voice (e.g. it-IT-IsabellaNeural)."
    ),
) -> None:
    """Talk to the agent using your microphone (requires .[voice] extras)."""
    from qagent import voice as voice_mod

    cfg = _resolve_options(
        model, root, allow_shell, allow_write, allow_send, max_steps, host, True
    )
    try:
        check_ollama(resolve_host(cfg.host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    agent_obj = _make_agent(
        cfg.model,
        cfg.root,
        cfg.allow_shell,
        cfg.allow_write,
        cfg.allow_send,
        cfg.max_steps,
        cfg.host,
        False,
    )
    try:
        voice_mod.run_voice_loop(agent_obj, seconds=seconds, voice=voice_name)
    except voice_mod.VoiceDepsMissing as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@app.command()
def bot(
    model: str | None = typer.Option(None, "--model"),
    root: Path | None = typer.Option(
        None, "--root", exists=True, file_okay=False, dir_okay=True, resolve_path=True
    ),
    allow_shell: bool | None = typer.Option(None, "--allow-shell"),
    allow_write: bool | None = typer.Option(None, "--allow-write/--no-write"),
    max_steps: int | None = typer.Option(None, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
) -> None:
    """Run the Telegram bot so you can chat with the agent from your phone."""
    from qagent.bot import run_bot

    cfg = _resolve_options(
        model, root, allow_shell, allow_write, None, max_steps, host, False
    )
    try:
        check_ollama(resolve_host(cfg.host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    run_bot(
        model=cfg.model,
        root=cfg.root,
        allow_write=cfg.allow_write,
        allow_shell=cfg.allow_shell,
        host=resolve_host(cfg.host),
        max_steps=cfg.max_steps,
    )


if __name__ == "__main__":
    app()

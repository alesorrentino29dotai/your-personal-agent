from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from qagent.agent import Agent
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


def _make_agent(
    model: str,
    root: Path,
    allow_shell: bool,
    max_steps: int,
    host: str | None,
) -> Agent:
    return Agent(
        model=model,
        root=root.resolve(),
        allow_shell=allow_shell,
        max_steps=max_steps,
        host=resolve_host(host),
    )


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
def chat(
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    root: Path = typer.Option(
        Path.cwd(),
        "--root",
        help="Project root for file tools (sandbox).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    allow_shell: bool = typer.Option(
        False,
        "--allow-shell",
        help="Enable run_shell tool (commands run in cwd).",
    ),
    max_steps: int = typer.Option(12, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
) -> None:
    """Interactive agent REPL."""
    try:
        check_ollama(resolve_host(host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    agent = _make_agent(model, root, allow_shell, max_steps, host)
    console.print(
        "[dim]Interactive agent. Commands: exit, quit, q, or Ctrl+D to leave; "
        "/reset clears history.[/dim]"
    )

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

        try:
            reply = agent.ask(line)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            continue

        console.print(f"[green]{reply}[/green]")


@app.command()
def run(
    text: str = typer.Argument(..., help="Question or task for the agent."),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
    root: Path = typer.Option(
        Path.cwd(),
        "--root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
    allow_shell: bool = typer.Option(False, "--allow-shell"),
    max_steps: int = typer.Option(12, "--max-steps", min=1),
    host: str | None = typer.Option(None, "--host"),
) -> None:
    """Run a single agent turn and print the reply."""
    try:
        check_ollama(resolve_host(host))
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    agent = _make_agent(model, root, allow_shell, max_steps, host)
    try:
        reply = agent.ask(text)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]{reply}[/green]")


if __name__ == "__main__":
    app()

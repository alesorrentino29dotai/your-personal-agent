# qwen-agent-cli

A local **coding agent** that runs **Qwen2.5** on your GPU through [Ollama](https://ollama.com). Good fit for an **RTX 3060 laptop (6 GB VRAM)** with `qwen2.5:3b-instruct`.

## What is this?

This is not just chat — it is an **agent loop**:

1. You give a task in plain English
2. The model decides which **tools** to call (`read_file`, `grep_files`, `write_file`, …)
3. Tool results go back to the model
4. It repeats until it produces a final answer

```
You → qagent agent → Ollama (Qwen2.5 on GPU)
                         ↓ tool calls
                    read / grep / write / shell
                         ↓
                    final answer
```

## Prerequisites

```bash
# Ollama (if not installed)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct
```

## Install

```bash
cd ~/Projects/qwen-agent-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Use it as an agent

```bash
# Check Ollama + model
qagent doctor

# Interactive coding agent (recommended)
qagent agent --verbose

# One-shot task (shows tool calls automatically)
qagent run "List the Python files and explain what each module does"

# Allow shell commands (tests, git, pip, …)
qagent agent --allow-shell --verbose

# Point at any project
qagent agent --root ~/Projects/my-app --verbose
```

### Example tasks

```text
you> Explain how src/qagent/agent.py works
you> Add a --version flag to the CLI
you> Find all functions named ask in this repo
you> Run the test suite and summarize failures   # needs --allow-shell
```

### REPL commands

| Command | Action |
|---------|--------|
| `/help` | Show example prompts |
| `/reset` | Clear conversation history |
| `exit` / `q` | Quit |

## Configuration

Optional `.qagent.json` in your project root:

```json
{
  "model": "qwen2.5:3b-instruct",
  "allow_write": true,
  "allow_shell": false,
  "max_steps": 12,
  "verbose": false
}
```

CLI flags override the config file.

## Tools

| Tool | Default | Description |
|------|---------|-------------|
| `read_file` | on | Read a file under `--root` |
| `list_dir` | on | List directory contents |
| `grep_content` | on | Regex search inside files |
| `search_files` | on | Glob find files (`**/*.py`) |
| `git_status` | on | Show git branch + changes |
| `write_file` | on | Create/overwrite files (`--no-write` to disable) |
| `run_shell` | off | Run shell commands (`--allow-shell` to enable) |

## Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--model` | `qwen2.5:3b-instruct` | Ollama model tag |
| `--root` | current directory | Sandbox for file tools |
| `--allow-shell` | off | Enable `run_shell` |
| `--allow-write` / `--no-write` | on | Enable `write_file` |
| `--max-steps` | `12` | Max tool rounds per turn |
| `--verbose` / `-v` | off | Show tool calls live |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach Ollama` | Run `ollama serve` or restart Ollama |
| `model not found` | `ollama pull qwen2.5:3b-instruct` |
| First reply very slow | Cold model load (~50s); then fast |
| Agent doesn't use tools | Try `--verbose`; use a clearer task like "read src/qagent/cli.py and …" |
| CUDA OOM | Stick to 3B model; close other GPU apps |

# qwen-agent-cli

A small terminal agent that runs **Qwen2.5** locally through [Ollama](https://ollama.com). Good fit for an RTX 3070 (8 GB VRAM): use the **7B instruct** model.

## Prerequisites

1. **NVIDIA driver** (you already have this if the 3070 works in games/CUDA).
2. **Ollama** — installs the runtime and pulls models.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct
```

Check the model:

```bash
ollama run qwen2.5:3b-instruct "Say hello in one sentence."
```

## Install the CLI

```bash
cd ~/Projects/qwen-agent-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Check Ollama + model
qagent doctor

# Interactive agent (tools: read/list files under project root)
qagent chat

# One-shot question
qagent run "Summarize what this repo does" 

# Allow shell tool (off by default — runs commands in your cwd)
qagent chat --allow-shell
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--model` | `qwen2.5:3b-instruct` | Ollama model tag |
| `--root` | current directory | Filesystem sandbox for file tools |
| `--allow-shell` | off | Enable `run_shell` tool |
| `--max-steps` | `12` | Max tool-call rounds per turn |

## How it works

```
You → qagent (Typer CLI) → Ollama API (localhost:11434)
                              ↓
                         Qwen2.5 7B on GPU
                              ↓
                    tool calls (read_file, list_dir, …)
                              ↓
                         back to model → answer
```

Ollama serves an OpenAI-style chat API. The agent loop sends your message, runs any tool calls the model requests, feeds results back, and repeats until the model replies with text only.

## Next steps (we can add together)

- [ ] Streaming tokens in the terminal
- [ ] `qagent.json` config (model, root, system prompt)
- [ ] More tools (web search, git status, HF Hub)
- [ ] Session memory saved to `~/.qagent/sessions/`
- [ ] 14B model with layer offload (slower, smarter)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach Ollama` | Run `ollama serve` or restart the Ollama app |
| `model not found` | `ollama pull qwen2.5:7b-instruct` |
| CUDA OOM | Use 7B + Q4 quant (Ollama default); close other GPU apps |
| Slow replies | Normal on first prompt (model load); 7B should be fast after |

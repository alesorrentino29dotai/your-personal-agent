# qwen-agent-cli

A personal **local agent** powered by **Qwen2.5** via [Ollama](https://ollama.com). It lives on your machine, uses your GPU, and can:

- Search and edit files in any folder
- Search the web and read pages
- Take notes
- Draft **emails**, **Telegram**, and **WhatsApp** messages
- Build **slide decks** (Markdown / `.pptx`)
- **Send** email and Telegram messages (gated, off by default)
- Talk to you with **voice** (Whisper STT + edge-tts)
- Listen on **Telegram** so you can chat with it from your iPhone

Tested on an **RTX 3060 Laptop (6 GB)** with `qwen2.5:3b-instruct`. No data leaves the machine except for web search, TTS, and Telegram (when you enable them).

## Install

```bash
# 1. Ollama + model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct

# 2. The CLI
cd ~/Projects/qwen-agent-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Optional extras
pip install -e ".[slides]"   # python-pptx
pip install -e ".[voice]"    # whisper + tts + sound
pip install -e ".[all]"      # everything
# Voice extras also need PortAudio: sudo apt install libportaudio2
```

## Use it

```bash
qagent doctor                    # check Ollama + model
qagent agent --verbose           # interactive agent
qagent run "Write a Python script that prints fibonacci"
qagent voice                     # talk to the agent
qagent bot                       # run Telegram bot (see Telegram setup below)
```

### Example tasks

```text
Take a note titled "groceries" with: milk, eggs, bread
Draft an email to marco@example.com about postponing Friday's call
Search the web for FastAPI streaming examples and save a note with 3 links
Make a 5-slide markdown deck about renewable energy
Find all TODO comments in this repo and list them
Read src/qagent/cli.py and add a --version flag
```

## Tools (19 + 2 gated)

| Category | Tools |
|----------|-------|
| Files | `read_file`, `write_file`, `list_dir`, `search_files`, `grep_content`, `git_status` |
| Notes | `write_note`, `list_notes`, `read_note` |
| Drafts | `draft_email`, `draft_telegram`, `draft_whatsapp`, `list_drafts`, `read_draft` |
| Web | `web_search`, `fetch_url` |
| Slides | `make_markdown_deck`, `make_pptx`, `list_presentations` |
| Shell | `run_shell` (`--allow-shell`) |
| Send | `send_email`, `send_telegram` (`--allow-send`) |

Data lives in `~/qagent-data/{notes,drafts,presentations}/`.

## Voice

```bash
pip install -e ".[voice]"
sudo apt install libportaudio2          # Linux only
qagent voice --voice it-IT-IsabellaNeural --seconds 6
```

Per turn: record 6–8 s → Whisper transcribes → Qwen replies → edge-tts speaks.

First run downloads the Whisper model (~150 MB, CPU). Audio runs on CPU so the GPU stays free for Qwen.

## Telegram bot (chat from your iPhone)

1. Open Telegram, talk to [@BotFather](https://t.me/BotFather): `/newbot`, follow prompts, copy the token.
2. Send your new bot any message.
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` and find your `chat.id`.
4. Copy `.env.example` to `.env` and fill in:

```bash
QAGENT_TG_BOT_TOKEN=123456:ABC...
QAGENT_TG_DEFAULT_CHAT=123456789
QAGENT_TG_ALLOWED_CHATS=123456789
```

5. Load env vars and run the bot:

```bash
set -a; source .env; set +a
qagent bot
```

Now message the bot from your iPhone Telegram app — the agent replies with the same tools as the CLI. Each chat keeps its own conversation history.

## Email setup (optional)

Add SMTP credentials to `.env` (Gmail App Password works):

```bash
QAGENT_SMTP_HOST=smtp.gmail.com
QAGENT_SMTP_PORT=587
QAGENT_SMTP_USER=you@example.com
QAGENT_SMTP_PASSWORD=your-app-password
```

Then:

```bash
set -a; source .env; set +a
qagent agent --allow-send
you> Send an email to marco@example.com saying I'll be 10 min late
```

Without `--allow-send`, the agent will only **draft** emails to `~/qagent-data/drafts/`.

## Config file (`.qagent.json`)

```json
{
  "model": "qwen2.5:3b-instruct",
  "allow_write": true,
  "allow_shell": false,
  "allow_send": false,
  "max_steps": 12,
  "verbose": false
}
```

CLI flags override the config file.

## Safety defaults

| Action | Default |
|--------|---------|
| Read files | on |
| Write files | on (`--no-write` to disable) |
| Shell commands | **off** (`--allow-shell`) |
| Send email/Telegram | **off** (`--allow-send`) |
| File access | only under `--root` |

Drafts are always saved locally first. The agent's system prompt instructs it to prefer `draft_*` over `send_*` unless you explicitly ask to send.

## Architecture

```
You (CLI / voice / Telegram)
    ↓
qagent.Agent  ──►  Ollama (Qwen2.5 on GPU)
    ↓
Tools: files, web, notes, drafts, slides, send, shell
```

The model decides which tool to call, gets the result, and loops until it produces a final reply (up to `--max-steps`).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach Ollama` | `ollama serve` or restart Ollama |
| Model misses tools | Try `--verbose` to see what's happening |
| Voice install fails | `sudo apt install libportaudio2 ffmpeg` |
| Bot doesn't reply | Check `QAGENT_TG_ALLOWED_CHATS` includes your chat id |
| Slow first reply | Cold model load (~30–50 s); fast after |
| CUDA OOM | Stick to 3B; close other GPU apps |

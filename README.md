# Your personal Agent is here!

A **local-first personal AI assistant**. The model runs on your **workstation / laptop GPU** (Qwen2.5 via [Ollama](https://ollama.com), or any OpenAI-compatible backend), and you reach it from:

- **CLI** on the same machine
- **Voice** with your microphone
- **Web app** on your phone or any laptop browser (same WiFi or via Tailscale)
- **Telegram bot** — chat with your agent from iPhone/Android, anywhere
- **iOS Siri Shortcut** — "Hey Siri, ask my agent"

It can read your files, take notes, draft & send emails, search the web, build slide decks and Word docs, manage tasks and a calendar, and run shell commands when you let it.

---

## What it does (29 tools, 5 model providers, 7 commands)

| Category | Tools |
|----------|-------|
| **Files** | `read_file`, `write_file`, `list_dir`, `search_files`, `grep_content`, `git_status` |
| **Notes** | `write_note`, `list_notes`, `read_note` |
| **Drafts** | `draft_email`, `draft_telegram`, `draft_whatsapp`, `list_drafts`, `read_draft` |
| **Web** | `web_search`, `fetch_url` |
| **Slides** | `make_markdown_deck`, `make_pptx`, `list_presentations` |
| **Documents** | `make_document` (md/docx/html), `list_documents`, `read_document` |
| **Calendar** | `add_task`, `list_tasks`, `complete_task`, `delete_task`, `add_event`, `list_events`, `agenda` |
| **Shell** | `run_shell` (gated by `--allow-shell`) |
| **Send** | `send_email`, `send_telegram` (gated by `--allow-send`) |

All your data lives under `~/qagent-data/` (notes, drafts, presentations, documents, calendar).

---

## Quick start

```bash
# 1. Local model (recommended)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct        # 6 GB VRAM (e.g. RTX 3060 laptop)
# or qwen2.5:7b-instruct on a bigger GPU

# 2. Install the agent
cd ~/Projects/your-personal-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"             # CLI + HTTP API + web UI
# pip install -e ".[all]"              # everything (voice, docx, slides)
```

```bash
# 3. Try it
qagent doctor                          # check Ollama + model
qagent agent --verbose                 # interactive REPL
qagent run "Add a task: pay rent (high priority, due Friday)"
qagent serve --port 8765               # start the web app (use from phone/laptop)
```

---

## Use it from your phone

### A. Web app on the same WiFi (zero config)

```bash
qagent serve --bind 0.0.0.0 --port 8765
```

- Find your workstation's LAN IP (`hostname -I`)
- On iPhone Safari / Android Chrome → `http://<LAN-IP>:8765`
- Tap **Share → Add to Home Screen** for a PWA-style icon

### B. Anywhere via Tailscale (recommended for remote use)

1. Install [Tailscale](https://tailscale.com/download) on workstation + phone, log into the same tailnet
2. Run `qagent serve` as usual
3. On the phone, open `http://<tailscale-ip>:8765` — works from anywhere, end-to-end encrypted

### C. Telegram bot (no port forwarding ever needed)

1. `@BotFather` → `/newbot` → copy token
2. Send your bot a message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your `chat.id`
3. Copy `.env.example` to `.env`, fill in `QAGENT_TG_*` vars
4. `set -a; source .env; set +a && qagent bot`
5. Message the bot from your iPhone — the agent replies. Each chat has its own history.

### D. Voice ("Hey Siri") via iOS Shortcut

Create an iOS Shortcut that POSTs `{"message": "<dictated>"}` to `http://<tailscale-ip>:8765/api/ask` and reads the `reply` field. Bind to "Hey Siri, ask my agent". See `deploy/PHONE_ACCESS.md`.

### E. Voice actions on iPhone (Telegram / Call / SMS / Calendar)

Four ready-made Siri Shortcut recipes turn your voice into iOS actions:

| Recipe | Shortcut | Result |
|--------|----------|--------|
| Telegram by voice | "Hey Siri, telegram message" | Opens Telegram with prefilled text, or sends via your bot |
| Call by voice | "Hey Siri, call contact" | Opens iOS Phone with the number ready |
| SMS by voice | "Hey Siri, send text" | iOS Messages opens prefilled (tap Send) |
| Add appointment | "Hey Siri, add appointment" | Adds event to iOS Calendar (no tap needed) |

Setup:

1. Edit `~/qagent-data/contacts.json` (template at `deploy/contacts.example.json`)
2. Build the 4 shortcuts following `deploy/IOS_SHORTCUTS.md` (step-by-step recipes in `deploy/shortcuts/`)
3. The shortcuts call `POST /api/intent/{telegram,call,sms,calendar}` on your workstation; the agent parses the transcript into clean JSON; the shortcut performs the iOS action.

**Telegram bot also accepts voice notes**: send a voice note to your bot from the Telegram app, it transcribes with Whisper, then the agent replies. (`pip install -e ".[voice]"` on the workstation first.)

Full phone-access guide → [`deploy/PHONE_ACCESS.md`](deploy/PHONE_ACCESS.md)
iOS Shortcuts guide → [`deploy/IOS_SHORTCUTS.md`](deploy/IOS_SHORTCUTS.md)

---

## Talk to it locally

```bash
pip install -e ".[voice]"
sudo apt install libportaudio2 ffmpeg
qagent voice --voice it-IT-IsabellaNeural
```

Per turn: record 6–8 s → Whisper transcribes → Qwen replies → edge-tts speaks. Whisper runs on CPU so the GPU stays free for Qwen.

---

## Send email + Telegram (gated)

```bash
# .env
QAGENT_SMTP_HOST=smtp.gmail.com
QAGENT_SMTP_USER=you@example.com
QAGENT_SMTP_PASSWORD=your-app-password
QAGENT_TG_BOT_TOKEN=...
QAGENT_TG_ALLOWED_CHATS=123456789
```

```bash
set -a; source .env; set +a
qagent agent --allow-send
you> Send an email to marco@example.com saying I'll be 10 min late
```

Without `--allow-send`, the agent always **drafts** to `~/qagent-data/drafts/` so you can review before sending.

---

## Pluggable model backend

Today: Ollama on your GPU. Tomorrow: bigger workstation, or an OpenAI-compatible endpoint — same config, no code change.

`.qagent.json` in any project root:

```json
{
  "provider": "ollama",
  "model": "qwen2.5:3b-instruct",
  "host": "http://127.0.0.1:11434",
  "allow_write": true,
  "allow_shell": false,
  "allow_send": false,
  "max_steps": 12
}
```

Supported providers:

| `provider` | What it talks to |
|------------|------------------|
| `ollama` | Local Ollama daemon (default) |
| `openai` / `openai-compat` | OpenAI API (`OPENAI_API_KEY`) |
| `vllm` | Self-hosted vLLM with `--host http://your-server:8000/v1` |
| `lmstudio` | LM Studio's local OpenAI-compatible server |

When you upgrade hardware, just bump the model:

```bash
qagent agent --model qwen2.5:14b-instruct        # bigger GPU
qagent agent --provider openai --model gpt-4o    # cloud fallback
```

---

## Auto-start on boot

```bash
chmod +x deploy/start-agent.sh
# Edit ~/.config/systemd/user/qagent.service (template in deploy/PHONE_ACCESS.md)
systemctl --user enable --now qagent
```

---

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CLI         │    │  Web (PWA)   │    │  Telegram    │
│  Voice       │    │  iOS / Mac   │    │  iPhone /    │
│  Shortcut    │    │  Android     │    │  Android     │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └─────── HTTP / stdin ─────┐  ┌── long-poll ──┘
                                  ▼  ▼
                          ┌────────────────────┐
                          │    qagent.Agent    │
                          │ provider + tools   │
                          └────────┬───────────┘
                                   │
       ┌───────────────────────────┼───────────────────────────┐
       ▼                           ▼                           ▼
 ┌──────────┐              ┌──────────────┐           ┌──────────────┐
 │ Ollama   │              │ Files, web,  │           │ OpenAI / vLLM│
 │ (Qwen GPU)│              │ notes, slides│           │ (optional)   │
 └──────────┘              │ calendar, …  │           └──────────────┘
                          └──────────────┘
```

The **model lives on your workstation** — your data stays local. Only outbound calls happen for: web search (DuckDuckGo), TTS (edge-tts → Microsoft), Telegram (your bot), and SMTP (your email server). All of those are off unless you turn them on.

---

## Safety defaults

| Action | Default | Toggle |
|--------|---------|--------|
| Read files | on | — |
| Write files | on | `--no-write` |
| Shell commands | **off** | `--allow-shell` |
| Send email / Telegram | **off** | `--allow-send` |
| File access | sandboxed to `--root` | — |
| HTTP API auth | open on LAN | `--api-token` (env `QAGENT_API_TOKEN`) |
| Telegram allowlist | deny-all | `QAGENT_TG_ALLOWED_CHATS` |

---

## Commands

| Command | What it does |
|---------|--------------|
| `qagent doctor` | Check provider + model availability |
| `qagent agent` | Interactive REPL (alias: `chat`) |
| `qagent run "..."` | One-shot task |
| `qagent voice` | Microphone → Whisper → agent → TTS speaker |
| `qagent serve` | HTTP API + mobile-friendly web UI |
| `qagent bot` | Telegram long-polling bot |

Each command accepts `--model`, `--root`, `--allow-shell`, `--allow-write/--no-write`, `--allow-send`, `--max-steps`, `--host`, `--verbose`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach Ollama` | `ollama serve` (or use `deploy/start-agent.sh`) |
| Web UI loads but `/api/ask` 500s | Cold model load (~30–50 s on first request); retry |
| Bot doesn't reply | Check your `chat.id` is in `QAGENT_TG_ALLOWED_CHATS` |
| Voice install fails | `sudo apt install libportaudio2 ffmpeg` |
| Phone can't reach LAN URL | Workstation firewall — open port 8765, or use Tailscale |
| CUDA OOM | Stick to 3B; close other GPU apps |

# Your personal Agent is here!

A **local-first personal AI assistant**. The model runs on your **workstation / laptop GPU** (Qwen2.5 via [Ollama](https://ollama.com), or any OpenAI-compatible backend), and you reach it from:

- **CLI** on the same machine
- **Voice** with your microphone (`qagent voice`)
- **Web app** on your phone or any laptop browser (same WiFi or Tailscale)
- **Telegram bot** — chat with your agent from iPhone/Android, including **voice notes**
- **iOS Shortcuts** — "Hey Siri, send a telegram / call / text / add appointment"

It can read your files, take notes, draft & send emails, search the web, build slide decks and Word docs, manage tasks and a calendar, transcribe voice, and trigger native iPhone actions — all driven by a small local LLM.

---

## Headline features

| | |
|---|---|
| 🧠 **Local model** | Qwen2.5 on your GPU via Ollama (3B fits on 6 GB; 7B/14B on bigger cards) |
| 🔌 **Pluggable backend** | `ollama`, `openai`, `openai-compat`, `vllm`, `lmstudio` — change with one config line |
| 🛠 **31 tools** | files, notes, drafts, web, slides, documents, calendar, send (gated) |
| 🌐 **HTTP API + web UI** | Mobile-first chat at `http://<host>:8765`, auth via bearer token |
| 📱 **iPhone voice actions** | Siri dictation → intent endpoints → native iOS Telegram / Phone / Messages / Calendar |
| 🎙 **Voice everywhere** | `qagent voice` (Whisper + edge-tts), Telegram bot accepts voice notes |
| 🔒 **Safe defaults** | Shell off, send off, file sandbox to `--root`, chat allowlist for the bot |

---

## What it does (31 tools, 5 model providers, 7 CLI commands, 9 API endpoints)

### Tools

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

All your data lives under `~/qagent-data/` (notes, drafts, presentations, documents, calendar, contacts).

### HTTP API

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/health` | server up + current model + active sessions |
| `GET`  | `/api/tools` | list of tool names the agent has |
| `POST` | `/api/ask` | full agent chat: `{message, session_id?}` → `{session_id, reply}` |
| `POST` | `/api/reset` | reset a session's history |
| `POST` | `/api/intent/telegram` | voice → `{ok, contact, chat_id, message}` |
| `POST` | `/api/intent/telegram/send` | parse **and** send via your bot |
| `POST` | `/api/intent/call` | voice → `{ok, contact, number, tel_url}` |
| `POST` | `/api/intent/sms` | voice → `{ok, contact, number, message, sms_url}` |
| `POST` | `/api/intent/calendar` | voice → `{ok, title, when, duration_min, notes}` (resolves "tomorrow", "tonight", "next friday") |
| `GET`  | `/` | mobile-first web chat UI |

All `POST`s honor `Authorization: Bearer <QAGENT_API_TOKEN>` when set.

### CLI commands

| Command | What it does |
|---------|--------------|
| `qagent doctor` | Check provider + model availability |
| `qagent agent` | Interactive REPL (alias: `chat`) |
| `qagent run "..."` | One-shot task |
| `qagent voice` | Microphone → Whisper → agent → TTS speaker |
| `qagent serve` | HTTP API + mobile web UI |
| `qagent bot` | Telegram long-polling bot (handles text **and** voice notes) |

Each command accepts `--model`, `--provider`, `--root`, `--allow-shell`, `--allow-write/--no-write`, `--allow-send`, `--max-steps`, `--host`, `--verbose`.

---

## Quick start

```bash
# 1. Local model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b-instruct        # ~6 GB VRAM, e.g. RTX 3060 laptop
# or qwen2.5:7b-instruct on a bigger GPU

# 2. Install
cd ~/Projects/your-personal-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[server]"             # CLI + HTTP API + web UI
# pip install -e ".[all]"              # everything (voice, docx, slides)

# 3. Try it
qagent doctor                          # check Ollama + model
qagent agent --verbose                 # interactive REPL
qagent run "Add a task: pay rent (high priority, due Friday)"
qagent serve --port 8765               # start the web app for phone/laptop
```

---

## Use it from your phone

### A. Web app on the same WiFi (zero config)

```bash
qagent serve --bind 0.0.0.0 --port 8765
```

- Workstation LAN IP: `hostname -I`
- iPhone Safari / Android Chrome → `http://<LAN-IP>:8765`
- **Share → Add to Home Screen** for a PWA-style icon

### B. Anywhere via Tailscale (recommended for remote use)

1. Install [Tailscale](https://tailscale.com/download) on workstation + phone, log in to the same tailnet
2. Run `qagent serve` as usual
3. On phone → `http://<tailscale-ip>:8765` — works from anywhere, end-to-end encrypted

### C. Telegram bot (no port forwarding ever needed) — **with voice notes!**

1. `@BotFather` → `/newbot` → copy token
2. Send your bot a message, visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your `chat.id`
3. `cp .env.example .env` and fill in `QAGENT_TG_*` vars
4. `set -a; source .env; set +a && qagent bot`
5. Open Telegram on your iPhone → message the bot OR **tap the mic icon and send a voice note**.
   The bot transcribes with Whisper, runs the agent, replies.

### D. iPhone voice actions (Siri Shortcuts)

Four ready-made Siri Shortcuts turn your voice into native iOS actions:

| Voice command | iOS result |
|---------------|------------|
| "Hey Siri, **telegram message**" | Opens Telegram with text prefilled — or sends via your bot to a known contact |
| "Hey Siri, **call contact**" | Opens iOS Phone with the number ready (you tap to dial) |
| "Hey Siri, **send text**" | iOS Messages opens prefilled (Apple requires the final tap) |
| "Hey Siri, **add appointment**" | Event appears in iOS Calendar instantly (no tap needed) |

How they work: Siri dictates → Shortcut POSTs the transcript to `/api/intent/{telegram,call,sms,calendar}` → the agent returns clean JSON → the Shortcut runs the matching iOS native action.

**Setup (one time):**

1. Add contacts on the workstation:

```bash
cp deploy/contacts.example.json ~/qagent-data/contacts.json
# Edit with real chat_ids and phone numbers
```

```json
{
  "marco": {"telegram_chat_id": "123456789", "phone": "+39 333 1234567"},
  "mom":   {"telegram_chat_id": "987654321", "phone": "+39 333 9999999"}
}
```

2. Build the 4 shortcuts on your iPhone following:
   - [`deploy/IOS_SHORTCUTS.md`](deploy/IOS_SHORTCUTS.md) — index + general setup
   - [`deploy/shortcuts/telegram.md`](deploy/shortcuts/telegram.md)
   - [`deploy/shortcuts/call.md`](deploy/shortcuts/call.md)
   - [`deploy/shortcuts/sms.md`](deploy/shortcuts/sms.md)
   - [`deploy/shortcuts/calendar.md`](deploy/shortcuts/calendar.md)

3. Bind each to a Siri phrase. Done — you can now talk to your iPhone and have it act on the answers from the agent at home.

### E. Generic "Hey Siri, ask my agent"

A simpler shortcut that just POSTs to `/api/ask` and reads the reply aloud. Recipe in [`deploy/PHONE_ACCESS.md`](deploy/PHONE_ACCESS.md).

---

## iOS limits to know

Apple intentionally gates a few actions for security:

- **Phone calls and SMS always require a final user tap.** The voice → Shortcut → app prefill path is the closest you can get to "fire and forget".
- **Calendar events can be added without any confirmation.** Truly hands-free.
- **Telegram** has two flavors:
  - **Bot path** (smoothest) — voice note to your bot, agent replies in the same chat.
  - **Shortcut path** — Siri → agent extracts the recipient + body → either sends via the bot (if you have their `chat_id` in contacts) or opens the Telegram app prefilled.

---

## Talk to it locally (`qagent voice`)

```bash
pip install -e ".[voice]"
sudo apt install libportaudio2 ffmpeg    # Linux only
qagent voice --voice it-IT-IsabellaNeural --seconds 8
```

Per turn: record → Whisper transcribes (CPU) → Qwen replies (GPU) → edge-tts speaks the reply.

---

## Send email + Telegram (gated)

```bash
# .env
QAGENT_SMTP_HOST=smtp.gmail.com
QAGENT_SMTP_USER=you@example.com
QAGENT_SMTP_PASSWORD=your-app-password

QAGENT_TG_BOT_TOKEN=...
QAGENT_TG_DEFAULT_CHAT=123456789
QAGENT_TG_ALLOWED_CHATS=123456789
```

```bash
set -a; source .env; set +a
qagent agent --allow-send
you> Send an email to marco@example.com saying I'll be 10 min late
```

Without `--allow-send`, the agent always **drafts** to `~/qagent-data/drafts/` so you can review before sending. The `/api/intent/telegram/send` endpoint is also gated by `--allow-send`.

---

## Pluggable model backend

Today: Ollama on your GPU. Tomorrow: bigger workstation, or a cloud endpoint — same config, no code change.

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

| `provider` | What it talks to |
|------------|------------------|
| `ollama` | Local Ollama daemon (default) |
| `openai` / `openai-compat` | OpenAI API (`OPENAI_API_KEY`) |
| `vllm` | Self-hosted vLLM at `--host http://server:8000/v1` |
| `lmstudio` | LM Studio's OpenAI-compatible local server |

Upgrade or swap:

```bash
qagent agent --model qwen2.5:14b-instruct                     # bigger local GPU
qagent agent --provider openai --model gpt-4o-mini            # cloud fallback
qagent agent --provider vllm --host http://workstation:8000/v1 --model my-model
```

---

## Storage layout (`~/qagent-data/`)

```
~/qagent-data/
├── contacts.json              # name → {telegram_chat_id, phone}
├── notes/                     # *.md
├── drafts/                    # email-*.json, tg-*.json, wa-*.json
├── documents/                 # *.md, *.docx, *.html
├── presentations/             # *.md, *.pptx
└── calendar/
    ├── tasks.json
    └── events.json
```

Nothing here is committed to git; it stays on the workstation.

---

## Auto-start on boot

```bash
chmod +x deploy/start-agent.sh
# Edit ~/.config/systemd/user/qagent.service (template in deploy/PHONE_ACCESS.md)
systemctl --user enable --now qagent
```

`start-agent.sh` auto-starts Ollama if it isn't running, loads `.env`, and execs `qagent serve` on `${QAGENT_PORT:-8765}`.

---

## Architecture

```
            ┌────────── inputs ──────────┐
            │                            │
   ┌────────┴────┐  ┌─────────────┐  ┌───┴──────────┐
   │ CLI / voice │  │  Web (PWA)  │  │ Telegram bot │
   │ on laptop   │  │ phone / lap │  │ text + voice │
   └─────┬───────┘  └─────┬───────┘  └──────┬───────┘
         │                │                 │
         │           HTTP/JSON          long-poll
         │                │                 │
         │      ┌─────────▼──────────┐      │
         │      │  qagent server     │      │
         │      │  /api/ask          │      │
         │      │  /api/intent/*    ─┼──┐   │
         │      └─────────┬──────────┘  │   │
         │                │             │   │
         └────────────────▼─────────────┼───┘
                  ┌──────────────────┐  │
                  │   qagent.Agent   │  │   (intent parser
                  │  provider+tools  │  │    uses same model,
                  └────────┬─────────┘  │    JSON-only prompt)
                           │            │
       ┌───────────────────┼────────────┘
       ▼                   ▼
 ┌──────────┐      ┌──────────────┐
 │ Ollama   │      │ 31 tools     │
 │ Qwen GPU │      │ files, web,  │
 │          │      │ notes, slides│
 │ (or any  │      │ calendar,    │
 │ OpenAI-  │      │ docs, send,  │
 │ compat)  │      │ shell, …     │
 └──────────┘      └──────────────┘
                                       ┌───────────────┐
              Output side ────────────▶│ iPhone native │
              (intent endpoints        │ Phone / SMS / │
               return clean JSON       │ Calendar /    │
               for iOS Shortcuts)      │ Telegram      │
                                       └───────────────┘
```

The **model lives on your workstation** — your data stays local. Outbound calls happen only for: web search (DuckDuckGo), TTS (edge-tts → Microsoft), your Telegram bot, and your SMTP server. All are off unless you turn them on.

---

## Safety defaults

| Action | Default | Toggle |
|--------|---------|--------|
| Read files | on | — |
| Write files | on | `--no-write` |
| Shell commands | **off** | `--allow-shell` |
| Send email / Telegram | **off** | `--allow-send` |
| File access | sandboxed to `--root` | — |
| HTTP API auth | open on LAN | `--api-token` / `QAGENT_API_TOKEN` |
| Telegram allowlist | deny-all | `QAGENT_TG_ALLOWED_CHATS` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach Ollama` | `ollama serve` (or use `deploy/start-agent.sh`) |
| Web UI loads but `/api/ask` 500s | Cold model load (~30–50 s on first request); retry |
| Bot doesn't reply | Check your `chat.id` is in `QAGENT_TG_ALLOWED_CHATS` |
| Bot ignores voice notes | `pip install -e ".[voice]"` (workstation) |
| `/api/intent/calendar` returns placeholder text | The model wrote `<TOMORROW>` — Python resolves common cases; retry with more explicit dates |
| iOS Shortcut returns nothing | Check the URL includes your LAN/Tailscale IP and the API token header matches |
| Phone can't reach LAN URL | Workstation firewall — open port 8765, or use Tailscale |
| Voice install fails | `sudo apt install libportaudio2 ffmpeg` |
| CUDA OOM | Stick to 3B; close other GPU apps |

---

## Repo

- This repo: **`your-personal-agent`** (canonical)
- Mirror: **`qwen-agent-cli`** (kept in sync)

Both are public. Contributions and ideas welcome.

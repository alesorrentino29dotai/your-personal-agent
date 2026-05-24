# Telegram bot setup

Step-by-step guide to wire your personal agent to a Telegram bot you can chat with from your iPhone/Android.

The bot supports **text messages**, **voice notes** (auto-transcribed with Whisper), and is locked to an allowlist of chat IDs so only you can talk to it.

---

## 1. Create the bot

1. On Telegram, open a chat with **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot`
3. Pick a **name** (display name, e.g. "Marco's Agent")
4. Pick a **username** ending in `bot` (e.g. `marco_personal_assistant_bot`)
5. BotFather replies with a **token** like `123456:ABC-DEF...` — copy it

> ⚠️ **The token is a password.** Anyone with it can fully control the bot. Never paste it into chats, screenshots, or commits. If you ever leak it, send `/revoke` to BotFather and pick the bot to get a new one.

---

## 2. Find your chat ID

The bot only replies to chats in `QAGENT_TG_ALLOWED_CHATS`. You need your personal chat ID.

1. Open the bot you just created (search its username, e.g. `@marco_personal_assistant_bot`)
2. Send it any message, e.g. `hi`
3. On the workstation, run:

```bash
TOKEN='paste-your-token-here'
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates" | python3 -m json.tool
```

Look for `"chat": {"id": 123456789, ...}` — that **`id`** is your chat ID. If the response is empty (`"result": []`), you didn't send a message yet; send one and retry.

For multi-user groups, the `id` will be negative (e.g. `-1001234567890`).

---

## 3. Configure environment variables

First, **create `.env` from the template** (the repo only ships `.env.example` — `.env` itself is git-ignored to keep your secrets local):

```bash
cd ~/Projects/qwen-agent-cli
cp .env.example .env
${EDITOR:-nano} .env
```

Fill in these three lines (delete or ignore the SMTP block if you only want Telegram):

```bash
# Get this from BotFather (step 1)
QAGENT_TG_BOT_TOKEN=123456:ABC-DEF...

# Your own chat ID (step 2) — used as a fallback when the agent doesn't specify
QAGENT_TG_DEFAULT_CHAT=123456789

# Comma-separated allowlist. ONLY these chat IDs can talk to the bot.
# Add multiple by separating with commas. Leave empty = deny everyone.
QAGENT_TG_ALLOWED_CHATS=123456789
```

Syntax rules (silent footguns):

- **No quotes** around values — `KEY=abc:def`, not `KEY="abc:def"`
- **No spaces** around `=` — `KEY=value`, not `KEY = value`
- One `KEY=value` per line, no `export` keyword (the `set -a` step adds it)

**Verify the values were loaded** before starting the bot:

```bash
set -a; source .env; set +a
echo "token len: ${#QAGENT_TG_BOT_TOKEN}  default: $QAGENT_TG_DEFAULT_CHAT  allowed: $QAGENT_TG_ALLOWED_CHATS"
```

Expected output:

```
token len: 46  default: 123456789  allowed: 123456789
```

If `token len: 0` or the IDs are blank, `.env` is missing/typo'd. Fix and re-source before running `qagent bot`.

If multiple people will use the bot, add each chat ID to `QAGENT_TG_ALLOWED_CHATS`, comma-separated.

---

## 4. Run the bot

```bash
cd ~/Projects/qwen-agent-cli
source .venv/bin/activate
set -a; source .env; set +a       # load .env into the shell
qagent bot
```

You should see:

```
Bot is listening. Allowed chats: {123456789}. Press Ctrl+C to stop.
```

Now message your bot from Telegram on your iPhone — the agent replies. Each chat keeps its own conversation history.

---

## 5. Voice notes (recommended)

The bot can transcribe Telegram voice notes (tap & hold the mic icon in Telegram) using `faster-whisper`:

```bash
pip install -e ".[voice]"
sudo apt install ffmpeg libportaudio2     # Linux
```

Now send the bot a voice note — it will transcribe and reply. The first voice note triggers a one-time ~150 MB Whisper model download.

---

## 6. Keep the bot running 24/7

### Option A: `tmux` / `screen` (quick)

```bash
tmux new -s qagent
qagent bot
# Detach with Ctrl+B, D
```

### Option B: systemd user service (recommended on Linux)

Create `~/.config/systemd/user/qagent-bot.service`:

```ini
[Unit]
Description=Personal Agent Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Projects/qwen-agent-cli
EnvironmentFile=%h/Projects/qwen-agent-cli/.env
ExecStart=%h/Projects/qwen-agent-cli/.venv/bin/qagent bot
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now qagent-bot
journalctl --user -u qagent-bot -f      # live logs
```

---

## 7. Optional: agent sends Telegram messages back to you

`/api/intent/telegram/send` and the `send_telegram` tool let the agent **send messages on your behalf** (e.g. from a Siri Shortcut on your iPhone, voice → agent extracts → bot sends).

This is gated by `--allow-send`:

```bash
qagent serve --allow-send
qagent agent --allow-send
```

Add a `~/qagent-data/contacts.json` mapping contact names to their `telegram_chat_id` so the agent knows where to send. See [`contacts.example.json`](contacts.example.json).

---

## 8. Troubleshooting

| Problem | Likely cause / fix |
|---------|--------------------|
| `qagent bot` prints "Telegram bot is not configured" | `.env` doesn't exist or wasn't sourced. Run `cp .env.example .env`, fill it in, then `set -a; source .env; set +a` in the **same shell** before `qagent bot`. |
| `bash: .env: No such file or directory` | You never copied the template. `cp .env.example .env` first. |
| `getUpdates` returns 404 / "Not Found" | Token is wrong or already revoked. Generate a new one via BotFather. |
| `getUpdates` returns `"result": []` | You haven't messaged the bot yet, or another running bot instance is draining updates. Stop other instances and resend a message. |
| Bot starts but never replies | Your chat ID isn't in `QAGENT_TG_ALLOWED_CHATS`. Check the bot logs. |
| Bot says "Voice messages need faster-whisper" | `pip install -e ".[voice]"` |
| Bot says "Could not transcribe" | Whisper model failed to load — check disk space and `ffmpeg` install |
| Replies are slow on first message | Cold model load (~30–50 s for Qwen 3B), then fast |
| Token leaks (shared in chat, pushed by mistake, etc.) | BotFather → `/revoke` → pick the bot → use the new token everywhere |

---

## Quick reference

```bash
# Get bot info (validate token)
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -m json.tool

# Get chat IDs of people who messaged the bot
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates" | python3 -m json.tool

# Send a message (test from the workstation)
curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=hello from the agent"
```

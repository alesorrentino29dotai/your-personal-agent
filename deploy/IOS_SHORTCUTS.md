# iOS Shortcuts + Siri → Local qagent

Use Siri on your iPhone to drive your local `qagent` running on your workstation.
The Shortcut dictates a phrase, sends it to the agent's HTTP API, and the agent
returns structured JSON that the Shortcut turns into a native iOS action
(Telegram message, phone call, SMS, calendar event).

---

## Overview

- This connects your iPhone to your **local agent** (running at home on your
  workstation) via **Siri voice + iOS Shortcuts**.
- Voice transcription uses **Apple's built-in dictation** (no extra setup, no
  cloud STT, no API key).
- The agent parses the transcript and returns **structured JSON**; the Shortcut
  performs the iOS native action (open Messages, open Phone, add Calendar
  event, etc.).
- Result: you say "Hey Siri, telegram message", talk freely, and the right app
  pops up prefilled — or the action is queued through your agent's bot.

---

## Prerequisites

1. Workstation running the agent's HTTP server:

   ```bash
   qagent serve --bind 0.0.0.0 --port 8765
   ```

   For remote access (outside your LAN), expose it through **Tailscale** rather
   than opening a port on your router.

2. Set an API token so random LAN guests can't call your agent:

   ```bash
   export QAGENT_API_TOKEN=<random-string>
   ```

   Use the same string in the `Authorization: Bearer …` header in every
   Shortcut below.

3. Pick the URL your iPhone will hit:
   - LAN: `http://<workstation-lan-ip>:8765`
   - Remote via Tailscale: `http://<tailscale-ip>:8765`

4. Maintain a contacts file at `~/qagent-data/contacts.json` on the workstation,
   keyed by short names you'll actually say to Siri:

   ```json
   {
     "marco": {"telegram_chat_id": "123456789", "phone": "+39 333 1234567"},
     "mom":   {"telegram_chat_id": "987654321", "phone": "+39 333 9999999"}
   }
   ```

   The agent looks names up case-insensitively and tolerates fuzzy matches
   (e.g. "send a text to mom" → `mom`).

---

## Important iOS limits (read this first)

iOS deliberately restricts how far automation can go for messaging and calls.
The recipes below are designed around these limits, not against them.

- **SMS and phone calls always require a final user tap.** Apple security: a
  Shortcut can prefill Messages or the dialer, but you must confirm. There is
  no workaround — don't waste time looking for one.
- **Calendar events can be added without confirmation.** They appear
  immediately in iOS Calendar once the Shortcut runs.
- **Telegram via voice has two flavors:**
  - **Best UX:** send the bot a Telegram voice note directly — the bot
    transcribes server-side and the agent acts. No Shortcut needed.
  - **Alternative (covered here):** use the "Telegram via Agent" Shortcut to
    compose by voice on iPhone and either open the Telegram app prefilled or
    send through the agent's bot.

---

## Recipes

| Recipe                              | File                                       | Siri phrase                  |
|-------------------------------------|--------------------------------------------|------------------------------|
| Send Telegram by Voice              | [shortcuts/telegram.md](shortcuts/telegram.md) | "Hey Siri, telegram message" |
| Call by Voice                       | [shortcuts/call.md](shortcuts/call.md)         | "Hey Siri, call contact"     |
| Send SMS by Voice                   | [shortcuts/sms.md](shortcuts/sms.md)           | "Hey Siri, send text"        |
| Add Calendar Event by Voice         | [shortcuts/calendar.md](shortcuts/calendar.md) | "Hey Siri, add appointment"  |

---

## How to add a Shortcut on iPhone (general steps)

Every recipe below follows the same flow. If you've never built a Shortcut,
do it once on the Telegram recipe and the rest will feel mechanical.

1. Open the **Shortcuts** app on iPhone.
2. Tap **+** (top right) to create a new shortcut.
3. Tap **Add Action** and add the listed actions **in order**. Search by the
   exact action name shown in the recipe (e.g. *Dictate Text*, *Get Contents
   of URL*, *Get Dictionary Value*).
4. Wire variables: most recipes pass the **Dictated Text** straight into the
   HTTP request body, then read fields back out with **Get Dictionary Value**.
5. Tap the **(i)** icon at the bottom → **Add to Siri** → record the suggested
   phrase (e.g. *"telegram message"*). Siri will then trigger it from any
   screen, including the lock screen and CarPlay.
6. Run it once from the Shortcuts app first to grant permissions (Network,
   Messages, Calendar, etc.). After that, voice-only works.

---

## Troubleshooting

- **HTTP 401 / 403** → token mismatch. Re-check the `Authorization` header in
  the *Get Contents of URL* action.
- **HTTP 404 contact** → name in dictation didn't match `contacts.json`. Speak
  it the way you wrote it (or add an alias to the JSON).
- **Connection refused** → agent isn't bound to `0.0.0.0` (default is
  loopback), or the IP changed. Reconfirm with `qagent serve --bind 0.0.0.0
  --port 8765` and re-check the LAN/Tailscale IP.
- **Dictation gives garbage on long phrases** → set *Stop on Pause* in the
  *Dictate Text* action so you control when it stops listening.

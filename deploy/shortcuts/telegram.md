# Shortcut: Send Telegram by Voice

Dictate freely → the agent parses the contact and message body → choose to
either **send via the agent's Telegram bot** (fully hands-free, no app switch)
or **open the Telegram app prefilled** (you tap Send yourself).

Siri phrase: **"Hey Siri, telegram message"**

> Replace `<your-ip>` with your workstation's LAN IP or Tailscale IP, and
> `<your-token>` with `QAGENT_API_TOKEN`.

---

## Actions (in order)

### 1. Dictate Text
- **Language:** your choice (English / Italian / etc.)
- **Stop Listening:** *On Pause*
- Output is referenced below as **Dictated Text**.

### 2. Get Contents of URL
- **URL:** `http://<your-ip>:8765/api/intent/telegram`
- **Method:** `POST`
- **Headers:**
  - `Authorization`: `Bearer <your-token>`
  - `Content-Type`: `application/json`
- **Request Body:** *JSON*
  - Key `message` → Value: **Dictated Text** (from action 1)

Expected JSON response (the agent parses your free-form dictation):

```json
{
  "contact": "marco",
  "telegram_chat_id": "123456789",
  "message": "ci vediamo domani alle 8"
}
```

### 3. Get Dictionary Value
- **Get:** *Value*
- **Key:** `message`
- Tap the variable chip at the top → **Rename Variable** → `MessageBody`.

### 4. Get Dictionary Value
- **Get:** *Value*
- **Key:** `contact`
- Rename the variable to `ContactName`.

### 5. Choose from Menu
Add two menu items:

- **Send via Agent Bot** — fully automated, no app switch.
- **Open Telegram App** — opens Telegram with the message prefilled; you tap
  Send.

#### Branch A — "Send via Agent Bot"

Inside this menu branch:

1. **Get Contents of URL**
   - **URL:** `http://<your-ip>:8765/api/intent/telegram/send`
   - **Method:** `POST`
   - **Headers:**
     - `Authorization`: `Bearer <your-token>`
     - `Content-Type`: `application/json`
   - **Request Body:** *JSON*
     - `contact` → `ContactName`
     - `message` → `MessageBody`
2. **Show Notification**
   - **Title:** `Telegram`
   - **Body:** the response of the previous action (or just `MessageBody`).

#### Branch B — "Open Telegram App"

Inside this menu branch:

1. **URL** action
   - Value: `tg://msg?text=` followed by the variable **MessageBody**.
   - (Tip: use the *URL Encode* action on `MessageBody` if you expect special
     characters.)
2. **Open URLs** with that URL — Telegram opens with the body prefilled, then
   you tap the contact and Send.

### 6. (Optional) Speak Text
- Text: `Message sent to ` + variable **ContactName**.

### 7. Add to Siri
- Tap the **(i)** at the bottom → **Add to Siri** → record
  **"telegram message"**.

---

## Test

Voice phrase:

> *"Send a Telegram to Marco saying I'll be ten minutes late."*

Expected response from `POST /api/intent/telegram`:

```json
{
  "contact": "marco",
  "telegram_chat_id": "123456789",
  "message": "I'll be ten minutes late"
}
```

Expected response from `POST /api/intent/telegram/send` (Branch A):

```json
{
  "ok": true,
  "contact": "marco",
  "telegram_message_id": 4421
}
```

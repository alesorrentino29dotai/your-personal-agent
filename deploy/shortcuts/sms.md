# Shortcut: Send SMS by Voice

Dictate **"text <name> saying <message>"**, the agent splits out recipient
and body, and iOS opens Messages prefilled. You tap **Send**.

Siri phrase: **"Hey Siri, send text"**

> Like calls, SMS always requires a final user tap — Apple doesn't allow
> Shortcuts to send Messages silently.

---

## Actions (in order)

### 1. Dictate Text
- **Language:** your choice.
- **Stop Listening:** *On Pause*.
- Speak phrases like *"text Marco saying I'll be ten minutes late"*.

### 2. Get Contents of URL
- **URL:** `http://<your-ip>:8765/api/intent/sms`
- **Method:** `POST`
- **Headers:**
  - `Authorization`: `Bearer <your-token>`
  - `Content-Type`: `application/json`
- **Request Body:** *JSON*
  - `message` → **Dictated Text**

Expected response:

```json
{
  "contact": "marco",
  "number": "+39 333 1234567",
  "message": "I'll be ten minutes late",
  "sms_url": "sms:+393331234567&body=I%27ll%20be%20ten%20minutes%20late"
}
```

### 3. Get Dictionary Value (×2)
- First: **Get** *Value* for key `number` → rename variable to `Recipient`.
- Second: **Get** *Value* for key `message` → rename variable to `MessageBody`.

### 4. Send Message
- **Message:** **MessageBody**
- **Recipients:** **Recipient**
- Toggle **Show When Run** *on* — iOS opens Messages prefilled and you tap
  **Send** to confirm.

### 5. (Alternative) Open URLs with `sms_url`
If you prefer not to use the *Send Message* action, you can instead read the
`sms_url` field from the response and pass it to **Open URLs**. iPhone opens
Messages with both recipient and body filled — also tap-to-send.

### 6. Add to Siri
- Tap **(i)** → **Add to Siri** → record **"send text"**.

---

## Test

Voice phrase:

> *"Text Marco saying I'll be ten minutes late."*

Expected response from `POST /api/intent/sms`:

```json
{
  "contact": "marco",
  "number": "+39 333 1234567",
  "message": "I'll be ten minutes late",
  "sms_url": "sms:+393331234567&body=I%27ll%20be%20ten%20minutes%20late"
}
```

The Messages app appears with **+39 333 1234567** as recipient and the body
prefilled — tap **Send**.

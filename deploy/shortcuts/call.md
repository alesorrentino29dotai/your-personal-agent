# Shortcut: Call by Voice

Dictate **"call <name>"**, the agent resolves the contact, returns a `tel:`
URL, and iOS opens the dialer with the call confirmation.

Siri phrase: **"Hey Siri, call contact"**

> iOS always shows a final confirmation before dialing — this is an Apple
> security rule and cannot be bypassed.

---

## Actions (in order)

### 1. Dictate Text
- **Language:** your choice.
- **Stop Listening:** *On Pause*.
- Speak phrases like *"call Marco"* or *"call mom"*.

### 2. Get Contents of URL
- **URL:** `http://<your-ip>:8765/api/intent/call`
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
  "phone": "+39 333 1234567",
  "tel_url": "tel:+393331234567"
}
```

### 3. Get Dictionary Value
- **Get:** *Value*
- **Key:** `tel_url`
- Rename variable to `TelURL`.

### 4. (Optional) Get Dictionary Value
- **Get:** *Value*
- **Key:** `contact`
- Rename variable to `ContactName` (used by the Speak Text step below).

### 5. Open URLs
- URL input: **TelURL**.
- iPhone surfaces the native "Call <number>?" prompt.

### 6. (Optional) Speak Text
- Text: `Calling ` + **ContactName**.

### 7. Add to Siri
- Tap **(i)** → **Add to Siri** → record **"call contact"**.

---

## Test

Voice phrase:

> *"Call Marco."*

Expected response from `POST /api/intent/call`:

```json
{
  "contact": "marco",
  "phone": "+39 333 1234567",
  "tel_url": "tel:+393331234567"
}
```

After **Open URLs** runs, iOS displays the standard "Call +39 333 1234567?"
confirmation — tap **Call**.

# Shortcut: Add Calendar Event by Voice

Dictate **"remind me about <event> at <when>"**, the agent extracts a
structured event, and the Shortcut adds it directly to iOS Calendar — no
confirmation tap required.

Siri phrase: **"Hey Siri, add appointment"**

> Unlike SMS and calls, Calendar events **do not** require a final confirmation.
> They appear instantly once the Shortcut runs.

---

## Actions (in order)

### 1. Dictate Text
- **Language:** your choice.
- **Stop Listening:** *On Pause*.
- Speak phrases like *"remind me about the dentist tomorrow at 3pm for 30
  minutes"*.

### 2. Get Contents of URL
- **URL:** `http://<your-ip>:8765/api/intent/calendar`
- **Method:** `POST`
- **Headers:**
  - `Authorization`: `Bearer <your-token>`
  - `Content-Type`: `application/json`
- **Request Body:** *JSON*
  - `message` → **Dictated Text**

Expected response:

```json
{
  "title": "Dentist",
  "when": "2026-05-25T15:00:00+02:00",
  "duration_min": 30,
  "notes": "Added by qagent via Siri"
}
```

### 3. Get Dictionary Value (×4)
For each key, add a *Get Dictionary Value* action and rename the variable:

| Key            | Variable name   |
|----------------|-----------------|
| `title`        | `EventTitle`    |
| `when`         | `EventWhenISO`  |
| `duration_min` | `EventDuration` |
| `notes`        | `EventNotes`    |

### 4. Format Date
- **Format Date:** **EventWhenISO**
- **Date Format:** *ISO 8601* (input) → the action returns a real Date object.
- Rename output to `StartDate`.

### 5. Calculate
- **Adjust Date**
  - **Date:** **StartDate**
  - **Operation:** *Add*
  - **Magnitude:** **EventDuration**
  - **Unit:** *Minutes*
- Rename output to `EndDate`.

### 6. Add New Event
- **Title:** **EventTitle**
- **Calendar:** pick your default (e.g. *Home* or *Work*).
- **Start Date:** **StartDate**
- **End Date:** **EndDate**
- **Notes:** **EventNotes**
- Leave *Show When Run* **off** so the event is added silently.

### 7. Speak Text
- Text: `Added event ` + **EventTitle** + ` at ` + **EventWhenISO**.

### 8. Add to Siri
- Tap **(i)** → **Add to Siri** → record **"add appointment"**.

---

## Test

Voice phrase:

> *"Remind me about the dentist tomorrow at 3pm for 30 minutes."*

Expected response from `POST /api/intent/calendar`:

```json
{
  "title": "Dentist",
  "when": "2026-05-25T15:00:00+02:00",
  "duration_min": 30,
  "notes": "Added by qagent via Siri"
}
```

A new event titled **Dentist** appears in iOS Calendar at 15:00–15:30 on the
target day, and Siri confirms aloud: *"Added event Dentist at
2026-05-25T15:00:00+02:00."*

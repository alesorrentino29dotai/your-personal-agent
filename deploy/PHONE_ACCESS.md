# Phone Access Guide

How to reach your Personal Agent from a phone.

## 1. Same WiFi (easiest)

- Run `qagent serve --bind 0.0.0.0 --port 8765`
- Find workstation IP:
  - Linux: `hostname -I`
  - macOS: `ipconfig getifaddr en0`
  - Windows: `ipconfig`
- On iPhone/Android, open Safari/Chrome → `http://<LAN-IP>:8765`
- Add to Home Screen for a PWA-like icon (Safari: Share → Add to Home Screen)

## 2. Outside your network (recommended: Tailscale)

- Install Tailscale on workstation + phone: <https://tailscale.com/download>
- Authenticate both devices to the same tailnet
- Run agent normally; access via `http://<tailscale-ip>:8765` from phone anywhere
- Free for personal use, encrypted, no port forwarding needed

## 3. Public tunnel (Cloudflare)

- `cloudflared tunnel --url http://localhost:8765`
- Get a temporary `*.trycloudflare.com` URL
- Set `QAGENT_API_TOKEN` env var first and require it via Authorization header
- Good for quick sharing; not recommended for long-term use

## 4. Telegram (already supported)

- Just run `qagent bot` after setting `QAGENT_TG_*` env vars
- Then chat with your bot from the Telegram app on any phone — no port/firewall needed

## 5. Security

- Always set `QAGENT_API_TOKEN` for non-LAN exposure
- Keep `--allow-shell` and `--allow-send` off unless needed
- The bot honors `QAGENT_TG_ALLOWED_CHATS` allowlist

## 6. Auto-start on boot (Linux)

Use systemd. Example user unit at `~/.config/systemd/user/qagent.service`:

```ini
[Unit]
Description=Personal Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Projects/qwen-agent-cli
ExecStart=%h/Projects/qwen-agent-cli/deploy/start-agent.sh
Restart=on-failure

[Install]
WantedBy=default.target
```

Then enable and start:

```bash
systemctl --user enable --now qagent
```

## 7. iPhone shortcuts (Siri)

- Create an iOS Shortcut that does "Get Contents of URL" POST to `http://<your-tailscale-ip>:8765/api/ask` with JSON body `{"message": "<dictated input>"}` and Auth header.
- Bind to "Hey Siri, ask my agent" — now you can voice-prompt from iPhone.

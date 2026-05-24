#!/usr/bin/env bash
# Start the Personal Agent stack: ensures Ollama is running, then launches the HTTP server.
set -euo pipefail

PORT="${QAGENT_PORT:-8765}"
ROOT="${QAGENT_ROOT:-$HOME}"
MODEL="${QAGENT_MODEL:-qwen2.5:3b-instruct}"

cd "$(dirname "$0")/.."

# Load .env if present
if [ -f .env ]; then
  set -a; source .env; set +a
fi

# Make sure Ollama is reachable
if ! curl -s --max-time 2 "http://127.0.0.1:11434/api/tags" >/dev/null; then
  echo "Ollama not running. Starting it in the background..."
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  for i in $(seq 1 15); do
    if curl -s --max-time 2 "http://127.0.0.1:11434/api/tags" >/dev/null; then
      echo "Ollama is up."
      break
    fi
    sleep 1
  done
fi

# Activate venv if present
if [ -d .venv ]; then
  source .venv/bin/activate
fi

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "============================================"
echo "Personal Agent starting on port $PORT"
echo "Local:   http://localhost:$PORT"
echo "Network: http://$LAN_IP:$PORT  (open this on your phone, same WiFi)"
echo "============================================"

exec qagent serve --port "$PORT" --root "$ROOT" --model "$MODEL" "$@"

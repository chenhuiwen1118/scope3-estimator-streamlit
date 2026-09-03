#!/usr/bin/env bash
set -euo pipefail

APP_PORT="${APP_PORT:-8501}"
PYTHON_BIN="${PYTHON_BIN:-/Users/sashachen/Documents/Codex/2026-06-18/python3-m-venv-venv-source-venv/venv/bin/python}"

export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

echo "Starting Scope 3 Estimator on http://localhost:${APP_PORT}"
"${PYTHON_BIN}" -m streamlit run app.py \
  --server.port "${APP_PORT}" \
  --server.address localhost \
  --server.headless true &

APP_PID=$!

cleanup() {
  echo "Stopping Streamlit (${APP_PID})"
  kill "${APP_PID}" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for local Streamlit..."
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:${APP_PORT}/_stcore/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS "http://localhost:${APP_PORT}/_stcore/health" >/dev/null 2>&1; then
  echo "Streamlit did not become healthy on port ${APP_PORT}" >&2
  exit 1
fi

echo "Creating public tunnel with localhost.run..."
echo "Keep this terminal open while others are testing the public URL."
ssh -o StrictHostKeyChecking=no \
  -o ServerAliveInterval=30 \
  -R "80:localhost:${APP_PORT}" \
  nokey@localhost.run

#!/usr/bin/env bash
set -euo pipefail

OLLAMA_PORT="${OLLAMA_PORT:-11434}"
ADB_BIN="${ADB_BIN:-adb}"

if ! command -v "${ADB_BIN}" >/dev/null 2>&1; then
  echo "ERROR: adb not found"
  exit 1
fi

"${ADB_BIN}" start-server >/dev/null

echo "==> Connected devices"
"${ADB_BIN}" devices

echo "==> Reversing tcp:${OLLAMA_PORT}"
"${ADB_BIN}" reverse "tcp:${OLLAMA_PORT}" "tcp:${OLLAMA_PORT}"

echo
printf 'Pixel can now reach Ollama at http://127.0.0.1:%s\n' "${OLLAMA_PORT}"

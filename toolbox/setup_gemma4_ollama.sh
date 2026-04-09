#!/usr/bin/env bash
set -euo pipefail

MODEL_ALIAS="gemma4-26b-moe"
FALLBACK_MODEL="gemma4:latest"
OVERRIDE_DIR="${HOME}/.config/systemd/user/ollama.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/override.conf"

has_cmd() { command -v "$1" >/dev/null 2>&1; }

echo "==> Checking ollama"
if ! has_cmd ollama; then
  echo "ERROR: ollama not found. Install with: curl -fsSL https://ollama.com/install.sh | sh"
  exit 1
fi

if has_cmd systemctl && systemctl --user show-environment >/dev/null 2>&1; then
  echo "==> Writing systemd override"
  mkdir -p "${OVERRIDE_DIR}"
  cat > "${OVERRIDE_FILE}" <<'EOM'
[Service]
Environment=OLLAMA_FLASH_ATTENTION=1
Environment=OLLAMA_KV_CACHE_TYPE=q8_0
Environment=OLLAMA_NUM_PARALLEL=1
EOM
  systemctl --user daemon-reload
  if systemctl --user is-enabled ollama.service >/dev/null 2>&1; then
    systemctl --user restart ollama.service
  else
    systemctl --user enable --now ollama.service
  fi
else
  echo "==> No systemd user session; skipping override/restart"
fi

echo "==> Ensuring model ${FALLBACK_MODEL}"
if ! ollama list | awk 'NR>1{print $1}' | grep -Fxq "${FALLBACK_MODEL}"; then
  ollama pull "${FALLBACK_MODEL}"
fi

echo "==> Ensuring alias ${MODEL_ALIAS}"
if ! ollama list | awk 'NR>1{print $1}' | grep -Fxq "${MODEL_ALIAS}"; then
  tmp_modelfile="$(mktemp)"
  cat > "${tmp_modelfile}" <<EOM
FROM ${FALLBACK_MODEL}
PARAMETER num_ctx 163840
EOM
  ollama create "${MODEL_ALIAS}" -f "${tmp_modelfile}"
  rm -f "${tmp_modelfile}"
fi

echo "==> Smoke test"
out="$(ollama run "${MODEL_ALIAS}" "Reply with exactly: OK" 2>/dev/null | tr -d '\r' || true)"
if echo "${out}" | grep -q "OK"; then
  echo "Smoke test passed."
else
  echo "WARNING: Unexpected smoke test output:"
  echo "${out}"
fi

echo
echo "Endpoint: http://localhost:11434/v1"
echo "Model: ${MODEL_ALIAS}"
echo "Use these in your coding assistant/tool-user provider config."

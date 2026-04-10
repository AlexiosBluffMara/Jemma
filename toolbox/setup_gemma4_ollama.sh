#!/usr/bin/env bash
set -euo pipefail

MODEL_ROOT="${MODEL_ROOT:-${HOME}/models/hf}"
OVERRIDE_DIR="${HOME}/.config/systemd/user/ollama.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/override.conf"
PULL_OFFICIAL_OLLAMA="${PULL_OFFICIAL_OLLAMA:-0}"

E2B_BASE_SOURCE="${E2B_BASE_SOURCE:-${MODEL_ROOT}/google/gemma-4-E2B}"
E2B_IT_SOURCE="${E2B_IT_SOURCE:-${MODEL_ROOT}/google/gemma-4-E2B-it}"
E4B_BASE_SOURCE="${E4B_BASE_SOURCE:-${MODEL_ROOT}/google/gemma-4-E4B}"
E4B_IT_SOURCE="${E4B_IT_SOURCE:-${MODEL_ROOT}/google/gemma-4-E4B-it}"

OFFICIAL_E2B_OLLAMA_TAG="${OFFICIAL_E2B_OLLAMA_TAG:-gemma4:e2b}"
OFFICIAL_E4B_OLLAMA_TAG="${OFFICIAL_E4B_OLLAMA_TAG:-gemma4:e4b}"

E2B_NUM_CTX="${E2B_NUM_CTX:-131072}"
E4B_NUM_CTX="${E4B_NUM_CTX:-131072}"

REGISTER_BASE_MODELS="${REGISTER_BASE_MODELS:-1}"
REGISTER_INSTRUCT_MODELS="${REGISTER_INSTRUCT_MODELS:-1}"
REGISTER_QUANTS="${REGISTER_QUANTS:-1}"
REGISTER_BASE_QUANTS="${REGISTER_BASE_QUANTS:-0}"
RUN_SMOKE_TEST="${RUN_SMOKE_TEST:-0}"
RECREATE_EXISTING="${RECREATE_EXISTING:-0}"

E2B_QUANTS="${E2B_QUANTS:-q8_0,q4_K_M}"
E4B_QUANTS="${E4B_QUANTS:-q8_0,q4_K_M}"

TEMPERATURE="${TEMPERATURE:-1}"
TOP_P="${TOP_P:-0.95}"
TOP_K="${TOP_K:-64}"

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

model_exists() {
  ollama list | awk 'NR>1{print $1}' | grep -Fxq "$1"
}

source_exists() {
  local source="$1"
  [[ -e "$source" ]]
}

source_available() {
  local source="$1"
  source_exists "${source}" || model_exists "${source}"
}

alias_suffix_for_source() {
  local source="$1"
  if source_exists "${source}"; then
    printf '%s' 'bf16'
  else
    printf '%s' 'stock'
  fi
}

normalize_tag() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_'
}

ensure_ollama() {
  echo "==> Checking ollama"
  if ! has_cmd ollama; then
    echo "ERROR: ollama not found. Install with: curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
  fi
}

ensure_systemd_override() {
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
}

ensure_official_ollama_tag() {
  local tag="$1"

  if model_exists "${tag}"; then
    return
  fi

  if [[ "${PULL_OFFICIAL_OLLAMA}" != "1" ]]; then
    return
  fi

  echo "==> Pulling official Ollama tag ${tag}"
  ollama pull "${tag}"
}

fallback_source() {
  local preferred_source="$1"
  local fallback_tag="$2"

  if source_available "${preferred_source}"; then
    printf '%s' "${preferred_source}"
    return
  fi

  ensure_official_ollama_tag "${fallback_tag}"
  if model_exists "${fallback_tag}"; then
    printf '%s' "${fallback_tag}"
    return
  fi

  printf '%s' "${preferred_source}"
}

write_modelfile() {
  local source="$1"
  local num_ctx="$2"
  local modelfile="$3"

  cat > "${modelfile}" <<EOM
FROM ${source}
PARAMETER num_ctx ${num_ctx}
PARAMETER temperature ${TEMPERATURE}
PARAMETER top_p ${TOP_P}
PARAMETER top_k ${TOP_K}
EOM
}

create_model() {
  local alias="$1"
  local source="$2"
  local num_ctx="$3"
  local quant="${4:-}"
  local tmp_modelfile

  if ! source_available "${source}"; then
    echo "==> Skipping ${alias}: source not found at ${source}"
    return
  fi

  if model_exists "${alias}"; then
    if [[ "${RECREATE_EXISTING}" == "1" ]]; then
      echo "==> Recreating ${alias}"
      ollama rm "${alias}" >/dev/null
    else
      echo "==> Keeping existing ${alias}"
      return
    fi
  fi

  tmp_modelfile="$(mktemp)"
  write_modelfile "${source}" "${num_ctx}" "${tmp_modelfile}"

  echo "==> Creating ${alias} from ${source}"
  if [[ -n "${quant}" ]]; then
    ollama create --quantize "${quant}" "${alias}" -f "${tmp_modelfile}"
  else
    ollama create "${alias}" -f "${tmp_modelfile}"
  fi

  rm -f "${tmp_modelfile}"
}

create_quant_matrix() {
  local stem="$1"
  local source="$2"
  local num_ctx="$3"
  local quant_list="$4"
  local quant
  local quant_alias

  if ! source_exists "${source}"; then
    echo "==> Skipping quantization for ${stem}: source is not a local FP16/BF16 directory or GGUF file"
    return
  fi

  IFS=',' read -r -a quant_array <<< "${quant_list}"
  for quant in "${quant_array[@]}"; do
    quant="${quant#"${quant%%[![:space:]]*}"}"
    quant="${quant%"${quant##*[![:space:]]}"}"
    [[ -z "${quant}" ]] && continue
    quant_alias="${stem}:$(normalize_tag "${quant}")"
    create_model "${quant_alias}" "${source}" "${num_ctx}" "${quant}"
  done
}

smoke_test_alias() {
  local alias="$1"
  local output

  if ! model_exists "${alias}"; then
    echo "==> Smoke test skipped for ${alias}: alias not present"
    return
  fi

  echo "==> Smoke testing ${alias}"
  output="$(ollama run "${alias}" "Reply with exactly: OK" 2>/dev/null | tr -d '\r' || true)"
  if echo "${output}" | grep -q "OK"; then
    echo "Smoke test passed for ${alias}."
  else
    echo "WARNING: Unexpected smoke test output for ${alias}:"
    echo "${output}"
  fi
}

main() {
  local e2b_base_source
  local e2b_it_source
  local e4b_base_source
  local e4b_it_source
  local e2b_base_suffix
  local e2b_it_suffix
  local e4b_base_suffix
  local e4b_it_suffix

  ensure_ollama
  ensure_systemd_override

  e2b_base_source="$(fallback_source "${E2B_BASE_SOURCE}" "${OFFICIAL_E2B_OLLAMA_TAG}")"
  e2b_it_source="$(fallback_source "${E2B_IT_SOURCE}" "${OFFICIAL_E2B_OLLAMA_TAG}")"
  e4b_base_source="$(fallback_source "${E4B_BASE_SOURCE}" "${OFFICIAL_E4B_OLLAMA_TAG}")"
  e4b_it_source="$(fallback_source "${E4B_IT_SOURCE}" "${OFFICIAL_E4B_OLLAMA_TAG}")"
  e2b_base_suffix="$(alias_suffix_for_source "${e2b_base_source}")"
  e2b_it_suffix="$(alias_suffix_for_source "${e2b_it_source}")"
  e4b_base_suffix="$(alias_suffix_for_source "${e4b_base_source}")"
  e4b_it_suffix="$(alias_suffix_for_source "${e4b_it_source}")"

  if [[ "${REGISTER_BASE_MODELS}" == "1" ]]; then
    create_model "gemma4-e2b:${e2b_base_suffix}" "${e2b_base_source}" "${E2B_NUM_CTX}"
    create_model "gemma4-e4b:${e4b_base_suffix}" "${e4b_base_source}" "${E4B_NUM_CTX}"
  fi

  if [[ "${REGISTER_INSTRUCT_MODELS}" == "1" ]]; then
    create_model "gemma4-e2b-it:${e2b_it_suffix}" "${e2b_it_source}" "${E2B_NUM_CTX}"
    create_model "gemma4-e4b-it:${e4b_it_suffix}" "${e4b_it_source}" "${E4B_NUM_CTX}"
  fi

  if [[ "${REGISTER_QUANTS}" == "1" ]]; then
    if [[ "${REGISTER_BASE_QUANTS}" == "1" ]]; then
      create_quant_matrix "gemma4-e2b" "${e2b_base_source}" "${E2B_NUM_CTX}" "${E2B_QUANTS}"
      create_quant_matrix "gemma4-e4b" "${e4b_base_source}" "${E4B_NUM_CTX}" "${E4B_QUANTS}"
    fi

    create_quant_matrix "gemma4-e2b-it" "${e2b_it_source}" "${E2B_NUM_CTX}" "${E2B_QUANTS}"
    create_quant_matrix "gemma4-e4b-it" "${e4b_it_source}" "${E4B_NUM_CTX}" "${E4B_QUANTS}"
  fi

  if [[ "${RUN_SMOKE_TEST}" == "1" ]]; then
    smoke_test_alias "gemma4-e4b-it:q8_0"
    smoke_test_alias "gemma4-e4b-it:stock"
    smoke_test_alias "gemma4-e2b-it:q4_k_m"
    smoke_test_alias "gemma4-e2b-it:stock"
  fi

  echo
  echo "Endpoint: http://localhost:11434/v1"
  echo "Suggested workstation default: gemma4-e4b-it:q8_0"
  echo "Suggested mobile-target default: gemma4-e2b-it:q4_k_m"
}

main "$@"

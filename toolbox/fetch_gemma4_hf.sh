#!/usr/bin/env bash
set -euo pipefail

MODEL_ROOT="${MODEL_ROOT:-${HOME}/models/hf}"
SKIP_EXISTING="${SKIP_EXISTING:-1}"
HF_DOWNLOAD_TOOL="${HF_DOWNLOAD_TOOL:-auto}"
MODEL_IDS=(
  "google/gemma-4-E2B"
  "google/gemma-4-E2B-it"
  "google/gemma-4-E4B"
  "google/gemma-4-E4B-it"
)

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_hf() {
  case "${HF_DOWNLOAD_TOOL}" in
    uvx)
      if has_cmd uvx; then
        uvx --from huggingface_hub hf "$@"
        return
      fi
      ;;
    hf)
      if has_cmd hf; then
        hf "$@"
        return
      fi
      ;;
    huggingface-cli)
      if has_cmd huggingface-cli; then
        huggingface-cli "$@"
        return
      fi
      ;;
    auto)
      if has_cmd uvx; then
        uvx --from huggingface_hub hf "$@"
        return
      fi

      if has_cmd hf; then
        hf "$@"
        return
      fi

      if has_cmd huggingface-cli; then
        huggingface-cli "$@"
        return
      fi
      ;;
  esac

  echo "ERROR: need one of hf, huggingface-cli, or uvx to download checkpoints"
  exit 1
}

if [[ -n "${HF_TOKEN:-}" ]]; then
  export HUGGINGFACE_HUB_TOKEN="${HF_TOKEN}"
fi

mkdir -p "${MODEL_ROOT}"

echo "==> Download root: ${MODEL_ROOT}"
for model_id in "${MODEL_IDS[@]}"; do
  local_dir="${MODEL_ROOT}/${model_id}"
  if [[ "${SKIP_EXISTING}" == "1" && -d "${local_dir}" ]]; then
    if find "${local_dir}" -mindepth 1 -print -quit >/dev/null 2>&1; then
      echo "==> Skipping existing ${model_id}"
      continue
    fi
  fi

  echo "==> Downloading ${model_id}"
  mkdir -p "${local_dir}"
  run_hf download "${model_id}" --local-dir "${local_dir}"
done

echo
printf 'Downloaded official checkpoints into %s\n' "${MODEL_ROOT}"

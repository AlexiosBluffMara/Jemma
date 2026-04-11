#!/usr/bin/env bash
# Launch llama-server with a GGUF model for the Jemma framework.
# Usage: ./toolbox/launch_llamacpp_server.sh <path-to-gguf> [options]
#
# Prerequisites:
#   Build llama.cpp from source or install a release binary.
#   https://github.com/ggml-org/llama.cpp
#
# Examples:
#   ./toolbox/launch_llamacpp_server.sh /mnt/d/JemmaData/exports/gemma4-e4b-second-brain-gguf/model-Q8_0.gguf
#   ./toolbox/launch_llamacpp_server.sh model.gguf --ctx-size 16384 --n-gpu-layers 99
set -euo pipefail

GGUF_PATH="${1:?Usage: $0 <path-to-gguf> [extra llama-server flags]}"
shift

HOST="${LLAMACPP_HOST:-127.0.0.1}"
PORT="${LLAMACPP_PORT:-8080}"
CTX_SIZE="${LLAMACPP_CTX_SIZE:-8192}"
GPU_LAYERS="${LLAMACPP_GPU_LAYERS:-99}"
THREADS="${LLAMACPP_THREADS:-$(nproc 2>/dev/null || echo 4)}"

if ! command -v llama-server &>/dev/null; then
    echo "ERROR: llama-server not found. Build llama.cpp or add it to PATH." >&2
    echo "  git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j" >&2
    exit 1
fi

echo "Starting llama-server..."
echo "  Model:      $GGUF_PATH"
echo "  Host:       $HOST:$PORT"
echo "  Context:    $CTX_SIZE"
echo "  GPU layers: $GPU_LAYERS"
echo "  Threads:    $THREADS"

exec llama-server \
    --model "$GGUF_PATH" \
    --host "$HOST" \
    --port "$PORT" \
    --ctx-size "$CTX_SIZE" \
    --n-gpu-layers "$GPU_LAYERS" \
    --threads "$THREADS" \
    --flash-attn \
    "$@"

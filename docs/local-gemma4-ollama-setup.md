# Local Gemma 4 (Ollama) Setup

## Prerequisites
- Linux
- NVIDIA driver installed and working
- Ollama
- curl
- jq

## Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
systemctl --user daemon-reload
systemctl --user enable --now ollama.service
systemctl --user status ollama.service --no-pager

## Recommended performance settings
mkdir -p ~/.config/systemd/user/ollama.service.d

Create ~/.config/systemd/user/ollama.service.d/override.conf:
[Service]
Environment=OLLAMA_FLASH_ATTENTION=1
Environment=OLLAMA_KV_CACHE_TYPE=q8_0
Environment=OLLAMA_NUM_PARALLEL=1

Then:
systemctl --user daemon-reload
systemctl --user restart ollama.service

## Pull/create model alias
ollama pull gemma4:latest

Create local alias:
cat > /tmp/Modelfile.gemma4-26b-moe <<'EOM'
FROM gemma4:latest
PARAMETER num_ctx 163840
EOM
ollama create gemma4-26b-moe -f /tmp/Modelfile.gemma4-26b-moe

## Verify
curl -s http://localhost:11434/api/tags | jq .
ollama list
ollama run gemma4-26b-moe "Reply with exactly: OK"

## Use as coding assistant and tool user
- OpenAI-compatible endpoint: http://localhost:11434/v1
- Model: gemma4-26b-moe
- Configure your project agent/provider to use that endpoint and model.

## Example test prompt
"Write a Python CSV parser with strict validation, unit tests, and a short tradeoff analysis."

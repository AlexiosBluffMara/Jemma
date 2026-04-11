param(
    [Parameter(Mandatory)]
    [string]$GgufPath,

    [string]$Host = "127.0.0.1",
    [int]$Port = 8080,
    [int]$CtxSize = 8192,
    [int]$GpuLayers = 99,
    [int]$Threads = [Environment]::ProcessorCount
)

<#
.SYNOPSIS
  Launch llama-server with a GGUF model for the Jemma framework.

.DESCRIPTION
  Starts llama-server (from llama.cpp) exposing an OpenAI-compatible API
  that the Jemma LlamaCppProvider connects to.

.EXAMPLE
  .\toolbox\launch_llamacpp_server.ps1 -GgufPath D:\JemmaData\exports\gemma4-e4b-second-brain-gguf\model-Q8_0.gguf
  .\toolbox\launch_llamacpp_server.ps1 -GgufPath model.gguf -CtxSize 16384 -GpuLayers 99
#>

if (-not (Test-Path $GgufPath)) {
    throw "GGUF file not found: $GgufPath"
}

$llamaServer = Get-Command llama-server -ErrorAction SilentlyContinue
if (-not $llamaServer) {
    Write-Error "llama-server not found. Build llama.cpp or add it to PATH."
    Write-Error "  git clone https://github.com/ggml-org/llama.cpp; cd llama.cpp; cmake -B build -DGGML_CUDA=ON; cmake --build build --config Release"
    exit 1
}

Write-Host "Starting llama-server..."
Write-Host "  Model:      $GgufPath"
Write-Host "  Host:       ${Host}:${Port}"
Write-Host "  Context:    $CtxSize"
Write-Host "  GPU layers: $GpuLayers"
Write-Host "  Threads:    $Threads"

& llama-server `
    --model $GgufPath `
    --host $Host `
    --port $Port `
    --ctx-size $CtxSize `
    --n-gpu-layers $GpuLayers `
    --threads $Threads `
    --flash-attn

[CmdletBinding()]
param(
    [string]$NotebookPython = "D:\unsloth\studio\.venv\Scripts\python.exe",
    [string]$DataRoot = "D:\JemmaData",
    [ValidateSet("User", "Machine")]
    [string]$Scope = "User"
)

$resolvedDataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$datasetRoot = Join-Path $resolvedDataRoot "datasets"
$exportRoot = Join-Path $resolvedDataRoot "exports"
$runRoot = Join-Path $resolvedDataRoot "runs"
$logRoot = Join-Path $resolvedDataRoot "logs"

foreach ($path in @($resolvedDataRoot, $datasetRoot, $exportRoot, $runRoot, $logRoot)) {
    if (-not (Test-Path -LiteralPath $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

$variables = [ordered]@{
    JEMMA_NOTEBOOK_PYTHON = $NotebookPython
    JEMMA_DATA_DIR = $resolvedDataRoot
    OLLAMA_FLASH_ATTENTION = "1"
    OLLAMA_KV_CACHE_TYPE = "q8_0"
    OLLAMA_NUM_PARALLEL = "1"
}

foreach ($entry in $variables.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, $Scope)
    Write-Host ("Set {0}={1} [{2}]" -f $entry.Key, $entry.Value, $Scope)
}

Write-Host ""
Write-Host "Jemma workstation defaults are configured."
Write-Host "Restart your terminal and Ollama service before running notebook or deployment workflows."
Write-Host "Recommended next steps:"
Write-Host "  1. python FINAL_NOTEBOOK_RUNNER.py"
Write-Host "  2. python toolbox\prepare_ollama_cloud_bundle.py <deployment-manifest>"

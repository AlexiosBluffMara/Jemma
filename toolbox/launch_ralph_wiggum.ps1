<#
.SYNOPSIS
    Launch the Ralph Wiggum Loop for synthetic data generation.
    
    Sets up auth and runs the continuous data generation loop using
    FREE Gemma 4 26B on Vertex AI (free until Apr 16, 2026).

.DESCRIPTION
    STEP 1: Set your auth (pick ONE):
    
    Option A — API Key (easiest, works immediately):
      Go to https://aistudio.google.com/app/apikey
      Create a key, then:
        $env:GOOGLE_API_KEY = "your-api-key-here"

    Option B — Vertex AI (uses the $1K credit):
      1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
      2. gcloud auth application-default login
      3. $env:GOOGLE_CLOUD_PROJECT = "your-project-id"

    STEP 2: Run this script:
      .\toolbox\launch_ralph_wiggum.ps1

.NOTES
    Auto-shutoff: The loop automatically stops before the free period ends.
    After the free period, it enforces a $50/day budget cap.
#>

param(
    [string]$Model,
    [int]$MaxRpm = 30,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# --- Check Python ---
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: Python venv not found at $Python" -ForegroundColor Red
    exit 1
}

# --- Check auth ---
$hasApiKey = [bool]$env:GOOGLE_API_KEY
$hasProject = [bool]$env:GOOGLE_CLOUD_PROJECT

if (-not $hasApiKey -and -not $hasProject) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  AUTH REQUIRED - Pick one option:" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option A - API Key (easiest, works NOW):" -ForegroundColor Cyan
    Write-Host '  1. Go to: https://aistudio.google.com/app/apikey'
    Write-Host '  2. Create an API key'
    Write-Host '  3. Run: $env:GOOGLE_API_KEY = "YOUR_KEY_HERE"'
    Write-Host '  4. Re-run this script'
    Write-Host ""
    Write-Host "Option B - Vertex AI (uses $1K credit):" -ForegroundColor Cyan
    Write-Host '  1. Install gcloud: https://cloud.google.com/sdk/docs/install'
    Write-Host '  2. Run: gcloud auth application-default login'
    Write-Host '  3. Run: $env:GOOGLE_CLOUD_PROJECT = "your-project-id"'
    Write-Host '  4. Re-run this script'
    Write-Host ""
    exit 1
}

# --- Determine model ---
if (-not $Model) {
    if ($hasProject) {
        # Vertex AI: use the Gemma 4 model name
        $Model = "gemma-4-26b"
        Write-Host "Using Vertex AI with model: $Model" -ForegroundColor Green
    } else {
        # API key / Gemini Developer API: Gemma 4 may be listed differently
        $Model = "gemma-4-26b"
        Write-Host "Using API key with model: $Model" -ForegroundColor Green
    }
}

# --- Build command ---
$scriptPath = Join-Path $ScriptDir "vertex_synth_loop.py"
$outputDir = Join-Path $ProjectRoot "datasets\synth"

$cmdArgs = @(
    $scriptPath,
    "--model", $Model,
    "--max-rpm", $MaxRpm,
    "--output", $outputDir
)

if ($DryRun) {
    $cmdArgs += "--dry-run"
}

# --- Launch ---
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  RALPH WIGGUM LOOP — STARTING" -ForegroundColor Green
Write-Host "  Model: $Model" -ForegroundColor Green
Write-Host "  Output: $outputDir" -ForegroundColor Green
Write-Host "  Max RPM: $MaxRpm" -ForegroundColor Green
Write-Host "  Auth: $(if($hasApiKey){'API Key'}else{'Vertex AI'})" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

& $Python @cmdArgs

#!/usr/bin/env pwsh
# JEMMA Project Workflow Execution Script

$REPO_DIR = "D:\JemmaRepo\Jemma"
cd $REPO_DIR

Write-Host "============================================================================"
Write-Host "JEMMA PROJECT WORKFLOW EXECUTION"
Write-Host "============================================================================"
Write-Host "Working directory: $((Get-Location).Path)"
Write-Host ""

Write-Host ""
Write-Host "============================================================================"
Write-Host "COMMAND 1: python --version"
Write-Host "============================================================================"
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Command 1 failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "============================================================================"
Write-Host "COMMAND 2: python -c import sys info"
Write-Host "============================================================================"
python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Command 2 failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "============================================================================"
Write-Host "COMMAND 3: python -m pip list | findstr (fastapi discord uvicorn)"
Write-Host "============================================================================"
python -m pip list | findstr /I "fastapi discord uvicorn"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Command 3 may have returned no matches or failed"
}

Write-Host ""
Write-Host "============================================================================"
Write-Host "COMMAND 4: python -m pip install -e ."
Write-Host "============================================================================"
python -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Command 4 failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "============================================================================"
Write-Host "COMMAND 5: python -m unittest discover -s tests -p test_*.py -v"
Write-Host "============================================================================"
python -m unittest discover -s tests -p test_*.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Command 5 failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "============================================================================"
Write-Host "WORKFLOW EXECUTION COMPLETE"
Write-Host "============================================================================"

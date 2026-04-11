@echo off
REM Execute the profile-machine.ps1 PowerShell script
REM This script collects all machine facts including CPU, RAM, GPU, disks, network, and tools

cd /d d:\JemmaRepo\Jemma

REM Run with Windows PowerShell 5.x (the default powershell.exe on Windows)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "toolbox\windows\profile-machine.ps1" -AsJson > machine_profile.json

echo.
echo Profile collection complete. Output saved to machine_profile.json
echo.
type machine_profile.json

REM Also run without JSON for human-readable output
echo.
echo.
echo ============================================================
echo HUMAN-READABLE OUTPUT:
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "toolbox\windows\profile-machine.ps1"

@echo off
REM Android Studio JAR Inspector Batch Script
REM This script inspects three JAR files without extracting them
REM Uses Python's zipfile module for read-only access

echo.
echo ========================================
echo Android Studio JAR Inspector
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python or add it to your system PATH
    pause
    exit /b 1
)

echo Running JAR inspection script...
echo.

REM Run the inspection script
python d:\JemmaRepo\Jemma\jar_inspector_final.py

echo.
echo Press any key to exit...
pause >nul

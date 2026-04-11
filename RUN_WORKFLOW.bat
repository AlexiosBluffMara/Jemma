@echo off
REM JEMMA Project Workflow Execution
REM Executes the 5-step workflow:
REM 1. python --version
REM 2. python -c (sys info)
REM 3. python -m pip list
REM 4. python -m pip install -e .
REM 5. python -m unittest discover

setlocal enabledelayedexpansion

set PYTHON_EXE=python
set REPO_DIR=D:\JemmaRepo\Jemma

cd /d "%REPO_DIR%"

cls
echo.
echo ============================================================================
echo JEMMA PROJECT WORKFLOW EXECUTION
echo ============================================================================
echo Working directory: %REPO_DIR%
echo Python: %PYTHON_EXE%
echo.
echo This script executes 5 commands to verify the Jemma project setup
echo ============================================================================
echo.

echo.
echo ============================================================================
echo COMMAND 1: Python Version
echo ============================================================================
%PYTHON_EXE% --version

echo.
echo ============================================================================
echo COMMAND 2: Python Executable and Prefix
echo ============================================================================
%PYTHON_EXE% -c "import sys; print('Executable:', sys.executable); print('Prefix:', sys.prefix)"

echo.
echo ============================================================================
echo COMMAND 3: Installed Packages (pip list)
echo ============================================================================
echo Looking for: fastapi, discord, uvicorn
echo.
%PYTHON_EXE% -m pip list

echo.
echo ============================================================================
echo COMMAND 4: Installing Project in Editable Mode (pip install -e .)
echo ============================================================================
%PYTHON_EXE% -m pip install -e .

echo.
echo ============================================================================
echo COMMAND 5: Running Tests (unittest discover)
echo ============================================================================
%PYTHON_EXE% -m unittest discover -s tests -p test_*.py -v

echo.
echo ============================================================================
echo WORKFLOW EXECUTION COMPLETE
echo ============================================================================
echo.
pause

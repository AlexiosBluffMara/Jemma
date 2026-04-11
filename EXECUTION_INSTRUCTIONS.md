# Jemma Workflow Execution Instructions

## Overview
This document provides instructions for executing the complete Jemma workflow as requested.

## Requested Workflow
Execute the Python script: `python D:\JemmaRepo\Jemma\inline_workflow.py`

The script will perform these 6 steps:
1. Run `python --version`
2. Run `python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"`
3. Run `python -m pip list` (full output - before installation)
4. Run `python -m pip install -e .` (install Jemma in editable mode with dependencies)
5. Run `python -m pip list` again (after installation - supplemental)
6. Run `python -m unittest discover -s tests -p test_*.py -v` (run all tests)

The script generates a detailed report at: `D:\JemmaRepo\Jemma\workflow_report.txt`

## Execution Methods

### Method 1: Direct Python Execution (RECOMMENDED)
```bash
cd /d D:\JemmaRepo\Jemma
python inline_workflow.py
```

Expected output:
- Live console output showing each step's execution
- Generated `workflow_report.txt` with full results
- Summary at the end with test counts and package information

Expected duration: 5-15 minutes
- pip list: ~30 seconds
- pip install: 2-5 minutes
- unittest discover: 1-10 minutes

### Method 2: Using the Batch File
```bash
cd /d D:\JemmaRepo\Jemma
RUN_WORKFLOW.bat
```

This alternative batch file runs the same steps and will pause at the end for review.

### Method 3: Manual Step-by-Step Execution
Execute each command individually in Command Prompt:

```batch
cd /d D:\JemmaRepo\Jemma

echo === Step 1: Python Version ===
python --version

echo === Step 2: Interpreter Info ===
python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"

echo === Step 3: Pip List (Before) ===
python -m pip list

echo === Step 4: Install Dependencies ===
python -m pip install -e .

echo === Step 5: Pip List (After) ===
python -m pip list

echo === Step 6: Run Tests ===
python -m unittest discover -s tests -p test_*.py -v
```

## Expected Results

### Step 1: Python Version
- Exit Code: 0
- Output: e.g., "Python 3.11.7"

### Step 2: Interpreter Info
- Exit Code: 0
- Output:
  ```
  Executable: C:\...\python.exe
  Version: sys.version_info(major=3, minor=11, micro=7, ...)
  ```

### Step 3: Pip List (Before)
- Exit Code: 0
- Output: List of currently installed packages
- Look for: fastapi, discord.py, uvicorn (may or may not be present)

### Step 4: Installation
- Exit Code: 0
- Output: Installation progress ending with:
  ```
  Successfully installed jemma-0.1.0 discord.py-2.4.0 fastapi-0.115.0 uvicorn-0.35.0 ...
  ```
- Expected packages to be installed:
  - discord.py >=2.4,<3
  - fastapi >=0.115,<1
  - uvicorn >=0.35,<1
  - Other dependencies (pydantic, etc.)

### Step 5: Pip List (After)
- Exit Code: 0
- Output: Updated list with newly installed packages visible
- Should now include: discord.py, fastapi, uvicorn

### Step 6: Test Execution
- Exit Code: 0 if all tests pass, 1+ if failures
- Output: verbose test listing with results
  ```
  test_agent_loop.py (test_basic_loop) ... ok
  test_api_app.py (test_app_creation) ... ok
  ...
  Ran X tests in Y.XXX seconds
  OK (or FAILED)
  ```

## Generated Report

After execution completes, the script generates: `D:\JemmaRepo\Jemma\workflow_report.txt`

This report contains:
- Full command output for each step
- Exit codes for each step
- Summary of packages before/after installation
- Test execution results with counts
- Any errors or failures

## Troubleshooting

### If Step 4 (Installation) fails:
- Verify network connectivity
- Check pyproject.toml exists in D:\JemmaRepo\Jemma
- Ensure pip is properly installed
- Try: `python -m pip install --upgrade pip`

### If Step 6 (Tests) fail:
- Some tests may require specific dependencies or environment setup
- Check test files in `tests/` directory for prerequisites
- Review stderr output for specific error messages

### If pip commands are slow:
- This is normal on first run or with slow network
- Wait for completion (may take 5+ minutes)

## Script File Location

The script is located at:
```
D:\JemmaRepo\Jemma\inline_workflow.py
```

## Environment Requirements

- Python 3.11 or later
- pip package manager
- Internet connection (for downloading packages)
- ~500MB disk space (for installations and cache)

## Summary

To execute the workflow:
1. Open Command Prompt
2. Navigate to: `cd /d D:\JemmaRepo\Jemma`
3. Run: `python inline_workflow.py`
4. Wait for completion (5-15 minutes)
5. Review results in: `D:\JemmaRepo\Jemma\workflow_report.txt`

---
Date: 2025-01-21
Status: Ready for Execution

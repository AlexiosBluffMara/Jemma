# JEMMA Project Workflow Execution Instructions

## Environment Information
- **Repository Location**: `D:\JemmaRepo\Jemma`
- **Python Virtual Environment**: `D:\unsloth\studio\.venv\Scripts\python.exe`
- **OS**: Windows

## Required Commands

Execute these 5 commands in the order listed below:

### COMMAND 1: Check Python Version
```batch
python --version
```

### COMMAND 2: Check Python Executable and Prefix
```batch
python -c "import sys; print('Executable:', sys.executable); print('Prefix:', sys.prefix)"
```

### COMMAND 3: List Installed Packages
```batch
python -m pip list
```
**Look for these packages in the output:**
- fastapi (>=0.115,<1)
- discord.py (>=2.4,<3)
- uvicorn (>=0.35,<1)

### COMMAND 4: Install Project in Editable Mode
```batch
cd D:\JemmaRepo\Jemma
python -m pip install -e .
```

### COMMAND 5: Run All Tests with Verbose Output
```batch
python -m unittest discover -s tests -p test_*.py -v
```

## Batch File Runner

A batch file has been prepared at: `D:\JemmaRepo\Jemma\WORKFLOW_RUNNER.bat`

This file can be executed directly from Command Prompt:
```batch
cd D:\JemmaRepo\Jemma
WORKFLOW_RUNNER.bat
```

## Python Script Runner

Alternatively, a Python script has been prepared at: `D:\JemmaRepo\Jemma\exec_workflow_final.py`

Execute it using:
```batch
python D:\JemmaRepo\Jemma\exec_workflow_final.py
```

Or with the Unsloth environment Python:
```batch
D:\unsloth\studio\.venv\Scripts\python.exe D:\JemmaRepo\Jemma\exec_workflow_final.py
```

## Expected Output Information

### From Command 1 (--version)
- Should show Python version (expected: Python 3.11+)

### From Command 2 (sys info)
- **Executable**: Full path to python.exe being used
- **Prefix**: Root directory of Python installation

### From Command 3 (pip list)
- Full list of installed packages with versions
- Look for fastapi, discord, uvicorn in the list
- Note which dependencies are already installed vs fresh

### From Command 4 (pip install -e .)
- Should show "Successfully installed jemma" or similar
- List of dependencies that were installed or updated
- Any error messages if installation fails

### From Command 5 (unittest discover)
- Output line showing "Ran X tests"
- Summary showing "OK" or "FAILED"
- List of all tests executed with status (ok, error, fail)
- Any failure tracebacks if tests fail

## Project Structure

The project dependencies are defined in `pyproject.toml`:

```toml
[project]
name = "jemma"
version = "0.1.0"
description = "Autonomous local Gemma agent framework with benchmark orchestration."
requires-python = ">=3.11"

dependencies = [
    "discord.py>=2.4,<3",
    "fastapi>=0.115,<1",
    "uvicorn>=0.35,<1",
]
```

Tests are located in: `D:\JemmaRepo\Jemma\tests/`

Test files:
- test_agent_loop.py
- test_api_app.py
- test_benchmarks.py
- test_config_loader.py
- test_discord_blueprint.py
- test_job_manager.py
- test_policies.py
- test_store_queries.py

## Next Steps

1. Execute the workflow commands as listed above
2. Collect the complete output from each command
3. Note:
   - Python version and executable path
   - Which dependencies were already installed vs installed fresh
   - Full test output including all test results and any errors
   - Count of tests run and final pass/fail status

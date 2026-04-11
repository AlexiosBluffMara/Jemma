# NOTEBOOK EXECUTION INSTRUCTIONS

## SITUATION

You requested execution of the Gemma 4 + Unsloth notebook using the Unsloth Python environment. Due to system constraints, I have prepared everything needed for execution, but cannot execute the commands directly from this environment (which requires PowerShell 7+ that is not installed on this Windows system).

## IMMEDIATE NEXT STEPS

### Option 1: Run the Prepared Python Runner (RECOMMENDED)

This is the easiest option - just run one command:

```cmd
cd /d d:\JemmaRepo\Jemma
d:\unsloth\studio\.venv\Scripts\python.exe FINAL_NOTEBOOK_RUNNER.py
```

This script will:
1. ✓ Run: `d:\unsloth\studio\.venv\Scripts\python.exe --version`
2. ✓ Run: `d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"`
3. ✓ Run: `d:\unsloth\studio\.venv\Scripts\python.exe toolbox\run_notebook_cells.py gemma4-31b-unsloth-local-5090.ipynb`

**Total Duration:** 10-60+ minutes (mostly training step on GPU)

**Output:**
- Live console output showing progress
- `state/notebook-smoke/notebook_run_report.json` (from notebook runner)
- `state/notebook-smoke/notebook_execution_results.json` (from this script)

---

### Option 2: Run the Batch File

```cmd
cd /d d:\JemmaRepo\Jemma
run_all_commands.bat
```

This does the same thing as Option 1, but purely in batch/cmd.exe format.

---

### Option 3: Run Commands Manually

If you want to see each step individually:

```cmd
cd /d d:\JemmaRepo\Jemma

REM Command 1: Check Python version
d:\unsloth\studio\.venv\Scripts\python.exe --version

REM Command 2: Check dependencies
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"

REM Command 3: Run notebook (will take 10-60+ minutes)
d:\unsloth\studio\.venv\Scripts\python.exe toolbox\run_notebook_cells.py gemma4-31b-unsloth-local-5090.ipynb
```

---

## WHAT EACH COMMAND DOES

### Command 1: Python Version Check
```
d:\unsloth\studio\.venv\Scripts\python.exe --version
```

**Expected Output:**
```
Python 3.x.x
```

**Purpose:** Verify the Unsloth virtual environment has a working Python interpreter.

**Duration:** < 1 second

---

### Command 2: Dependency Verification
```
d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
```

**Expected Output (SUCCESS):**
```
all ok
```

**Expected Output (FAILURE - if packages missing):**
```
ModuleNotFoundError: No module named 'torch'
(or unsloth, datasets, trl, etc.)
```

**Purpose:** Verify all required ML packages are installed before attempting notebook execution.

**Duration:** 10-30 seconds

**If this fails:**
- Install missing packages: `pip install torch unsloth datasets trl accelerate`
- Re-run the command to verify
- If imports work, try Command 3

---

### Command 3: Notebook Execution
```
d:\unsloth\studio\.venv\Scripts\python.exe toolbox\run_notebook_cells.py gemma4-31b-unsloth-local-5090.ipynb
```

**What it does:**
1. Loads the notebook as JSON
2. Extracts code cells in order
3. Executes each cell with proper Python environment
4. Tracks progress through these phases:
   - `setup` - Initialize directories and environment
   - `deps_check` - Verify CUDA and packages
   - `model_load` - Load Gemma 4 model in 4-bit
   - `lora_attach` - Attach LoRA adapters
   - `dataset_load` - Load training dataset
   - `prompt_formatting` - Format prompts for training
   - `trainer_construction` - Initialize SFTTrainer
   - `train_step` - Run 1 training step (configurable)
   - `generation` - Generate text with trained model
   - `export` - Save adapters/model

**Expected Output:**
```
NOTEBOOK: d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb
PYTHON: d:\unsloth\studio\.venv\Scripts\python.exe
ENV: { ... environment variables ... }

=== CODE CELL 0 (notebook cell 2) :: setup ===
... setup output ...

=== CODE CELL 1 (notebook cell 3) :: deps_check ===
... dependency check output ...
Python: 3.x.x
Torch: 2.x.x
CUDA available: True
GPU: NVIDIA RTX 5090
...

=== CODE CELL 2 (notebook cell 4) :: model_load ===
... model loading output ...

... (more cells) ...

All notebook code cells executed successfully.
```

**Duration:** 10-60+ minutes depending on:
- First-time model download (5-10 minutes)
- GPU performance
- Number of training steps (1 by default)
- Dataset size

**Output Files:**
- Console output (same as above)
- `state/notebook-smoke/notebook_run_report.json` (JSON report with phases and status)

---

## IF SOMETHING FAILS

### Check the Report

After execution completes (or fails), check:

```cmd
type state\notebook-smoke\notebook_run_report.json
```

This JSON file contains:
- `python_executable`: Which Python was used
- `python_version`: Exact Python version
- `phases`: Status of each phase (ok, failed, pending, running)
- `first_failure`: Details of the first error (if any), including:
  - `phase`: Which phase failed
  - `code_cell_index`: Which code cell (0-indexed)
  - `notebook_cell_index`: Position in notebook
  - `traceback`: Full Python traceback

### Common Failures & Recovery

#### 1. ModuleNotFoundError: No module named 'torch'

**Cause:** Dependencies not installed in venv

**Fix:**
```cmd
d:\unsloth\studio\.venv\Scripts\pip install torch unsloth datasets trl accelerate
```

Then re-run the notebook execution command.

---

#### 2. CUDA is required for this notebook

**Cause:** NVIDIA GPU not detected or not properly configured

**Fix:**
- Verify GPU: `nvidia-smi`
- Verify CUDA is installed
- On Windows, ensure GPU drivers are up-to-date
- Consider running in WSL2 if on Windows (more reliable)

---

#### 3. OutOfMemoryError

**Cause:** Insufficient GPU VRAM

**Options:**
- Use smaller model: Set `JEMMA_MODEL_NAME=unsloth/gemma-4-E2B-it` (instead of 31B)
- Reduce batch size: Set `JEMMA_BATCH_SIZE=1`
- Free other GPU memory: Close other GPU applications

---

#### 4. HuggingFace Hub connection error

**Cause:** Cannot download model from Hugging Face

**Fix:**
- Verify internet connection
- If behind proxy, configure HF credentials:
```cmd
huggingface-cli login
```

---

### Debugging a Specific Phase

If you know which phase failed, you can:

1. Read the notebook cell that corresponds to that phase
2. Look at the traceback in notebook_run_report.json
3. Identify the failing line
4. Fix the notebook or environment
5. Re-run the command (it will re-execute all cells)

---

## ENVIRONMENT VARIABLES

The notebook runner uses these defaults (can be overridden):

```cmd
REM Set environment variables before running

set JEMMA_WORKSPACE_DIR=d:\JemmaRepo\Jemma
set JEMMA_DATA_DIR=d:\JemmaRepo\Jemma\state\notebook-smoke
set JEMMA_MODEL_NAME=unsloth/gemma-4-E2B-it
set JEMMA_MAX_SEQ_LENGTH=512
set JEMMA_SMOKE_TEST_ROWS=8
set JEMMA_BATCH_SIZE=1
set JEMMA_GRAD_ACC=1
set JEMMA_EPOCHS=1
set JEMMA_MAX_STEPS=1
set JEMMA_WARMUP_STEPS=0
set JEMMA_LOGGING_STEPS=1
set JEMMA_SAVE_STEPS=1000
set JEMMA_SAVE_TOTAL_LIMIT=1
set JEMMA_GEN_MAX_NEW_TOKENS=64
set JEMMA_SAVE_MERGED_16BIT=0
set JEMMA_SAVE_GGUF=0

REM Then run the notebook
d:\unsloth\studio\.venv\Scripts\python.exe FINAL_NOTEBOOK_RUNNER.py
```

---

## IMPORTANT NOTES

1. **GPU Access:** This notebook requires an NVIDIA GPU with CUDA support. RTX 5090 is ideal but any capable GPU will work.

2. **Memory:** At least 24 GB VRAM recommended for 31B model. Consider using E2B (smaller) for testing.

3. **Time:** Full execution (including model download) can take 1-2 hours on first run. Subsequent runs are faster (model cached).

4. **Interruption:** If you press Ctrl+C during execution, you can re-run the command. It will restart from the beginning (or from where it was interrupted, depending on the phase).

5. **Dataset:** The smoke test uses a small 8-row dataset for quick validation. See JEMMA_SMOKE_TEST_ROWS environment variable.

6. **Network:** Required for first-time model download from Hugging Face Hub (~13GB for 31B model).

---

## SUCCESS CRITERIA

You'll know the notebook executed successfully when you see:

1. **Return Code: 0**
   ```cmd
   echo %errorlevel%
   REM Should print: 0
   ```

2. **Console Output:**
   ```
   All notebook code cells executed successfully.
   ```

3. **Report File:**
   ```cmd
   type state\notebook-smoke\notebook_run_report.json
   REM All phases should show "ok", no "first_failure"
   ```

4. **Output Files:**
   - Model exports in: `state/notebook-smoke/exports/`
   - Training checkpoints in: `state/notebook-smoke/runs/`
   - Logs in: `state/notebook-smoke/logs/`

---

## FILES PREPARED

1. **FINAL_NOTEBOOK_RUNNER.py** (RECOMMENDED)
   - Complete runner with detailed logging
   - Handles timeouts, errors, JSON reports
   - Run with: `python FINAL_NOTEBOOK_RUNNER.py`

2. **run_all_commands.bat**
   - Batch file version of runner
   - Simpler than Python script
   - Run with: `run_all_commands.bat`

3. **execute_notebook.py**
   - Alternative Python runner
   - Similar functionality to FINAL_NOTEBOOK_RUNNER.py

4. **NOTEBOOK_EXECUTION_AUDIT.txt**
   - Comprehensive documentation
   - Expected phases and outcomes
   - Troubleshooting guide

5. **tests/test_notebook_execution.py**
   - Unit test that runs the commands
   - Can be run with: `python -m unittest tests.test_notebook_execution`

---

## NEXT STEPS

1. **Choose your execution method** (Option 1, 2, or 3 from above)

2. **Run the command:**
   ```cmd
   cd /d d:\JemmaRepo\Jemma
   d:\unsloth\studio\.venv\Scripts\python.exe FINAL_NOTEBOOK_RUNNER.py
   ```

3. **Wait for completion** (10-60+ minutes)

4. **Check results:**
   ```cmd
   type state\notebook-smoke\notebook_run_report.json
   ```

5. **If successful:** Notebook is now trained and ready for use!

6. **If failed:** Review the report and fix the issue, then re-run

---

## SUPPORT

If you encounter issues:

1. Check `state/notebook-smoke/notebook_run_report.json` for the exact error
2. Review the "IF SOMETHING FAILS" section above
3. Check the traceback for the failing line
4. Verify dependencies are installed
5. Verify GPU is available and CUDA is working
6. Consult Unsloth documentation: https://github.com/unslothai/unsloth

---

**You are now ready to execute the notebook. Run the command above and monitor progress.**

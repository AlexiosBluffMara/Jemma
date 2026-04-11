#!/usr/bin/env python3
"""
NOTEBOOK EXECUTION RUNNER
=========================

This script executes all three required commands for the Gemma 4 + Unsloth notebook training.

USAGE:
  d:\unsloth\studio\.venv\Scripts\python.exe this_script.py

WHAT IT DOES:
  1. Runs: d:\unsloth\studio\.venv\Scripts\python.exe --version
  2. Runs: d:\unsloth\studio\.venv\Scripts\python.exe -c "import torch, unsloth, datasets, trl; print('all ok')"
  3. Runs: d:\unsloth\studio\.venv\Scripts\python.exe toolbox\run_notebook_cells.py gemma4-31b-unsloth-local-5090.ipynb
  
OUTPUT:
  - Prints detailed progress to console
  - Creates JSON report: state/notebook-smoke/notebook_run_report.json (from notebook runner)
  - Creates JSON results: state/notebook-smoke/notebook_execution_results.json (from this script)

TIMING:
  - Command 1: < 1 second
  - Command 2: 10-30 seconds
  - Command 3: 10-60+ minutes (training depends on GPU, model size, number of steps)
  TOTAL: 10-65+ minutes

REQUIREMENTS:
  - Python 3.8+
  - Unsloth environment with torch, unsloth, datasets, trl installed
  - CUDA-enabled GPU (RTX 5090 recommended)
  - 24+ GB VRAM
  - Network access to Hugging Face Hub (for model download on first run)

ERROR HANDLING:
  - If any command fails, the script captures the error and saves it to JSON
  - The notebook_run_report.json will contain the exact failure point and traceback
  - Script exits with RC=1 if any command fails, RC=0 if all succeed
"""

import subprocess
import sys
import json
import traceback
import os
from pathlib import Path
from datetime import datetime, timedelta


def log(msg="", level="INFO", end="\n"):
    """Log a message with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if msg:
        print(f"[{ts}] [{level}] {msg}", end=end, flush=True)
    else:
        print(msg, end=end, flush=True)


def run_command(cmd, cmd_name, timeout=None):
    """
    Run a command and capture output.
    
    Args:
        cmd: List of command arguments
        cmd_name: Descriptive name for logging
        timeout: Timeout in seconds (None for no timeout)
    
    Returns:
        Tuple of (success: bool, output: str, returncode: int, error: str)
    """
    log(f"\n{'='*80}")
    log(f"EXECUTING: {cmd_name}", level="CMD")
    log(f"{'='*80}")
    log(f"Command: {' '.join(cmd)}")
    log()
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=r"d:\JemmaRepo\Jemma"
        )
        
        elapsed = datetime.now() - start_time
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        
        # Log output (limit size for large outputs)
        if len(output) > 5000:
            log(output[:2500])
            log(f"\n... [truncated, total length: {len(output)} chars] ...\n")
            log(output[-2500:])
        else:
            log(output)
        
        log(f"Return Code: {result.returncode}")
        log(f"Elapsed Time: {elapsed}")
        
        success = result.returncode == 0
        status = "✓ PASSED" if success else "✗ FAILED"
        log(f"Status: {status}", level="RESULT")
        
        return success, output, result.returncode, None
        
    except subprocess.TimeoutExpired as e:
        elapsed = datetime.now() - start_time
        log(f"TIMEOUT: Command exceeded {timeout} seconds", level="ERROR")
        log(f"Elapsed Time: {elapsed}")
        return False, "", -1, f"Command timed out after {timeout} seconds"
        
    except Exception as e:
        log(f"EXCEPTION: {e}", level="ERROR")
        log(traceback.format_exc())
        return False, "", -2, str(e)


def main():
    log()
    log("="*80)
    log("GEMMA 4 + UNSLOTH NOTEBOOK EXECUTION RUNNER", level="MAIN")
    log("="*80)
    log(f"Start Time: {datetime.now().isoformat()}")
    log()
    
    # Setup
    repo_root = Path(r"d:\JemmaRepo\Jemma")
    py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
    notebook = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
    runner = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
    report_path = repo_root / "state" / "notebook-smoke" / "notebook_run_report.json"
    results_path = repo_root / "state" / "notebook-smoke" / "notebook_execution_results.json"
    
    # Ensure output directory exists
    results_path.parent.mkdir(parents=True, exist_ok=True)
    
    results = {
        "start_time": datetime.now().isoformat(),
        "script_version": "1.0",
        "python_exe": py_exe,
        "notebook": notebook,
        "repo_root": str(repo_root),
        "commands": {},
        "summary": {}
    }
    
    # COMMAND 1: Python Version
    log("\n" + "="*80)
    log("PHASE 1: PYTHON VERSION CHECK", level="PHASE")
    log("="*80)
    success1, output1, rc1, error1 = run_command(
        [py_exe, "--version"],
        "Check Python version in Unsloth environment",
        timeout=30
    )
    results["commands"]["cmd1_version"] = {
        "success": success1,
        "return_code": rc1,
        "output": output1[:5000],
        "error": error1
    }
    
    # COMMAND 2: Dependency Check
    log("\n" + "="*80)
    log("PHASE 2: DEPENDENCY CHECK", level="PHASE")
    log("="*80)
    success2, output2, rc2, error2 = run_command(
        [py_exe, "-c", "import torch, unsloth, datasets, trl; print('all ok')"],
        "Verify torch, unsloth, datasets, trl are installed and importable",
        timeout=120
    )
    results["commands"]["cmd2_deps"] = {
        "success": success2,
        "return_code": rc2,
        "output": output2[:5000],
        "error": error2
    }
    
    # Check dependency status before proceeding
    if not success2:
        log("\n" + "="*80)
        log("⚠️  DEPENDENCY CHECK FAILED", level="WARN")
        log("="*80)
        log("One or more required packages are missing or not importable:")
        log("  - torch (PyTorch)")
        log("  - unsloth (Unsloth optimization library)")
        log("  - datasets (Hugging Face datasets)")
        log("  - trl (Transformer Reinforcement Learning)")
        log("")
        log("RECOVERY:")
        log("  Install missing packages in the Unsloth venv:")
        log("  cd d:\\unsloth\\studio")
        log("  .venv\\Scripts\\pip install torch unsloth datasets trl")
        log("")
        results["summary"]["status"] = "BLOCKED_BY_DEPS"
        results["summary"]["message"] = "Dependency check failed - cannot proceed to notebook execution"
        results["end_time"] = datetime.now().isoformat()
        results_path.write_text(json.dumps(results, indent=2))
        log(f"Results saved to: {results_path}")
        return 1
    
    # COMMAND 3: Notebook Execution (the long-running one)
    log("\n" + "="*80)
    log("PHASE 3: NOTEBOOK EXECUTION", level="PHASE")
    log("="*80)
    log("⏳ IMPORTANT: This will take 10-60+ minutes depending on:")
    log("   - Model loading time (first time: 5-10 minutes)")
    log("   - GPU VRAM and speed")
    log("   - Number of training steps (1 step by default)")
    log("   - Dataset size")
    log("")
    log("Do NOT interrupt this process.")
    log("")
    
    success3, output3, rc3, error3 = run_command(
        [py_exe, runner, notebook],
        "Execute notebook cells through run_notebook_cells.py",
        timeout=4000  # 66+ minutes to be safe
    )
    results["commands"]["cmd3_notebook"] = {
        "success": success3,
        "return_code": rc3,
        "output_length": len(output3),
        "output_tail": output3[-2000:],
        "error": error3
    }
    
    # Check for notebook run report
    if report_path.exists():
        log(f"\n📋 Notebook run report found at: {report_path}")
        try:
            with open(report_path, 'r') as f:
                notebook_report = json.load(f)
            results["notebook_report"] = notebook_report
            
            log("\n" + "="*80)
            log("NOTEBOOK RUN REPORT SUMMARY", level="INFO")
            log("="*80)
            
            if "first_failure" in notebook_report and notebook_report["first_failure"]:
                log(f"❌ FAILURE DETECTED")
                log(f"   Phase: {notebook_report['first_failure'].get('phase', 'UNKNOWN')}")
                log(f"   Code Cell: {notebook_report['first_failure'].get('code_cell_index', 'N/A')}")
                log(f"   Error: {notebook_report['first_failure'].get('traceback', '')[:500]}")
            else:
                log(f"✓ All phases completed successfully")
                for phase, status in notebook_report.get("phases", {}).items():
                    log(f"   {phase}: {status}")
        except Exception as e:
            log(f"⚠️  Could not parse notebook report: {e}")
    else:
        log(f"❌ Notebook run report NOT found (expected at {report_path})")
        log("   This usually means the notebook execution failed before creating the report.")
    
    # Final summary
    log("\n" + "="*80)
    log("EXECUTION SUMMARY", level="MAIN")
    log("="*80)
    
    cmd1_status = "✓ PASS" if success1 else "✗ FAIL"
    cmd2_status = "✓ PASS" if success2 else "✗ FAIL"
    cmd3_status = "✓ PASS" if success3 else "✗ FAIL"
    
    log(f"Command 1 (Python Version): {cmd1_status} (RC={rc1})")
    log(f"Command 2 (Dependencies):   {cmd2_status} (RC={rc2})")
    log(f"Command 3 (Notebook):       {cmd3_status} (RC={rc3})")
    
    overall_success = success1 and success2 and success3
    overall_status = "✓ ALL PASSED" if overall_success else "✗ SOME FAILED"
    log()
    log(f"Overall Status: {overall_status}")
    
    # Determine phase status
    if not overall_success:
        if not success1:
            results["summary"]["phase"] = "python_check"
            results["summary"]["message"] = "Python version check failed"
        elif not success2:
            results["summary"]["phase"] = "deps_check"
            results["summary"]["message"] = "Dependency check failed"
        else:
            results["summary"]["phase"] = "notebook_execution"
            results["summary"]["message"] = "Notebook execution failed - see notebook_run_report.json"
    else:
        results["summary"]["phase"] = "completed"
        results["summary"]["message"] = "All phases completed successfully"
    
    log(f"Phase: {results['summary']['phase']}")
    log(f"Message: {results['summary']['message']}")
    
    # Save results
    log()
    log("="*80)
    log("SAVING RESULTS", level="INFO")
    log("="*80)
    results["end_time"] = datetime.now().isoformat()
    results["success"] = overall_success
    results_path.write_text(json.dumps(results, indent=2))
    log(f"Results saved to: {results_path}")
    log(f"Report saved to:  {report_path}")
    
    log()
    log("="*80)
    log("DONE", level="MAIN")
    log("="*80)
    log(f"End Time: {datetime.now().isoformat()}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("\n\n❌ INTERRUPTED BY USER", level="ERROR")
        sys.exit(130)
    except Exception as e:
        log(f"\n\n❌ FATAL ERROR: {e}", level="ERROR")
        log(traceback.format_exc())
        sys.exit(2)

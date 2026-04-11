import unittest
import subprocess
from pathlib import Path

class NotebookExecutionTest(unittest.TestCase):
    """Test that executes the notebook."""
    
    def test_execute_notebook(self):
        """Execute the three required commands."""
        py_exe = r"d:\unsloth\studio\.venv\Scripts\python.exe"
        notebook = r"d:\JemmaRepo\Jemma\gemma4-31b-unsloth-local-5090.ipynb"
        runner = r"d:\JemmaRepo\Jemma\toolbox\run_notebook_cells.py"
        
        # Command 1: Version
        print("\n" + "="*80)
        print("COMMAND 1: Python Version")
        print("="*80)
        r1 = subprocess.run([py_exe, "--version"], capture_output=True, text=True)
        print(r1.stdout, r1.stderr)
        self.assertEqual(r1.returncode, 0, f"Python version check failed: {r1.stderr}")
        
        # Command 2: Dependencies
        print("\n" + "="*80)
        print("COMMAND 2: Check Dependencies")
        print("="*80)
        r2 = subprocess.run(
            [py_exe, "-c", "import torch, unsloth, datasets, trl; print('all ok')"],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(r2.stdout, r2.stderr)
        self.assertIn("all ok", r2.stdout, f"Dependency check failed: {r2.stderr}")
        
        # Command 3: Notebook
        print("\n" + "="*80)
        print("COMMAND 3: Execute Notebook")
        print("(This will take 10-60+ minutes)")
        print("="*80)
        r3 = subprocess.run(
            [py_exe, runner, notebook],
            capture_output=True,
            text=True,
            timeout=4000
        )
        # Print last portion
        print(r3.stdout[-3000:] if len(r3.stdout) > 3000 else r3.stdout)
        if r3.stderr:
            print("STDERR:", r3.stderr[-1000:])
        
        # Check report
        report_path = Path(r"d:\JemmaRepo\Jemma\state\notebook-smoke\notebook_run_report.json")
        if report_path.exists():
            import json
            report = json.loads(report_path.read_text())
            print("\n" + "="*80)
            print("NOTEBOOK RUN REPORT")
            print("="*80)
            print(json.dumps(report, indent=2)[:2000])
        
        # Assert success
        self.assertEqual(r3.returncode, 0, f"Notebook execution failed with RC={r3.returncode}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

import unittest
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jemma.notebook_support import build_notebook_paths, resolve_python_executable

class NotebookExecutionTest(unittest.TestCase):
    """Test that executes the notebook."""
    
    def test_execute_notebook(self):
        """Execute the three required commands."""
        repo_root = Path(__file__).resolve().parents[1]
        paths = build_notebook_paths(repo_root)
        py_exe_path = resolve_python_executable(repo_root)
        if py_exe_path is None:
            self.skipTest("No notebook Python environment found. Set JEMMA_NOTEBOOK_PYTHON or create the expected Unsloth venv.")
        notebook = str(paths["notebook"])
        runner = str(paths["runner"])
        py_exe = str(py_exe_path)
        
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
            [py_exe, "-c", "import torch, unsloth, datasets, trl, transformers, accelerate; print('all ok')"],
            capture_output=True,
            text=True,
            timeout=120
        )
        print(r2.stdout, r2.stderr)
        if r2.returncode != 0:
            self.skipTest(f"Notebook environment is present but missing training dependencies: {r2.stderr.strip()}")
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
        report_path = paths["report_path"]
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

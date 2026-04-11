#!/usr/bin/env python3
"""
JEMMA Workflow Executor - Comprehensive test runner
Captures complete output of all workflow steps
"""

import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Configuration
REPO_DIR = Path(r"D:\JemmaRepo\Jemma")
OUTPUT_FILE = REPO_DIR / "WORKFLOW_EXECUTION_OUTPUT.txt"

# Change to repo directory
os.chdir(REPO_DIR)

class WorkflowExecutor:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "working_directory": str(os.getcwd()),
            "python_executable": sys.executable,
            "commands": []
        }
        self.output = []
    
    def log(self, text):
        """Log text to both console and output list"""
        print(text)
        self.output.append(text)
    
    def run_command(self, step_num, description, cmd_args, use_shell=False):
        """Execute a command and capture output"""
        self.log("")
        self.log("=" * 90)
        self.log(f"STEP {step_num}: {description}")
        self.log("=" * 90)
        
        # Log the command
        if use_shell:
            cmd_str = cmd_args if isinstance(cmd_args, str) else " ".join(cmd_args)
        else:
            cmd_str = " ".join(cmd_args) if isinstance(cmd_args, list) else str(cmd_args)
        self.log(f"Command: {cmd_str}")
        self.log("")
        
        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                shell=use_shell,
                cwd=str(REPO_DIR)
            )
            
            if result.stdout:
                self.log("STDOUT:")
                self.log(result.stdout)
            
            if result.stderr:
                self.log("STDERR:")
                self.log(result.stderr)
            
            self.log(f"Exit Code: {result.returncode}")
            
            self.results["commands"].append({
                "step": step_num,
                "description": description,
                "command": cmd_str,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            })
            
            return result
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            self.log(error_msg)
            self.results["commands"].append({
                "step": step_num,
                "description": description,
                "command": cmd_str,
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "success": False
            })
            return None
    
    def execute_workflow(self):
        """Execute the complete workflow"""
        self.log("=" * 90)
        self.log("JEMMA PROJECT WORKFLOW EXECUTION")
        self.log("=" * 90)
        self.log(f"Timestamp: {self.results['timestamp']}")
        self.log(f"Working Directory: {self.results['working_directory']}")
        self.log(f"Python Executable: {self.results['python_executable']}")
        self.log("")
        
        # Step 1: Python version
        result1 = self.run_command(
            1,
            "python --version",
            [sys.executable, "--version"]
        )
        
        # Step 2: Python executable and version info
        result2 = self.run_command(
            2,
            "python -c (import sys; print info)",
            [sys.executable, "-c", "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"]
        )
        
        # Step 3: pip list with filtering (custom implementation for Windows)
        self.log("")
        self.log("=" * 90)
        self.log("STEP 3: python -m pip list | findstr /I 'fastapi discord uvicorn'")
        self.log("=" * 90)
        self.log("Command: python -m pip list | findstr /I \"fastapi discord uvicorn\"")
        self.log("")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                cwd=str(REPO_DIR)
            )
            
            packages_found = []
            if result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(pkg in line.lower() for pkg in ['fastapi', 'discord', 'uvicorn']):
                        self.log(line)
                        packages_found.append(line.strip())
            
            if not packages_found:
                self.log("No matching packages found (they may not be installed yet)")
            
            self.log(f"Exit Code: {result.returncode}")
            
            self.results["commands"].append({
                "step": 3,
                "description": "python -m pip list | findstr",
                "command": "python -m pip list | findstr /I \"fastapi discord uvicorn\"",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "packages_found": packages_found,
                "success": True
            })
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log(error_msg)
            self.results["commands"].append({
                "step": 3,
                "description": "python -m pip list | findstr",
                "exit_code": -1,
                "stderr": error_msg,
                "success": False
            })
        
        # Step 4: Install project
        result4 = self.run_command(
            4,
            "python -m pip install -e .",
            [sys.executable, "-m", "pip", "install", "-e", "."]
        )
        
        # Step 5: Run tests
        result5 = self.run_command(
            5,
            "python -m unittest discover -s tests -p test_*.py -v",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"]
        )
        
        # Print final summary
        self.log("")
        self.log("=" * 90)
        self.log("WORKFLOW EXECUTION SUMMARY")
        self.log("=" * 90)
        
        successful = sum(1 for cmd in self.results["commands"] if cmd["success"])
        total = len(self.results["commands"])
        
        self.log(f"Total Commands: {total}")
        self.log(f"Successful: {successful}")
        self.log(f"Failed: {total - successful}")
        self.log("")
        
        for cmd in self.results["commands"]:
            status = "✓ PASS" if cmd["success"] else "✗ FAIL"
            self.log(f"{status} - Step {cmd['step']}: {cmd['description']} (Exit: {cmd['exit_code']})")
        
        # Test summary from step 5
        if result5 and result5.stdout:
            lines = result5.stdout.split('\n')
            for line in lines[-20:]:  # Last 20 lines usually contain summary
                if any(keyword in line for keyword in ['Ran', 'FAILED', 'OK', 'Error']):
                    self.log(line)
        
        self.log("")
        self.log("=" * 90)
        self.log("END OF WORKFLOW EXECUTION")
        self.log("=" * 90)
    
    def save_output(self):
        """Save output to file"""
        output_text = "\n".join(self.output)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output_text)
        
        print(f"\n\nFull output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    executor = WorkflowExecutor()
    executor.execute_workflow()
    executor.save_output()

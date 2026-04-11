#!/usr/bin/env python3
"""Validation script for backend API and frontend stack."""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None, description=""):
    """Run a command and return success status with output."""
    print(f"\n{'='*60}")
    print(f"Running: {description or ' '.join(cmd)}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("✓ SUCCESS")
            if result.stdout:
                print(result.stdout[:500])
            return True, result.stdout + result.stderr
        else:
            print("✗ FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("✗ TIMEOUT (300s exceeded)")
        return False, "Command timeout"
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False, str(e)

def main():
    repo_root = Path("D:\\JemmaRepo\\Jemma")
    web_root = repo_root / "web"
    
    # Step 1: Display file contents
    print("\n" + "="*60)
    print("STEP 1: Inspecting pyproject.toml and web/package.json")
    print("="*60)
    print("\npyproject.toml preview:")
    print((repo_root / "pyproject.toml").read_text()[:500])
    print("\nweb/package.json preview:")
    print((web_root / "package.json").read_text()[:500])
    
    # Step 2: Install Python dependencies
    print("\n" + "="*60)
    print("STEP 2: Installing Python dependencies")
    print("="*60)
    success, output = run_command(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(repo_root),
        description="pip install -e . (backend dependencies)"
    )
    if not success:
        print(f"\n✗ Python dependency installation FAILED")
        print("Output:", output)
        return False
    
    # Step 3: Run Python tests
    print("\n" + "="*60)
    print("STEP 3: Running Python unittest suite")
    print("="*60)
    success, output = run_command(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        cwd=str(repo_root),
        description="python -m unittest discover (run tests)"
    )
    if not success:
        print(f"\n✗ Python tests FAILED")
        print("Full output:")
        print(output)
        return False
    print("\nTest output:")
    print(output)
    
    # Step 4: Install frontend dependencies
    print("\n" + "="*60)
    print("STEP 4: Installing frontend dependencies")
    print("="*60)
    success, output = run_command(
        ["npm", "install", "--prefer-offline"],
        cwd=str(web_root),
        description="npm install (frontend dependencies)"
    )
    if not success:
        print(f"\n✗ Frontend dependency installation FAILED")
        print("Output:", output)
        return False
    
    # Step 5: Run frontend build
    print("\n" + "="*60)
    print("STEP 5: Running frontend build")
    print("="*60)
    success, output = run_command(
        ["npm", "run", "build"],
        cwd=str(web_root),
        description="npm run build (frontend build)"
    )
    if not success:
        print(f"\n✗ Frontend build FAILED")
        print("Full output:")
        print(output)
        return False
    print("\nBuild output:")
    print(output)
    
    # All succeeded
    print("\n" + "="*60)
    print("✓ ALL VALIDATION STEPS PASSED")
    print("="*60)
    print("\nSummary:")
    print("  ✓ Python dependencies installed")
    print("  ✓ Python unittest suite passed")
    print("  ✓ Frontend dependencies installed")
    print("  ✓ Frontend build succeeded")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python
"""Validation script for Discord setup additions."""
import subprocess
import sys
import json

def run_tests():
    """Run the test suite."""
    print("=" * 70)
    print("RUNNING PYTEST TEST SUITE")
    print("=" * 70)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd="D:\\JemmaRepo\\Jemma"
    )
    return result.returncode == 0

def run_cli_checks():
    """Run CLI checks."""
    print("\n" + "=" * 70)
    print("RUNNING CLI CHECKS")
    print("=" * 70)
    
    # Check 1: discord-setup-check
    print("\n[CLI Check 1] discord-setup-check")
    print("-" * 70)
    result1 = subprocess.run(
        [sys.executable, "-c", 
         "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd() / 'src')); from jemma.cli import main; main(['discord-setup-check'])"],
        cwd="D:\\JemmaRepo\\Jemma"
    )
    
    # Check 2: discord-oauth-url
    print("\n[CLI Check 2] discord-oauth-url with test credentials")
    print("-" * 70)
    result2 = subprocess.run(
        [sys.executable, "-c", 
         "import sys; from pathlib import Path; sys.path.insert(0, str(Path.cwd() / 'src')); from jemma.cli import main; main(['discord-oauth-url','--client-id','123456','--guild-id','654321'])"],
        cwd="D:\\JemmaRepo\\Jemma"
    )
    
    return result1.returncode == 0 and result2.returncode == 0

if __name__ == "__main__":
    tests_passed = run_tests()
    cli_checks_passed = run_cli_checks()
    
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Tests passed: {tests_passed}")
    print(f"CLI checks passed: {cli_checks_passed}")
    
    if tests_passed and cli_checks_passed:
        print("\n✓ All validations passed!")
        sys.exit(0)
    else:
        print("\n✗ Some validations failed")
        sys.exit(1)

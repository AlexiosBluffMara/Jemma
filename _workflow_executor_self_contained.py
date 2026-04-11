#!/usr/bin/env python3
"""
Self-contained workflow executor.
This MUST work because it uses only stdlib and doesn't depend on any external tools.
"""

def main():
    import os
    import sys
    import subprocess
    from pathlib import Path
    from datetime import datetime
    
    os.chdir(r'd:\JemmaRepo\Jemma')
    repo_dir = Path.cwd()
    print(f"Working in: {repo_dir}")
    print(f"Python: {sys.executable}")
    
    # Cleanup phase
    print("\n" + "="*60)
    print("CLEANUP PHASE")
    print("="*60)
    
    FILES_TO_REMOVE = {
        'run_workflow_now.py', 'run_workflow_now.bat', 'START_EXECUTION.txt',
        'workflow_execution_guide.txt', 'WORKFLOW_INDEX.txt', 
        'environment_adaptation_report.txt', 'EXECUTION_READY.txt',
        '__temp_workflow_exec__.py', 'run_temp_workflow.bat', 'exec_workflow_inline.py',
        'run_workflow_exec.py', 'RUN.py', 'EXEC_NOW.cmd', 'run.cmd'
    }
    
    removed = 0
    for fname in FILES_TO_REMOVE:
        fpath = repo_dir / fname
        if fpath.exists():
            try:
                os.remove(fpath)
                removed += 1
                print(f"  Removed: {fname}")
            except Exception as e:
                print(f"  Error: {fname}: {e}")
    
    print(f"\nTotal cleaned: {removed} files")
    
    # Build report
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("JEMMA WORKFLOW EXECUTION REPORT")
    report_lines.append("=" * 70)
    report_lines.append(f"Timestamp: {datetime.now().isoformat()}")
    report_lines.append(f"Repository: {repo_dir}")
    report_lines.append(f"Python Executable: {sys.executable}")
    report_lines.append("")
    
    # STEP 1: python --version
    print("\nStep 1: python --version")
    report_lines.append("STEP 1: python --version")
    report_lines.append("-" * 70)
    try:
        result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True, shell=False)
        report_lines.append(f"Exit Code: {result.returncode}")
        report_lines.append(f"Output: {result.stdout.strip()}")
        print(f"  ✓ Exit Code: {result.returncode}")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # STEP 2: Interpreter info
    print("Step 2: Interpreter info")
    report_lines.append("STEP 2: Interpreter Information")
    report_lines.append("-" * 70)
    try:
        code = 'import sys; print("Executable:", sys.executable); print("Version:", sys.version_info)'
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, shell=False)
        report_lines.append(f"Exit Code: {result.returncode}")
        for line in result.stdout.strip().split('\n'):
            report_lines.append(f"  {line}")
        print(f"  ✓ Exit Code: {result.returncode}")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # STEP 3: pip list (before)
    print("Step 3: pip list (before)")
    report_lines.append("STEP 3: pip list (BEFORE install)")
    report_lines.append("-" * 70)
    before_pkgs = {}
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False, timeout=60)
        report_lines.append(f"Exit Code: {result.returncode}")
        if result.returncode == 0:
            for line in result.stdout.split('\n')[2:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        pkg = parts[0].lower()
                        ver = parts[1]
                        before_pkgs[pkg] = ver
                        if any(x in pkg for x in ['fastapi', 'discord', 'uvicorn']):
                            report_lines.append(f"  {pkg}=={ver}")
            report_lines.append(f"Total packages: {len(before_pkgs)}")
        print(f"  ✓ Exit Code: {result.returncode}, Total: {len(before_pkgs)}")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # STEP 4: pip install -e .
    print("Step 4: pip install -e .")
    report_lines.append("STEP 4: pip install -e .")
    report_lines.append("-" * 70)
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                               capture_output=True, text=True, shell=False, timeout=300, cwd=str(repo_dir))
        report_lines.append(f"Exit Code: {result.returncode}")
        if result.returncode == 0:
            report_lines.append("Status: SUCCESS")
        else:
            report_lines.append("Status: FAILED")
            # Show error
            for line in result.stderr.split('\n')[-20:]:
                if line.strip():
                    report_lines.append(f"  {line}")
        print(f"  ✓ Exit Code: {result.returncode}")
    except subprocess.TimeoutExpired:
        report_lines.append("ERROR: Timeout (>300s)")
        print(f"  ✗ Timeout")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # STEP 5: pip list (after)
    print("Step 5: pip list (after)")
    report_lines.append("STEP 5: pip list (AFTER install)")
    report_lines.append("-" * 70)
    after_pkgs = {}
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True, shell=False, timeout=60)
        report_lines.append(f"Exit Code: {result.returncode}")
        if result.returncode == 0:
            for line in result.stdout.split('\n')[2:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        pkg = parts[0].lower()
                        ver = parts[1]
                        after_pkgs[pkg] = ver
                        if any(x in pkg for x in ['fastapi', 'discord', 'uvicorn']):
                            report_lines.append(f"  {pkg}=={ver}")
            report_lines.append(f"Total packages: {len(after_pkgs)}")
            new_pkgs = set(after_pkgs.keys()) - set(before_pkgs.keys())
            if new_pkgs:
                report_lines.append(f"Newly installed: {len(new_pkgs)}")
        print(f"  ✓ Exit Code: {result.returncode}, Total: {len(after_pkgs)}")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # STEP 6: unittest discover
    print("Step 6: unittest discover")
    report_lines.append("STEP 6: unittest discover -s tests -p test_*.py -v")
    report_lines.append("-" * 70)
    try:
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', 
                                '-s', 'tests', '-p', 'test_*.py', '-v'],
                               capture_output=True, text=True, shell=False, timeout=120, cwd=str(repo_dir))
        report_lines.append(f"Exit Code: {result.returncode}")
        
        output = result.stdout + result.stderr
        test_total = 0
        test_pass = 0
        test_fail = 0
        test_error = 0
        
        for line in output.split('\n'):
            if ' ... ok' in line:
                test_total += 1
                test_pass += 1
            elif ' ... FAIL' in line:
                test_total += 1
                test_fail += 1
            elif ' ... ERROR' in line:
                test_total += 1
                test_error += 1
        
        # Find summary line
        for line in output.split('\n'):
            if 'Ran' in line or 'OK' in line or 'FAILED' in line:
                report_lines.append(f"  {line.strip()}")
        
        report_lines.append(f"Parsed: total={test_total}, pass={test_pass}, fail={test_fail}, error={test_error}")
        print(f"  ✓ Exit Code: {result.returncode}, Tests: {test_total} (pass={test_pass}, fail={test_fail}, error={test_error})")
    except subprocess.TimeoutExpired:
        report_lines.append("ERROR: Tests timed out (>120s)")
        print(f"  ✗ Timeout")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
        print(f"  ✗ ERROR: {e}")
    report_lines.append("")
    
    # Git status
    print("Git status...")
    report_lines.append("GIT STATUS")
    report_lines.append("-" * 70)
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, shell=False, cwd=str(repo_dir))
        lines = [l for l in result.stdout.split('\n') if l.strip()]
        tracked = [l for l in lines if l.startswith(('M ', 'D ', 'A '))]
        untracked = [l for l in lines if l.startswith('??')]
        report_lines.append(f"Tracked changes: {len(tracked)}")
        for line in tracked[:15]:
            report_lines.append(f"  {line}")
        if len(tracked) > 15:
            report_lines.append(f"  ... and {len(tracked)-15} more")
        print(f"  ✓ {len(tracked)} tracked changes, {len(untracked)} untracked")
    except Exception as e:
        report_lines.append(f"ERROR: {e}")
    report_lines.append("")
    
    # Final cleanup check
    report_lines.append("CLEANUP VERIFICATION")
    report_lines.append("-" * 70)
    remaining = [f for f in FILES_TO_REMOVE if (repo_dir / f).exists()]
    if remaining:
        report_lines.append(f"ERROR: Remaining files: {remaining}")
    else:
        report_lines.append("✓ All extra files removed")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 70)
    
    # Write report
    report_text = '\n'.join(report_lines)
    with open('workflow_report.txt', 'w') as f:
        f.write(report_text)
    
    print("\n✓ Report written to workflow_report.txt")
    
    # Cleanup self
    self_files = ['_workflow_executor_self_contained.py', '_execute_workflow.py', 'RUN.py', 'EXEC_NOW.cmd', 'run.cmd']
    print("Cleaning up temporary files...")
    for fname in self_files:
        fpath = repo_dir / fname
        if fpath.exists():
            try:
                os.remove(fpath)
                print(f"  Removed: {fname}")
            except:
                pass

if __name__ == '__main__':
    main()

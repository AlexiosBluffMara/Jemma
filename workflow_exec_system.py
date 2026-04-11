#!/usr/bin/env python3
"""Execute workflow using os.system()"""
import os
import sys

repo = r'D:\JemmaRepo\Jemma'
report = os.path.join(repo, 'workflow_report_system.txt')

os.chdir(repo)

# Collect all output
output = []

# Step 1
output.append("STEP 1: python --version\n")
output.append("=" * 80 + "\n")
os.system(f'python --version >> "{report}" 2>&1')
output.append("\n\n")

# Step 2
output.append("STEP 2: Python interpreter info\n")
output.append("=" * 80 + "\n")
os.system(f'python -c "import sys; print(\'Executable:\', sys.executable); print(\'Version:\', sys.version_info)" >> "{report}" 2>&1')
output.append("\n\n")

# Step 3
output.append("STEP 3: pip list (before install)\n")
output.append("=" * 80 + "\n")
os.system(f'python -m pip list >> "{report}" 2>&1')
output.append("\n\n")

# Step 4
output.append("STEP 4: pip install -e .\n")
output.append("=" * 80 + "\n")
os.system(f'python -m pip install -e . >> "{report}" 2>&1')
output.append("\n\n")

# Step 4 supplemental
output.append("STEP 4 SUPPLEMENTAL: pip list (after install)\n")
output.append("=" * 80 + "\n")
os.system(f'python -m pip list >> "{report}" 2>&1')
output.append("\n\n")

# Step 5
output.append("STEP 5: unittest discover\n")
output.append("=" * 80 + "\n")
os.system(f'python -m unittest discover -s tests -p test_*.py -v >> "{report}" 2>&1')

print(f"Report written to: {report}")

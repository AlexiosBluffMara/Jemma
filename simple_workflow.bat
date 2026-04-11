@echo off
REM Simple workflow runner that captures to files for parsing

setlocal enabledelayedexpansion

set REPO_DIR=D:\JemmaRepo\Jemma
cd /d "%REPO_DIR%"

REM Create output directory
if not exist "%REPO_DIR%\workflow_outputs" mkdir "%REPO_DIR%\workflow_outputs"

REM Step 1
echo Running Step 1: python --version
python --version > "%REPO_DIR%\workflow_outputs\step1.txt" 2>&1
echo Step 1 complete

REM Step 2
echo Running Step 2: sys info
python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)" > "%REPO_DIR%\workflow_outputs\step2.txt" 2>&1
echo Step 2 complete

REM Step 3
echo Running Step 3: pip list pre-install
python -m pip list > "%REPO_DIR%\workflow_outputs\step3.txt" 2>&1
echo Step 3 complete

REM Step 4
echo Running Step 4: pip install -e .
python -m pip install -e . > "%REPO_DIR%\workflow_outputs\step4.txt" 2>&1
echo Step 4 complete

REM Supplemental
echo Running Supplemental: pip list post-install
python -m pip list > "%REPO_DIR%\workflow_outputs\supplemental.txt" 2>&1
echo Supplemental complete

REM Step 5
echo Running Step 5: unittest discover
python -m unittest discover -s tests -p test_*.py -v > "%REPO_DIR%\workflow_outputs\step5.txt" 2>&1
echo Step 5 complete

echo All steps completed!

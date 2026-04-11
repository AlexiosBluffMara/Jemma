@echo off
cd /d D:\JemmaRepo\Jemma

echo.
echo ============================================================================
echo JEMMA PROJECT WORKFLOW EXECUTION
echo ============================================================================
echo Working directory: %cd%
echo.

echo.
echo ============================================================================
echo COMMAND 1: python --version
echo ============================================================================
python --version

echo.
echo ============================================================================
echo COMMAND 2: python -c import sys info
echo ============================================================================
python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"

echo.
echo ============================================================================
echo COMMAND 3: python -m pip list ^| findstr /I "fastapi discord uvicorn"
echo ============================================================================
python -m pip list | findstr /I "fastapi discord uvicorn"

echo.
echo ============================================================================
echo COMMAND 4: python -m pip install -e .
echo ============================================================================
python -m pip install -e .

echo.
echo ============================================================================
echo COMMAND 5: python -m unittest discover -s tests -p test_*.py -v
echo ============================================================================
python -m unittest discover -s tests -p test_*.py -v

echo.
echo ============================================================================
echo WORKFLOW EXECUTION COMPLETE
echo ============================================================================
pause

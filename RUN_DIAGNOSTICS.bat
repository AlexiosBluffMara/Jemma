@echo off
setlocal enabledelayedexpansion

cd /d D:\JemmaRepo\Jemma

echo ================================================================================
echo STEP 1: python --version
echo ================================================================================
python --version
echo Exit Code: !ERRORLEVEL!
echo.

echo ================================================================================
echo STEP 2: python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"
echo ================================================================================
python -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version_info)"
echo Exit Code: !ERRORLEVEL!
echo.

echo ================================================================================
echo STEP 3: python -m pip list ^| findstr /I "fastapi discord uvicorn"
echo ================================================================================
python -m pip list | findstr /I "fastapi discord uvicorn"
echo Exit Code: !ERRORLEVEL!
echo.

echo ================================================================================
echo STEP 4: python -m pip install -e .
echo ================================================================================
python -m pip install -e .
echo Exit Code: !ERRORLEVEL!
echo.

echo ================================================================================
echo STEP 5: python -m unittest discover -s tests -p test_*.py -v
echo ================================================================================
python -m unittest discover -s tests -p test_*.py -v
echo Exit Code: !ERRORLEVEL!
echo.

echo ================================================================================
echo DIAGNOSTICS COMPLETE
echo ================================================================================

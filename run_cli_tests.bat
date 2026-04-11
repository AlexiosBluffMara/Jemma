@echo off
echo.
echo ===================================
echo CLI Test via CMD.exe
echo ===================================
echo.

echo === Test 1: git status ===
git --no-pager status --short
echo.

echo === Test 2: python version ===
python --version
echo.

echo === Test 3: Where is git ===
where git
echo.

echo === Test 4: Where is python ===
where python
echo.

echo Tests completed.

@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo DISK C: (fsutil volume diskfree C:)
echo ============================================================
fsutil volume diskfree C: 2>&1

echo.
echo ============================================================
echo DISK D: (fsutil volume diskfree D:)
echo ============================================================
fsutil volume diskfree D: 2>&1

echo.
echo ============================================================
echo NETWORK ADAPTERS (netsh interface ipv4 show interfaces)
echo ============================================================
netsh interface ipv4 show interfaces 2>&1

echo.
echo ============================================================
echo JAVA PATH (where java)
echo ============================================================
where java 2>&1

echo.
echo ============================================================
echo ADB PATH (where adb)
echo ============================================================
where adb 2>&1

echo.
echo ============================================================
echo GRADLEW IN D: (dir /s /b D:\gradlew.bat D:\gradlew 2^>nul ^| findstr /i gradlew)
echo ============================================================
for /f "delims=" %%I in ('dir /s /b D:\gradlew* 2^>nul') do echo %%I

echo.
echo ============================================================
echo GRADLE (where gradle)
echo ============================================================
where gradle 2>&1

echo.
echo ============================================================
echo EMULATOR (where emulator)
echo ============================================================
where emulator 2>&1

echo.
echo ============================================================
echo SPEEDTEST (where speedtest)
echo ============================================================
where speedtest 2>&1

echo.
echo ============================================================
echo TAILSCALE (where tailscale.exe)
echo ============================================================
where tailscale 2>&1

echo.
echo ============================================================
echo ENVIRONMENT VARIABLES (set)
echo ============================================================
set 2>&1

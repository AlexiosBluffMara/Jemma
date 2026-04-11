@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo CPU INFO (wmic cpu get name,manufacturer,maxclockspeed,numberofcores,numberoflogicalprocessors)
echo ============================================================
wmic cpu get name,manufacturer,maxclockspeed,numberofcores,numberoflogicalprocessors 2>&1

echo.
echo ============================================================
echo GPU INFO (wmic path win32_videocontroller get name,driverversion,description)
echo ============================================================
wmic path win32_videocontroller get name,driverversion,description 2>&1

echo.
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
echo ENVIRONMENT VARIABLES (set)
echo ============================================================
set 2>&1

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
echo GRADLEW PATH (where gradlew)
echo ============================================================
where gradlew 2>&1

echo.
echo ============================================================
echo GRADLE PATH (where gradle)
echo ============================================================
where gradle 2>&1

echo.
echo ============================================================
echo EMULATOR PATH (where emulator)
echo ============================================================
where emulator 2>&1

echo.
echo ============================================================
echo SPEEDTEST PATH (where speedtest)
echo ============================================================
where speedtest 2>&1

echo.
echo ============================================================
echo TAILSCALE PATH (where tailscale)
echo ============================================================
where tailscale 2>&1

echo.
echo ============================================================
echo REGISTRY JAVA (reg query "HKLM\SOFTWARE\JavaSoft" /s)
echo ============================================================
reg query "HKLM\SOFTWARE\JavaSoft" /s 2>&1

echo.
echo ============================================================
echo REGISTRY ANDROID STUDIO (reg query "HKLM\SOFTWARE\Android" /s)
echo ============================================================
reg query "HKLM\SOFTWARE\Android" /s 2>&1

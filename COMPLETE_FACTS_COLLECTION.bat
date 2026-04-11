@echo off
setlocal enabledelayedexpansion
cd /d d:\JemmaRepo\Jemma

(
    echo ============================================================================
    echo COMPLETE MACHINE FACTS COLLECTION
    echo ============================================================================
    echo.
    
    echo ============================================================================
    echo 1. CPU MARKETING NAME
    echo ============================================================================
    wmic cpu get name
    echo.
    
    echo ============================================================================
    echo 2. CPU DETAILS (cores, speed, manufacturer)
    echo ============================================================================
    wmic cpu get name,manufacturer,numberofcores,numberoflogicalprocessors,maxclockspeed
    echo.
    
    echo ============================================================================
    echo 3. TOTAL RAM (KB - convert to GB by dividing by 1048576)
    echo ============================================================================
    wmic os get TotalVisibleMemorySize
    echo.
    
    echo ============================================================================
    echo 4. GPU - Video Controller Information
    echo ============================================================================
    wmic path win32_videocontroller get name,driverversion,description
    echo.
    
    echo ============================================================================
    echo 5. DISK C: FREE SPACE (fsutil volume diskfree)
    echo ============================================================================
    fsutil volume diskfree C:
    echo.
    
    echo ============================================================================
    echo 6. DISK D: FREE SPACE (fsutil volume diskfree)
    echo ============================================================================
    fsutil volume diskfree D:
    echo.
    
    echo ============================================================================
    echo 7. ALL FIXED DISKS - Size and Free Space (WMIC)
    echo ============================================================================
    wmic logicaldisk get name,size,freespace
    echo.
    
    echo ============================================================================
    echo 8. NETWORK ADAPTERS - Status and Details
    echo ============================================================================
    netsh interface ipv4 show interfaces
    echo.
    
    echo ============================================================================
    echo 9. NETWORK ADAPTER SPEEDS (bits per second)
    echo ============================================================================
    wmic nic get name,speed,status,netconnectionstatus
    echo.
    
    echo ============================================================================
    echo 10. FULL IPCONFIG /ALL - Complete Network Configuration
    echo ============================================================================
    ipconfig /all
    echo.
    
    echo ============================================================================
    echo 11. JAVA - Location and Version
    echo ============================================================================
    echo Searching for java.exe in PATH...
    where java 2>nul || echo java not found in PATH
    echo.
    echo Java version check:
    java -version 2>&1 || echo java command failed
    echo.
    
    echo ============================================================================
    echo 12. ADB - Android Debug Bridge Location and Version
    echo ============================================================================
    echo Searching for adb.exe in PATH...
    where adb 2>nul || echo adb not found in PATH
    echo.
    echo ADB version:
    adb version 2>&1 || echo adb command failed
    echo.
    
    echo ============================================================================
    echo 13. ANDROID EMULATOR - Location
    echo ============================================================================
    echo Searching for emulator.exe in PATH...
    where emulator 2>nul || echo emulator not found in PATH
    echo.
    
    echo ============================================================================
    echo 14. ANDROID STUDIO - Location Check
    echo ============================================================================
    echo Searching for Android Studio installation...
    where studio.exe 2>nul || echo studio.exe not found in PATH
    echo.
    
    echo ============================================================================
    echo 15. TAILSCALE - Location and Version
    echo ============================================================================
    echo Searching for tailscale.exe in PATH...
    where tailscale 2>nul || echo tailscale not found in PATH
    echo.
    echo Tailscale version:
    tailscale version 2>&1 || echo tailscale command failed
    echo.
    echo Tailscale processes (tasklist):
    tasklist | findstr /i tailscale
    echo.
    
    echo ============================================================================
    echo 16. GRADLE - Location and Version
    echo ============================================================================
    echo Searching for gradle.exe in PATH...
    where gradle 2>nul || echo gradle not found in PATH
    echo.
    echo Gradle version:
    gradle --version 2>&1 || echo gradle command failed
    echo.
    
    echo ============================================================================
    echo 17. SPEEDTEST - Location and Version
    echo ============================================================================
    echo Searching for speedtest.exe in PATH...
    where speedtest 2>nul || echo speedtest not found in PATH
    echo.
    echo Speedtest version:
    speedtest --version 2>&1 || echo speedtest command failed
    echo.
    
    echo ============================================================================
    echo 18. NVIDIA GPU DETAILS (nvidia-smi)
    echo ============================================================================
    echo Searching for nvidia-smi.exe in PATH...
    where nvidia-smi 2>nul || echo nvidia-smi not found in PATH
    echo.
    echo nvidia-smi output:
    nvidia-smi 2>&1 || echo nvidia-smi command failed
    echo.
    
    echo ============================================================================
    echo COLLECTION COMPLETE
    echo ============================================================================
    
) > MACHINE_FACTS_COMPLETE.txt 2>&1

echo.
echo ============================================================================
echo RESULTS WRITTEN TO: MACHINE_FACTS_COMPLETE.txt
echo ============================================================================
echo.
echo First 100 lines of output:
type MACHINE_FACTS_COMPLETE.txt | more +0

echo.
echo COMPLETE OUTPUT:
echo.
type MACHINE_FACTS_COMPLETE.txt

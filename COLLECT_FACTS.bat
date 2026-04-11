@echo off
setlocal enabledelayedexpansion

echo ================================================================================
echo CPU INFORMATION
echo ================================================================================
wmic cpu get name /format:value
echo.

echo ================================================================================
echo DISK C: SPACE (fsutil)
echo ================================================================================
fsutil volume diskfree C:
echo.

echo ================================================================================
echo DISK D: SPACE (fsutil)
echo ================================================================================
fsutil volume diskfree D:
echo.

echo ================================================================================
echo ALL DISKS SUMMARY (wmic)
echo ================================================================================
wmic logicaldisk get name,size,freespace
echo.

echo ================================================================================
echo GPU INFORMATION
echo ================================================================================
wmic path win32_videocontroller get name,driverversion /format:value
echo.

echo ================================================================================
echo NETWORK INTERFACES (netsh)
echo ================================================================================
netsh interface ipv4 show interfaces
echo.

echo ================================================================================
echo NETWORK ADAPTER SPEEDS (wmic)
echo ================================================================================
wmic nic get name,speed,status,netconnectionstatus /format:value
echo.

echo ================================================================================
echo IPCONFIG ALL
echo ================================================================================
ipconfig /all
echo.

echo ================================================================================
echo TAILSCALE STATUS
echo ================================================================================
tasklist | findstr /i tailscale
ipconfig | findstr /i tailscale
echo.

echo ================================================================================
echo NVIDIA GPU (nvidia-smi)
echo ================================================================================
nvidia-smi 2>nul || echo nvidia-smi not available in PATH
echo.

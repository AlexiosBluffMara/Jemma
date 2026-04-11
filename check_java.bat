@echo off
REM Java Environment Check - Non-destructive diagnostic
REM This script checks JAVA_HOME, java on PATH, and Android tooling

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo JAVA ENVIRONMENT DIAGNOSTIC
echo ============================================================================
echo.

echo [1] JAVA_HOME Environment Variable:
echo     Value: %JAVA_HOME%
if defined JAVA_HOME (
    echo     Status: SET
    if exist "%JAVA_HOME%\bin\java.exe" (
        echo     java.exe found: YES
    ) else (
        echo     java.exe found: NO
    )
) else (
    echo     Status: NOT SET
)

echo.
echo [2] java command on PATH (using where):
where java >nul 2>&1
if !errorlevel! equ 0 (
    echo     Status: FOUND
    for /f "delims=" %%A in ('where java') do (
        echo       - %%A
    )
    echo     Version info:
    java -version 2>&1 | for /f "delims=" %%A in ('findstr /r "."') do echo       %%A
) else (
    echo     Status: NOT FOUND on PATH
)

echo.
echo [3] Android Studio JBR Locations:
set JBR_FOUND=0
if exist "C:\Program Files\Android\Android Studio\jbr\bin\java.exe" (
    echo     Found: C:\Program Files\Android\Android Studio\jbr
    set JBR_FOUND=1
)
if exist "C:\Program Files (x86)\Android\Android Studio\jbr\bin\java.exe" (
    echo     Found: C:\Program Files (x86)\Android\Android Studio\jbr
    set JBR_FOUND=1
)
if %APPDATA%_X NEQ _X (
    if exist "%APPDATA%\Local\Android\Sdk\jbr\bin\java.exe" (
        echo     Found: %APPDATA%\Local\Android\Sdk\jbr
        set JBR_FOUND=1
    )
    if exist "%APPDATA%\Local\Android\Sdk\jre\bin\java.exe" (
        echo     Found: %APPDATA%\Local\Android\Sdk\jre
        set JBR_FOUND=1
    )
)
if %JBR_FOUND% equ 0 (
    echo     Status: NOT FOUND at standard locations
)

echo.
echo [4] C:\Program Files\Android Directory:
if exist "C:\Program Files\Android" (
    echo     Directory exists: YES
    for /d %%D in ("C:\Program Files\Android\*") do (
        set DIR_NAME=%%~nxD
        if "!DIR_NAME:jdk=!"   NEQ "!DIR_NAME!" echo       - !DIR_NAME! ^(JDK match^)
        if "!DIR_NAME:java=!"  NEQ "!DIR_NAME!" echo       - !DIR_NAME! ^(JAVA match^)
        if "!DIR_NAME:jre=!"   NEQ "!DIR_NAME!" echo       - !DIR_NAME! ^(JRE match^)
        if "!DIR_NAME:openjdk=!" NEQ "!DIR_NAME!" echo       - !DIR_NAME! ^(OpenJDK match^)
    )
) else (
    echo     Directory exists: NO
)

echo.
echo [5] Gradle/AGP Compatibility:
if defined JAVA_HOME (
    echo     JAVA_HOME: SET ^(Gradle will use this^)
) else (
    echo     JAVA_HOME: NOT SET
)
where gradle >nul 2>&1
if !errorlevel! equ 0 (
    echo     gradle command: FOUND on PATH
) else (
    echo     gradle command: NOT FOUND on PATH
)
where java >nul 2>&1
if !errorlevel! equ 0 (
    echo     java command: FOUND on PATH ^(builds will work^)
) else (
    echo     java command: NOT FOUND ^(builds will FAIL^)
)

echo.
echo ============================================================================
echo SUMMARY
echo ============================================================================
if defined JAVA_HOME (
    echo     JAVA_HOME configured: YES
) else (
    echo     JAVA_HOME configured: NO
)
where java >nul 2>&1
if !errorlevel! equ 0 (
    echo     java available: YES
) else (
    echo     java available: NO
)
if %JBR_FOUND% equ 1 (
    echo     Android JBR available: YES
) else (
    echo     Android JBR available: NO
)
echo.
echo ============================================================================

#!/usr/bin/env python3
"""
Java environment diagnostic - Non-destructive.
Write output to a text file since direct execution has constraints.
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

output_lines = []

def log(msg=""):
    """Log a message."""
    output_lines.append(msg)
    print(msg)

def main():
    log("=" * 75)
    log(f"JAVA ENVIRONMENT DIAGNOSTIC REPORT")
    log(f"Generated: {datetime.now().isoformat()}")
    log("=" * 75)
    
    # [1] JAVA_HOME
    log("\n[1] JAVA_HOME ENVIRONMENT VARIABLE")
    log("-" * 75)
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        log(f"Status: SET")
        log(f"Value:  {java_home}")
        java_home_path = Path(java_home)
        if java_home_path.exists():
            log(f"Path exists: YES")
            java_exe = java_home_path / "bin" / "java.exe"
            if java_exe.exists():
                log(f"java.exe: YES - {java_exe}")
            else:
                log(f"java.exe: NO (expected at {java_exe})")
        else:
            log(f"Path exists: NO")
    else:
        log(f"Status: NOT SET")
    
    # [2] java on PATH
    log("\n[2] JAVA ON PATH")
    log("-" * 75)
    try:
        result = subprocess.run(
            ['where', 'java'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            java_paths = result.stdout.strip().split('\n')
            log(f"Status: FOUND ({len(java_paths)} location(s))")
            for path in java_paths:
                if path.strip():
                    log(f"  - {path}")
            
            # Version
            try:
                ver = subprocess.run(
                    ['java', '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = (ver.stderr + ver.stdout).strip()
                lines = [l.strip() for l in output.split('\n') if l.strip()]
                if lines:
                    log(f"Version info:")
                    for line in lines[:3]:
                        log(f"  {line}")
            except Exception as e:
                log(f"Could not get version: {e}")
        else:
            log(f"Status: NOT FOUND on PATH")
            if result.stderr.strip():
                log(f"stderr: {result.stderr}")
    except Exception as e:
        log(f"Status: ERROR - {e}")
    
    # [3] Android Studio JBR
    log("\n[3] ANDROID STUDIO JBR")
    log("-" * 75)
    jbr_paths = [
        "C:\\Program Files\\Android\\Android Studio\\jbr",
        "C:\\Program Files (x86)\\Android\\Android Studio\\jbr",
        os.path.expandvars(r"%APPDATA%\Local\Android\Sdk\jre"),
        os.path.expandvars(r"%APPDATA%\Local\Android\Sdk\jbr")
    ]
    jbr_found = []
    for path in jbr_paths:
        p = Path(path)
        if p.exists():
            jbr_found.append(str(p))
            java_exe = p / "bin" / "java.exe"
            log(f"Found: {p}")
            if java_exe.exists():
                log(f"  java.exe: YES")
            else:
                log(f"  java.exe: NO")
    if not jbr_found:
        log(f"Status: NOT FOUND at standard locations")
    
    # [4] C:\Program Files\Android
    log("\n[4] C:\\PROGRAM FILES\\ANDROID CONTENTS")
    log("-" * 75)
    android_base = Path("C:\\Program Files\\Android")
    if android_base.exists():
        log(f"Directory exists: YES")
        try:
            subdirs = sorted([d.name for d in android_base.iterdir() if d.is_dir()])
            log(f"Subdirectories ({len(subdirs)}):")
            
            jdk_matches = [d for d in subdirs if any(x in d.lower() for x in ['jdk', 'java', 'jre', 'openjdk'])]
            if jdk_matches:
                log(f"  JDK/JRE-like directories:")
                for d in jdk_matches:
                    p = android_base / d
                    java_exe = p / "bin" / "java.exe"
                    exe_status = "✓" if java_exe.exists() else "✗"
                    log(f"    {exe_status} {d}")
            else:
                log(f"  No JDK/JRE-like directories found")
                log(f"  Other subdirs (first 10):")
                for d in subdirs[:10]:
                    log(f"    - {d}")
                if len(subdirs) > 10:
                    log(f"    ... and {len(subdirs) - 10} more")
        except Exception as e:
            log(f"Error listing: {e}")
    else:
        log(f"Directory exists: NO")
    
    # [5] Summary
    log("\n[5] SUMMARY & GRADLE/AGP COMPATIBILITY")
    log("-" * 75)
    
    has_java_home = os.environ.get('JAVA_HOME') is not None
    has_java_path = False
    try:
        result = subprocess.run(['where', 'java'], capture_output=True, timeout=10)
        has_java_path = result.returncode == 0
    except:
        pass
    
    log(f"JAVA_HOME set:          {('YES ✓' if has_java_home else 'NO ✗')}")
    log(f"java on PATH:           {('YES ✓' if has_java_path else 'NO ✗')}")
    log(f"JBR available:          {('YES ✓' if jbr_found else 'NO ✗')}")
    
    log(f"\nGradle/AGP Status:")
    if has_java_path:
        log(f"  ✓ Java available - Gradle builds should work")
        if has_java_home:
            log(f"  ✓ JAVA_HOME set - optimal configuration for Gradle")
        else:
            log(f"  ⚠ JAVA_HOME not set - Gradle will use PATH")
    else:
        log(f"  ✗ Java NOT available - Gradle builds will FAIL")
        log(f"  ACTION: Install JDK or set JAVA_HOME")
    
    if jbr_found:
        log(f"\nAndroid Studio JBR:")
        log(f"  ✓ Available - Can be used if JAVA_HOME not set")
    
    log(f"\n" + "=" * 75)
    
    return output_lines

if __name__ == '__main__':
    lines = main()
    
    # Write to file
    output_file = Path("D:\\JemmaRepo\\Jemma\\java_diagnostic.txt")
    try:
        output_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f"\nResults written to: {output_file}")
    except Exception as e:
        print(f"\nError writing file: {e}")
    
    sys.exit(0)

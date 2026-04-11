#!/usr/bin/env python3
"""Quick Java environment checker - does not modify any files."""

import os
import subprocess
import sys
from pathlib import Path

def check_java_home():
    """Check if JAVA_HOME is set."""
    print("=" * 70)
    print("[1] JAVA_HOME ENVIRONMENT VARIABLE")
    print("=" * 70)
    
    java_home = os.environ.get('JAVA_HOME')
    if not java_home:
        print("Status: NOT SET")
        return None
    
    print(f"Status: SET")
    print(f"Value:  {java_home}")
    
    java_home_path = Path(java_home)
    if java_home_path.exists():
        print(f"Path exists: YES")
        java_exe = java_home_path / "bin" / "java.exe"
        if java_exe.exists():
            print(f"java.exe at {java_exe.parent}: YES")
            return str(java_exe)
        else:
            print(f"java.exe at {java_exe.parent}: NO")
    else:
        print(f"Path exists: NO (does not exist on filesystem)")
    
    return None

def check_java_on_path():
    """Check if java is available on PATH."""
    print("\n" + "=" * 70)
    print("[2] JAVA ON PATH (where command)")
    print("=" * 70)
    
    try:
        result = subprocess.run(
            ['where', 'java'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            java_paths = result.stdout.strip().split('\n')
            print(f"Status: FOUND ({len(java_paths)} location(s))")
            for path in java_paths:
                print(f"  - {path}")
            
            # Try to get version
            try:
                ver_result = subprocess.run(
                    ['java', '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                ver_output = (ver_result.stderr + ver_result.stdout).strip()
                lines = [l for l in ver_output.split('\n') if l.strip()]
                if lines:
                    print(f"Version info:")
                    for line in lines[:3]:
                        print(f"  {line}")
            except Exception as e:
                print(f"Could not get version: {e}")
            
            return java_paths[0] if java_paths else None
        else:
            print("Status: NOT FOUND on PATH")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Status: ERROR checking PATH - {e}")
    
    return None

def check_android_studio_jbr():
    """Check for Android Studio bundled JBR."""
    print("\n" + "=" * 70)
    print("[3] ANDROID STUDIO BUNDLED JBR")
    print("=" * 70)
    
    jbr_paths = [
        Path("C:/Program Files/Android/Android Studio/jbr"),
        Path("C:/Program Files (x86)/Android/Android Studio/jbr"),
        Path(os.path.expandvars(r"%APPDATA%\Local\Android\Sdk\jre")),
        Path(os.path.expandvars(r"%APPDATA%\Local\Android\Sdk\jbr"))
    ]
    
    found_count = 0
    for path in jbr_paths:
        if path.exists():
            found_count += 1
            print(f"Found: {path}")
            java_exe = path / "bin" / "java.exe"
            if java_exe.exists():
                print(f"  ✓ java.exe present")
    
    if found_count == 0:
        print("Status: NOT FOUND at common Android Studio locations")
    else:
        print(f"Status: FOUND ({found_count} location(s))")
    
    return found_count > 0

def check_android_sdk_paths():
    """Check C:\Program Files\Android for standalone OpenJDK."""
    print("\n" + "=" * 70)
    print("[4] C:\\PROGRAM FILES\\ANDROID (Standalone OpenJDK)")
    print("=" * 70)
    
    android_path = Path("C:/Program Files/Android")
    if not android_path.exists():
        print("Status: Directory does NOT exist")
        return None
    
    print("Status: Directory EXISTS")
    
    try:
        subdirs = [d for d in android_path.iterdir() if d.is_dir()]
        print(f"Subdirectories found: {len(subdirs)}")
        
        jdk_dirs = [d for d in subdirs if any(x in d.name.lower() for x in ['jdk', 'java', 'jre', 'openjdk'])]
        
        if jdk_dirs:
            print(f"\nJDK/JRE-like directories ({len(jdk_dirs)}):")
            for d in jdk_dirs:
                print(f"  - {d.name}")
                java_exe = d / "bin" / "java.exe"
                if java_exe.exists():
                    print(f"    ✓ java.exe present")
                else:
                    print(f"    ✗ java.exe NOT present")
        else:
            print(f"\nNo JDK/JRE-like directories found.")
            print("Subdirectories present:")
            for d in sorted(subdirs)[:10]:  # Show first 10
                print(f"  - {d.name}")
            if len(subdirs) > 10:
                print(f"  ... and {len(subdirs) - 10} more")
        
        return len(jdk_dirs) > 0
    
    except Exception as e:
        print(f"Error listing directory: {e}")
        return None

def assess_gradle_compatibility():
    """Assess compatibility with Gradle/AGP."""
    print("\n" + "=" * 70)
    print("[5] GRADLE/AGP COMPATIBILITY ASSESSMENT")
    print("=" * 70)
    
    has_java_home = os.environ.get('JAVA_HOME') is not None
    has_java_path = None
    
    try:
        result = subprocess.run(['where', 'java'], capture_output=True, text=True, timeout=5)
        has_java_path = result.returncode == 0
    except:
        has_java_path = False
    
    print("\nCurrent Status:")
    print(f"  JAVA_HOME set:        {'YES ✓' if has_java_home else 'NO ✗'}")
    print(f"  java on PATH:         {'YES ✓' if has_java_path else 'NO ✗'}")
    
    print("\nGradle/AGP Usability:")
    if has_java_home:
        print("  • JAVA_HOME is properly configured")
        print("  • Gradle will prefer JAVA_HOME for builds")
    else:
        print("  • JAVA_HOME not set - Gradle will rely on PATH")
    
    if has_java_path:
        print("  • java command is available - basic execution possible")
    else:
        print("  • java NOT on PATH - Gradle builds will fail")
        print("  • ACTION NEEDED: Set JAVA_HOME or add java to PATH")
        return False
    
    # Check JBR
    has_jbr = check_android_studio_jbr.__code__.co_consts  # Placeholder
    jbr_paths = [
        Path("C:/Program Files/Android/Android Studio/jbr"),
        Path("C:/Program Files (x86)/Android/Android Studio/jbr"),
    ]
    jbr_exists = any(p.exists() for p in jbr_paths)
    
    print(f"\nAndroid Studio JBR:")
    if jbr_exists:
        print("  • JBR available (can be used if no JAVA_HOME set)")
    else:
        print("  • JBR NOT available at standard locations")
    
    print(f"\nConclusion:")
    if has_java_home or has_java_path:
        print("  ✓ GRADLE/AGP builds should work")
        if not has_java_home and not jbr_exists:
            print("  ⚠ Note: Consider setting JAVA_HOME for optimal compatibility")
    else:
        print("  ✗ GRADLE/AGP builds will FAIL - Java not available")
    
    return has_java_path or has_java_home

def main():
    """Run all checks."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " JAVA ENVIRONMENT DIAGNOSTIC REPORT ".center(68) + "║")
    print("╚" + "=" * 68 + "╝")
    
    java_home_path = check_java_home()
    java_path = check_java_on_path()
    has_jbr = check_android_studio_jbr()
    has_openjdk = check_android_sdk_paths()
    gradle_ok = assess_gradle_compatibility()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"JAVA_HOME configured:     {java_home_path is not None}")
    print(f"java on PATH:             {java_path is not None}")
    print(f"Android Studio JBR found: {has_jbr}")
    print(f"Standalone OpenJDK found: {has_openjdk}")
    print(f"Gradle/AGP compatible:    {gradle_ok}")
    print("=" * 70)
    print()

if __name__ == '__main__':
    main()

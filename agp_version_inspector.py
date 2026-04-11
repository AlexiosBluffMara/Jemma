#!/usr/bin/env python3
"""
Read-only inspection of Android Studio JAR files for AGP version.
Uses Python zipfile module - NO file extraction.
"""

import zipfile
import os
import sys
from io import StringIO

def inspect_jar_readonly(jar_path, jar_name):
    """Inspect JAR file contents without extracting."""
    print(f"\n{'='*80}")
    print(f"JAR: {jar_name}")
    print(f"Path: {jar_path}")
    print('='*80)
    
    if not os.path.exists(jar_path):
        print(f"❌ NOT FOUND")
        return
    
    size_mb = os.path.getsize(jar_path) / (1024*1024)
    print(f"✓ Size: {size_mb:.2f} MB")
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as zf:
            entries = zf.namelist()
            print(f"✓ Entries: {len(entries)}")
            
            # Find entries with AGP/version/gradle/buildTools/compileSdk
            keywords = ['agp', 'version', 'gradle', 'buildtools', 'compilesdk', 'android']
            matching_entries = []
            
            for entry in entries:
                entry_lower = entry.lower()
                if any(kw in entry_lower for kw in keywords):
                    matching_entries.append(entry)
            
            print(f"\n📌 Matching Entries ({len(matching_entries)}):")
            if matching_entries:
                for entry in sorted(matching_entries)[:30]:
                    try:
                        info = zf.getinfo(entry)
                        size_str = f"{info.file_size} bytes" if info.file_size > 0 else "0 bytes"
                        print(f"  {entry:<70} ({size_str})")
                    except:
                        print(f"  {entry}")
                if len(matching_entries) > 30:
                    print(f"  ... and {len(matching_entries)-30} more")
            else:
                print("  (none found)")
            
            # Look for specific known files with version info
            print(f"\n📂 Looking for config files...")
            config_patterns = ['.properties', '.xml', '.gradle', 'version', 'gradle.properties', 'build.gradle']
            config_files = []
            
            for entry in entries:
                for pattern in config_patterns:
                    if pattern in entry.lower():
                        config_files.append(entry)
                        break
            
            if config_files:
                print(f"📄 Found {len(config_files)} config-related files:")
                for cf in sorted(config_files)[:20]:
                    print(f"  {cf}")
                if len(config_files) > 20:
                    print(f"  ... and {len(config_files)-20} more")
            
            # Try to read and display relevant text files
            print(f"\n📖 Attempting to read key files...")
            text_files = [e for e in entries if e.lower().endswith(('.properties', '.txt', '.gradle', '.xml', '.json'))]
            
            for text_file in sorted(text_files):
                if any(kw in text_file.lower() for kw in keywords):
                    try:
                        content = zf.read(text_file).decode('utf-8', errors='ignore')
                        if content.strip():
                            print(f"\n  📝 {text_file}:")
                            lines = content.split('\n')[:10]
                            for line in lines:
                                if line.strip():
                                    print(f"    {line[:100]}")
                    except Exception as e:
                        pass  # Skip files we can't read
    
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    studio_base = r"C:\Program Files\Android\Android Studio"
    lib_path = os.path.join(studio_base, "plugins", "android", "lib")
    
    print("\n" + "="*80)
    print("ANDROID STUDIO JAR INSPECTION (READ-ONLY MODE)")
    print("="*80)
    
    # Check product-info.json
    print(f"\n[PRODUCT-INFO]")
    product_info = os.path.join(studio_base, "product-info.json")
    if os.path.exists(product_info):
        print(f"✓ Found: {product_info}")
        try:
            with open(product_info, 'r') as f:
                content = f.read()
                # Find gradle/agp references
                import re
                matches = re.findall(r'"[^"]*(?:gradle|agp|version)[^"]*":\s*"([^"]*)"', content, re.I)
                if matches:
                    print(f"  Version references: {matches[:5]}")
        except:
            pass
    else:
        print(f"❌ Not found: {product_info}")
    
    # Target JARs
    target_jars = [
        "wizard-template.jar",
        "android-gradle.jar",
        "libagp-version.jar"
    ]
    
    for jar_name in target_jars:
        jar_path = os.path.join(lib_path, jar_name)
        inspect_jar_readonly(jar_path, jar_name)
    
    # List all AGP/gradle/version jars
    print(f"\n{'='*80}")
    print("ALL AGP/GRADLE/VERSION JARS IN PLUGINS/ANDROID/LIB")
    print('='*80)
    
    if os.path.exists(lib_path):
        all_jars = sorted([f for f in os.listdir(lib_path) if f.endswith('.jar')])
        agp_jars = [j for j in all_jars if any(x in j.lower() for x in ['agp', 'gradle', 'version'])]
        
        print(f"Found {len(agp_jars)} matching JAR files:")
        for jar in agp_jars:
            jar_path = os.path.join(lib_path, jar)
            size = os.path.getsize(jar_path) / 1024
            print(f"  {jar:<50} ({size:.1f} KB)")
    
    print(f"\n{'='*80}")
    print("INSPECTION COMPLETE - NO FILES EXTRACTED OR MODIFIED")
    print('='*80 + "\n")

if __name__ == "__main__":
    main()

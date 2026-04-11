#!/usr/bin/env python3
"""Read-only inspection of Android Studio JAR files for AGP version and build config."""

import zipfile
import os
from pathlib import Path

studio_base = r"C:\Program Files\Android\Android Studio"
lib_path = os.path.join(studio_base, "plugins", "android", "lib")

print("=" * 80)
print("ANDROID STUDIO JAR INSPECTION - READ-ONLY")
print("=" * 80)

# Target JARs
target_jars = {
    "wizard-template.jar": [],
    "android-gradle.jar": [],
    "libagp-version.jar": []
}

# Keywords to search
keywords = ['agp', 'gradle', 'version', 'buildtools', 'compilesdk']

print("\n[1] INSPECTING PRODUCT-INFO.JSON")
print("-" * 80)
product_info = os.path.join(studio_base, "product-info.json")
if os.path.exists(product_info):
    print(f"✓ Found: {product_info}")
    # Search for AGP version info in the JSON
    with open(product_info, 'r') as f:
        content = f.read()
        if 'agp' in content.lower():
            print("  AGP references found in product-info.json")
else:
    print(f"✗ Not found: {product_info}")

# Inspect each JAR
print("\n[2] INSPECTING TARGET JAR FILES")
print("-" * 80)

for jar_name in target_jars.keys():
    jar_path = os.path.join(lib_path, jar_name)
    print(f"\nJAR: {jar_name}")
    print(f"Path: {jar_path}")
    
    if not os.path.exists(jar_path):
        print(f"✗ NOT FOUND")
        continue
    
    print(f"✓ FOUND ({os.path.getsize(jar_path)} bytes)")
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as z:
            entries = z.namelist()
            print(f"  Total entries: {len(entries)}")
            
            # Find relevant entries
            relevant = []
            for entry in entries:
                entry_lower = entry.lower()
                if any(kw in entry_lower for kw in keywords):
                    relevant.append(entry)
            
            if relevant:
                print(f"  Entries matching keywords ({len(relevant)}):")
                for entry in relevant[:15]:  # Show first 15
                    print(f"    - {entry}")
                if len(relevant) > 15:
                    print(f"    ... and {len(relevant) - 15} more")
            
            # Look for .properties, .xml, .gradle files
            config_files = [e for e in entries if e.lower().endswith(('.properties', '.xml', '.gradle', '.txt'))]
            if config_files:
                print(f"  Config files found ({len(config_files)}):")
                for cf in config_files[:10]:
                    print(f"    - {cf}")
                if len(config_files) > 10:
                    print(f"    ... and {len(config_files) - 10} more")
    except Exception as e:
        print(f"✗ ERROR: {e}")

# List ALL jars containing agp/gradle/version
print("\n[3] ALL JAR FILES CONTAINING AGP/GRADLE/VERSION")
print("-" * 80)

if os.path.exists(lib_path):
    all_jars = sorted([f for f in os.listdir(lib_path) if f.lower().endswith('.jar')])
    matching = [j for j in all_jars if any(x in j.lower() for x in ['agp', 'gradle', 'version'])]
    print(f"Matching JARs ({len(matching)}):")
    for jar in matching:
        print(f"  - {jar}")
else:
    print(f"✗ Path not found: {lib_path}")

print("\n" + "=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)

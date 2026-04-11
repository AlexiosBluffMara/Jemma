#!/usr/bin/env python3
"""
Inspect Android Studio JAR files without extracting them.
Uses zipfile module for read-only access.
Comprehensive search for build/version metadata.
"""

import zipfile
import os
from pathlib import Path

jar_dir = r"C:\Program Files\Android\Android Studio\plugins\android\lib"

# Explicit targets
target_names = ['wizard-template.jar', 'android-gradle.jar', 'libagp-version.jar']

# Additional keywords for file discovery
search_patterns = ['agp', 'gradle', 'version']

# Find all matching JAR files
all_jars = [f for f in os.listdir(jar_dir) if f.endswith('.jar')] if os.path.exists(jar_dir) else []
jar_files = []

# Add explicit targets
for jar in all_jars:
    if jar in target_names:
        jar_files.append(os.path.join(jar_dir, jar))

# Add pattern matches (case-insensitive)
for jar in all_jars:
    jar_lower = jar.lower()
    for pattern in search_patterns:
        if pattern in jar_lower and os.path.join(jar_dir, jar) not in jar_files:
            jar_files.append(os.path.join(jar_dir, jar))
            break

jar_files = sorted(set(jar_files))

keywords = ['agp', 'gradle', 'version', 'buildtools', 'compilesdk', 'build-tools', 'sdk']
extensions = ['.properties', '.xml', '.gradle', '.json', '.mf']

def inspect_jar(jar_path):
    """Inspect a JAR file without extracting"""
    if not os.path.exists(jar_path):
        print(f"\n❌ JAR file not found: {jar_path}\n")
        return
    
    jar_name = os.path.basename(jar_path)
    print(f"\n{'='*100}")
    print(f"📦 INSPECTING: {jar_name}")
    print(f"{'='*100}")
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            all_entries = jar.namelist()
            print(f"\n✅ Total entries: {len(all_entries)}\n")
            
            # Find entries matching keywords
            keyword_matches = []
            for entry in all_entries:
                entry_lower = entry.lower()
                for keyword in keywords:
                    if keyword in entry_lower:
                        keyword_matches.append(entry)
                        break
            
            # Find config files
            config_files = []
            for entry in all_entries:
                entry_lower = entry.lower()
                if any(entry_lower.endswith(ext) for ext in extensions):
                    config_files.append(entry)
            
            # Display all entries
            print(f"📄 ALL ENTRIES ({len(all_entries)} total):")
            print("-" * 100)
            for entry in sorted(all_entries):
                print(f"  {entry}")
            
            # Display keyword matches
            if keyword_matches:
                print(f"\n🔍 KEYWORD MATCHES ({len(keyword_matches)} found):")
                print("-" * 100)
                for entry in sorted(keyword_matches):
                    print(f"  ✓ {entry}")
            
            # Display config files
            if config_files:
                print(f"\n⚙️  CONFIG FILES ({len(config_files)} found):")
                print("-" * 100)
                for entry in sorted(config_files):
                    print(f"  📝 {entry}")
            
            # Read and display content
            print(f"\n📖 CONTENT OF KEYWORD MATCHES:")
            print("-" * 100)
            for entry in sorted(keyword_matches):
                if not entry.endswith('/'):
                    try:
                        content = jar.read(entry)
                        try:
                            text_content = content.decode('utf-8', errors='ignore').strip()
                            if text_content:
                                print(f"\n{'▶'*50}")
                                print(f"FILE: {entry}")
                                print(f"{'▶'*50}")
                                lines = text_content.split('\n')
                                for line in lines[:50]:
                                    print(f"  {line}")
                                if len(lines) > 50:
                                    print(f"  ... ({len(lines) - 50} more lines)")
                        except:
                            print(f"\n{entry} (binary, {len(content)} bytes)")
                    except Exception as e:
                        print(f"\nError reading {entry}: {e}")
            
            # Read and display config files
            print(f"\n\n⚙️  CONTENT OF CONFIG FILES:")
            print("-" * 100)
            for entry in sorted(config_files):
                if not entry.endswith('/'):
                    try:
                        content = jar.read(entry)
                        try:
                            text_content = content.decode('utf-8', errors='ignore').strip()
                            if text_content:
                                print(f"\n{'▶'*50}")
                                print(f"FILE: {entry}")
                                print(f"{'▶'*50}")
                                lines = text_content.split('\n')
                                for line in lines[:100]:
                                    print(f"  {line}")
                                if len(lines) > 100:
                                    print(f"  ... ({len(lines) - 100} more lines)")
                        except:
                            print(f"\n{entry} (binary, {len(content)} bytes)")
                    except Exception as e:
                        print(f"\nError reading {entry}: {e}")
                    
    except zipfile.BadZipFile:
        print(f"❌ Invalid JAR file format: {jar_path}")
    except Exception as e:
        print(f"❌ Error opening JAR file: {e}")

# Inspect all JAR files
for jar_path in jar_files:
    inspect_jar(jar_path)

print(f"\n\n{'='*100}")
print("✅ JAR inspection complete")
print(f"{'='*100}\n")

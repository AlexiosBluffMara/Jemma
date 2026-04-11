#!/usr/bin/env python3
"""
Android Studio JAR File Inspector
Reads JAR files using Python's zipfile module - NO extraction to disk
Searches for AGP, Gradle, version, and build configuration entries
"""

import zipfile
import os
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

JAR_FILES = [
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\wizard-template.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\android-gradle.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"
]

SEARCH_KEYWORDS = [
    'agp', 'gradle', 'version', 'buildtools', 'compilesdk',
    'android', 'sdk', 'ndk', 'plugin', 'task', 'variant'
]

CONFIG_EXTENSIONS = (
    '.properties', '.xml', '.gradle', '.json', '.txt',
    '.manifest', '.config', '.cfg'
)

# ============================================================================
# FUNCTIONS
# ============================================================================

def print_header(text, char='=', width=100):
    """Print a formatted header"""
    print(f"\n{char * width}")
    print(f"{text}")
    print(f"{char * width}\n")

def print_subheader(text, width=100):
    """Print a formatted subheader"""
    print(f"\n{text}")
    print("─" * width)

def read_file_safe(jar, entry_name, max_lines=50):
    """Safely read file content from JAR"""
    try:
        content = jar.read(entry_name)
        try:
            text = content.decode('utf-8', errors='ignore')
        except:
            text = content.decode('latin-1', errors='ignore')
        return text
    except Exception as e:
        return f"[Error reading file: {e}]"

def inspect_jar_file(jar_path):
    """Inspect a single JAR file"""
    
    jar_name = os.path.basename(jar_path)
    print_header(f"📦 INSPECTING: {jar_name}", '=', 100)
    
    # Check file existence
    if not os.path.exists(jar_path):
        print(f"❌ ERROR: File not found: {jar_path}\n")
        return False
    
    print(f"📂 Path: {jar_path}\n")
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            
            # Get all entries
            all_entries = sorted(jar.namelist())
            files_only = [e for e in all_entries if not e.endswith('/')]
            
            print(f"✅ Successfully opened JAR file")
            print(f"   Total entries: {len(all_entries)}")
            print(f"   Files (not directories): {len(files_only)}\n")
            
            # ================================================================
            # SECTION 1: FILE TYPE DISTRIBUTION
            # ================================================================
            print_subheader("📊 FILE TYPE DISTRIBUTION")
            
            file_types = {}
            for entry in files_only:
                ext = os.path.splitext(entry)[1] or '(no extension)'
                file_types[ext] = file_types.get(ext, 0) + 1
            
            for ext in sorted(file_types.keys(), key=lambda x: -file_types[x])[:20]:
                count = file_types[ext]
                pct = f"{(count/len(files_only)*100):.1f}%"
                print(f"   {ext:20} : {count:5} files ({pct})")
            
            if len(file_types) > 20:
                print(f"\n   ... and {len(file_types) - 20} more file types")
            
            # ================================================================
            # SECTION 2: KEYWORD MATCHES
            # ================================================================
            
            keyword_matches = []
            for entry in all_entries:
                entry_lower = entry.lower()
                for kw in SEARCH_KEYWORDS:
                    if kw in entry_lower:
                        keyword_matches.append(entry)
                        break
            
            if keyword_matches:
                print_subheader(f"🔍 KEYWORD MATCHES ({len(keyword_matches)} found)")
                
                # Group by keyword
                by_keyword = {}
                for entry in keyword_matches:
                    entry_lower = entry.lower()
                    for kw in SEARCH_KEYWORDS:
                        if kw in entry_lower:
                            by_keyword.setdefault(kw, []).append(entry)
                            break
                
                for kw in sorted(by_keyword.keys()):
                    entries = by_keyword[kw]
                    print(f"\n   Keyword: '{kw}' ({len(entries)} matches)")
                    for entry in sorted(entries)[:15]:
                        print(f"      ✓ {entry}")
                    if len(entries) > 15:
                        print(f"      ... and {len(entries) - 15} more")
            else:
                print_subheader("🔍 KEYWORD MATCHES")
                print("   (None found)")
            
            # ================================================================
            # SECTION 3: CONFIG FILES
            # ================================================================
            
            config_files = [e for e in all_entries if e.lower().endswith(CONFIG_EXTENSIONS)]
            
            if config_files:
                print_subheader(f"⚙️  CONFIGURATION FILES ({len(config_files)} found)")
                
                for entry in sorted(config_files)[:30]:
                    print(f"   📝 {entry}")
                
                if len(config_files) > 30:
                    print(f"\n   ... and {len(config_files) - 30} more")
            else:
                print_subheader("⚙️  CONFIGURATION FILES")
                print("   (None found)")
            
            # ================================================================
            # SECTION 4: CONTENT OF KEY FILES
            # ================================================================
            
            print_subheader("📖 CONTENT OF KEY FILES")
            
            # Read keyword matches
            entries_to_read = keyword_matches[:20]
            
            if entries_to_read:
                print("\n   📄 KEYWORD MATCH FILES:")
                
                for entry in sorted(entries_to_read):
                    if entry.endswith('/'):
                        continue
                    
                    print(f"\n   ▼▼▼ {entry}")
                    content = read_file_safe(jar, entry)
                    
                    if content.startswith('[Error'):
                        print(f"   {content}")
                    else:
                        lines = content.split('\n')
                        
                        # Skip very long binary files
                        if len(lines) > 500:
                            print(f"   [File too large: {len(lines)} lines, showing first 20...]")
                        
                        for i, line in enumerate(lines[:50]):
                            if line.strip():  # Only print non-empty lines
                                print(f"   {line[:140]}")  # Truncate long lines
                        
                        if len(lines) > 50:
                            print(f"   ... ({len(lines) - 50} more lines)")
                    
                    print(f"   ▲▲▲")
            
            # Read config files
            if config_files:
                print("\n\n   ⚙️  CONFIG FILES:")
                
                for entry in sorted(config_files)[:15]:
                    if entry.endswith('/'):
                        continue
                    
                    print(f"\n   ▼▼▼ {entry}")
                    content = read_file_safe(jar, entry)
                    
                    if content.startswith('[Error'):
                        print(f"   {content}")
                    else:
                        lines = content.split('\n')
                        
                        for i, line in enumerate(lines[:50]):
                            if line.strip():
                                print(f"   {line[:140]}")
                        
                        if len(lines) > 50:
                            print(f"   ... ({len(lines) - 50} more lines)")
                    
                    print(f"   ▲▲▲")
            
            # ================================================================
            # SECTION 5: ALL ENTRIES LISTING
            # ================================================================
            
            print_subheader(f"📋 ALL ENTRIES LISTING ({len(all_entries)} total)")
            
            for entry in sorted(all_entries):
                size_str = ""
                if not entry.endswith('/'):
                    try:
                        size = jar.getinfo(entry).file_size
                        if size > 1024*1024:
                            size_str = f" [{size/(1024*1024):.1f}MB]"
                        elif size > 1024:
                            size_str = f" [{size/1024:.1f}KB]"
                        else:
                            size_str = f" [{size}B]"
                    except:
                        pass
                
                dir_marker = "📁 " if entry.endswith('/') else "   "
                print(f"   {dir_marker}{entry}{size_str}")
            
            print()
            return True
            
    except zipfile.BadZipFile:
        print(f"❌ ERROR: Not a valid ZIP/JAR file\n")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("\n")
    print_header("ANDROID STUDIO JAR FILE INSPECTOR", '=', 100)
    print("Using Python's zipfile module for read-only inspection (no extraction)\n")
    
    print(f"Target JAR files:")
    for jar in JAR_FILES:
        print(f"  • {jar}")
    
    print(f"\nSearch keywords: {', '.join(SEARCH_KEYWORDS)}")
    print(f"Config extensions: {', '.join(CONFIG_EXTENSIONS)}\n")
    
    success_count = 0
    for jar_path in JAR_FILES:
        if inspect_jar_file(jar_path):
            success_count += 1
    
    # Summary
    print_header("INSPECTION SUMMARY", '=', 100)
    print(f"✅ Successfully inspected: {success_count}/{len(JAR_FILES)} JAR files")
    
    if success_count == len(JAR_FILES):
        print("✅ All JAR files were successfully analyzed\n")
    elif success_count == 0:
        print("❌ Could not read any JAR files. Verify paths are correct.\n")
        sys.exit(1)
    else:
        print(f"⚠️  {len(JAR_FILES) - success_count} JAR file(s) could not be read\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

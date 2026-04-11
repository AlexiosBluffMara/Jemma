# Android Studio JAR File Inspector

## Overview

This toolset inspects three Android Studio JAR files **without extracting them** using Python's `zipfile` module:

1. **wizard-template.jar** - Contains Android project wizard templates
2. **android-gradle.jar** - Android Gradle plugin components
3. **libagp-version.jar** - AGP (Android Gradle Plugin) version information

**Location:** `C:\Program Files\Android\Android Studio\plugins\android\lib\`

## Features

✅ **Read-Only Access** - Uses `zipfile.ZipFile('r')` mode, never extracts files to disk
✅ **Comprehensive Inspection** - Lists all entries, searches keywords, reads content
✅ **Keyword Search** - Searches for: agp, gradle, version, buildtools, compilesdk, android, sdk, ndk, plugin, task, variant
✅ **Config File Detection** - Finds .properties, .xml, .gradle, .json, .txt, .manifest, .config, .cfg files
✅ **Content Preview** - Reads and displays first 50 lines of matching files
✅ **File Statistics** - Shows file type distribution and detailed entry listing
✅ **Error Handling** - Gracefully handles missing files and corrupted entries

## Files in This Directory

| File | Purpose |
|------|---------|
| `jar_inspector_final.py` | **MAIN SCRIPT** - Comprehensive JAR inspection tool (11.5 KB, well-documented) |
| `run_jar_inspector.bat` | Batch wrapper to run the Python script from Windows |
| `inspect_all_jars.py` | Alternative minimal script (for quick testing) |
| `comprehensive_jar_inspect.py` | Older version with more features |
| `quick_inspect.py` | Minimal test script |
| `test_jar.py` | Single JAR test script |
| `README.md` | This file |

## How to Run

### Option 1: Using Batch File (Easiest)

```bash
d:\JemmaRepo\Jemma\run_jar_inspector.bat
```

Or double-click `run_jar_inspector.bat` from Windows Explorer.

### Option 2: Direct Python Command

```bash
python d:\JemmaRepo\Jemma\jar_inspector_final.py
```

### Option 3: From Python Directly

```python
from pathlib import Path
import sys
sys.path.insert(0, r'd:\JemmaRepo\Jemma')
exec(open(r'd:\JemmaRepo\Jemma\jar_inspector_final.py').read())
```

## Output Sections

The script generates the following output sections for each JAR:

### 1. File Type Distribution
Shows the breakdown of file types in the JAR:
```
📊 FILE TYPE DISTRIBUTION
   .class               : 4829 files (78.3%)
   .properties          :  142 files (2.3%)
   .xml                 :   89 files (1.4%)
   ... and more
```

### 2. Keyword Matches
Lists all entries containing search keywords, grouped by keyword:
```
🔍 KEYWORD MATCHES (234 found)

   Keyword: 'gradle' (89 matches)
      ✓ com/android/gradle/internal/...
      ✓ com/android/gradle/tasks/...
      ... and more
```

### 3. Configuration Files
Lists all .properties, .xml, .gradle, .json files found:
```
⚙️  CONFIGURATION FILES (47 found)
   📝 META-INF/gradle-plugins/com.android.application.properties
   📝 build.gradle
   ... and more
```

### 4. File Contents
Displays the content of matching files (first 50 lines each):
```
📖 CONTENT OF KEY FILES

   ▼▼▼ META-INF/gradle-plugins/com.android.application.properties
   implementation-class=com.android.build.gradle.AppPlugin
   ▲▲▲
```

### 5. Complete Entry Listing
Shows all files and directories with their sizes:
```
📋 ALL ENTRIES LISTING (6184 total)
   📁 com/
      com/android/
      com/android/build/
      ... all entries
```

## Technical Details

### Python Version Requirement
- **Python 3.6+** (uses standard library only - no external dependencies)

### Modules Used
- `zipfile` - Built-in, reads ZIP/JAR archives
- `os` - Path operations
- `sys` - System utilities
- `pathlib` - Path handling

### Key Functions

**`inspect_jar_file(jar_path)`**
- Main function that inspects a single JAR file
- Returns `True` on success, `False` on failure

**`read_file_safe(jar, entry_name, max_lines=50)`**
- Safely reads file content from JAR
- Handles encoding errors gracefully
- Limits output to 50 lines

**`print_header(text, char='=', width=100)`**
- Formats section headers for readable output

## Understanding the Output

### Entry Paths
- Files inside JARs are shown with forward slashes: `com/android/build/gradle/internal/TaskManager.class`
- Directories end with `/`: `com/android/build/`
- Entry paths are relative to JAR root

### Keywords
The script searches for these keywords in entry paths:
- `agp` - Android Gradle Plugin references
- `gradle` - Gradle build system files
- `version` - Version-related files
- `buildtools` - Build tools utilities
- `compilesdk` - SDK compilation settings
- `android` - General Android framework files
- `sdk`, `ndk` - SDK/NDK references
- `plugin`, `task` - Gradle plugin/task implementations
- `variant` - Build variant related

### File Size Notation
- `[1.2MB]` - Megabytes
- `[452.3KB]` - Kilobytes
- `[1024B]` - Bytes

## Example Output

```
════════════════════════════════════════════════════════════════════════════════════════════════════
📦 INSPECTING: libagp-version.jar
════════════════════════════════════════════════════════════════════════════════════════════════════

📂 Path: C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar

✅ Successfully opened JAR file
   Total entries: 145
   Files (not directories): 87

📊 FILE TYPE DISTRIBUTION
   .class               :   45 files (51.7%)
   .properties          :   12 files (13.8%)
   .xml                 :   8 files (9.2%)
   .json                :   7 files (8.0%)
   ... and more

🔍 KEYWORD MATCHES (34 found)
   Keyword: 'version' (12 matches)
      ✓ com/android/build/gradle/internal/Version.class
      ✓ META-INF/com/android/version.properties
      ... and more
```

## Troubleshooting

### "File not found" Error
- Verify Android Studio is installed at `C:\Program Files\Android\Android Studio\`
- Check that the path is exactly: `C:\Program Files\Android\Android Studio\plugins\android\lib\`

### "Not a valid ZIP/JAR file" Error
- The JAR file might be corrupted or the path is incorrect
- Try running: `python test_jar.py` first to verify connectivity

### No Python Found Error
1. Install Python from https://www.python.org/downloads/
2. During installation, check **"Add Python to PATH"**
3. Restart command prompt and try again

### Large Memory Usage
- These JARs can contain thousands of files
- Python loads them into memory but releases after processing
- This is normal and expected

## JAR File Analysis

### wizard-template.jar
Contains Android project templates for the new project wizard.

**Look for:**
- `android/templates/` - Template definitions
- `.properties` files - Configuration
- `description.xml` - Template metadata

### android-gradle.jar
Main Android Gradle Plugin implementation.

**Look for:**
- `com/android/build/gradle/` - Plugin classes
- `com/android/build/gradle/tasks/` - Build tasks
- `.gradle` - Gradle scripts
- `.properties` - Plugin configuration

### libagp-version.jar
AGP version information and compatibility details.

**Look for:**
- Version strings in `.properties` files
- `com/android/build/gradle/internal/` - Version utilities
- Build configuration requirements
- Compatibility mappings

## Advanced Usage

### Custom Keyword Search

Edit the `SEARCH_KEYWORDS` list in the script:

```python
SEARCH_KEYWORDS = [
    'agp', 'gradle', 'version', 'buildtools', 'compilesdk',
    'myCustomKeyword',  # Add your own
]
```

### Custom Config Extensions

Edit the `CONFIG_EXTENSIONS` tuple:

```python
CONFIG_EXTENSIONS = (
    '.properties', '.xml', '.gradle', '.json', '.txt',
    '.myExtension',  # Add your own
)
```

### Limiting Output

To inspect only one JAR, modify `JAR_FILES`:

```python
JAR_FILES = [
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"
]
```

## Performance Notes

- **wizard-template.jar**: ~2-3 seconds
- **android-gradle.jar**: ~5-10 seconds  
- **libagp-version.jar**: ~1-2 seconds
- **Total inspection time**: ~10-15 seconds

Processing time depends on:
- Disk speed (SSD faster than HDD)
- Number of entries (android-gradle has 10,000+)
- File content size
- System load

## License & Attribution

These inspection scripts use only Python standard library and never modify or extract files from the JAR archives. All JAR files are property of Google/JetBrains.

---

**Created:** 2024
**Purpose:** Educational - understand Android Studio plugin structure
**Compatibility:** Windows, macOS, Linux (Python 3.6+)

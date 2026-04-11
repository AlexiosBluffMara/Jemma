# QUICK START GUIDE - JAR Inspector

## TL;DR - Just Run This

```bash
python d:\JemmaRepo\Jemma\jar_inspector_final.py
```

Or double-click:
```
d:\JemmaRepo\Jemma\run_jar_inspector.bat
```

## What Gets Inspected

Three JAR files from Android Studio plugins:

| JAR File | Location | Contains |
|----------|----------|----------|
| wizard-template.jar | plugins/android/lib/ | Project wizard templates |
| android-gradle.jar | plugins/android/lib/ | Gradle plugin implementation |
| libagp-version.jar | plugins/android/lib/ | AGP version info |

## What You'll See

For each JAR:

1. **Entry Count** - Total files inside
   ```
   Total entries: 12,847
   Files (not directories): 12,402
   ```

2. **File Types** - Breakdown by extension
   ```
   📊 FILE TYPE DISTRIBUTION
      .class      : 4829 files
      .properties :  142 files
      .xml        :   89 files
   ```

3. **Keyword Matches** - Files containing:
   - agp, gradle, version, buildtools, compilesdk
   - android, sdk, ndk, plugin, task, variant
   
   ```
   🔍 KEYWORD MATCHES (234 found)
      ✓ com/android/gradle/internal/TaskManager.class
      ✓ META-INF/gradle-plugins/com.android.application.properties
   ```

4. **Config Files** - All .properties, .xml, .gradle, .json
   ```
   ⚙️  CONFIGURATION FILES (47 found)
      📝 META-INF/gradle-plugins/com.android.application.properties
      📝 build.gradle
   ```

5. **File Contents** - First 50 lines of each matching file
   ```
   📖 CONTENT OF KEY FILES
      ▼▼▼ META-INF/gradle-plugins/com.android.application.properties
      implementation-class=com.android.build.gradle.AppPlugin
      ▲▲▲
   ```

## Requirements

✅ Python 3.6+ (already in your system)
✅ Android Studio installed at `C:\Program Files\Android\Android Studio\`
✅ Windows/macOS/Linux

## Scripts Available

| Script | Use Case |
|--------|----------|
| `jar_inspector_final.py` | **MAIN** - Comprehensive inspection |
| `run_jar_inspector.bat` | Windows batch wrapper (easiest) |
| `inspect_all_jars.py` | Alternative minimal version |
| `test_jar.py` | Quick test - read one JAR |
| `quick_inspect.py` | List entries only |

## Common Tasks

### Task: Find all Gradle plugin files
**Output Section:** "🔍 KEYWORD MATCHES" with keyword 'gradle'
**Look for:** `META-INF/gradle-plugins/` entries

### Task: Find version information
**Output Section:** "🔍 KEYWORD MATCHES" with keyword 'version'
**Files to read:** `.properties` files in libagp-version.jar

### Task: Find build configuration
**Output Section:** "⚙️ CONFIGURATION FILES"
**Look for:** `.properties` and `.xml` files

### Task: Find source code for specific task
**Output Section:** "🔍 KEYWORD MATCHES" with keyword 'task'
**Then look at:** Content section for matching `.class` file references

## Understanding Entry Paths

```
com/android/build/gradle/internal/TaskManager.class
├─ com/                      (package: com)
├─ android/                  (package: android)
├─ build/                    (package: build)
├─ gradle/                   (package: gradle)
├─ internal/                 (package: internal)
└─ TaskManager.class         (the actual class file)
```

## File Types Explained

| Extension | Purpose |
|-----------|---------|
| `.class` | Compiled Java bytecode |
| `.properties` | Configuration key-value pairs |
| `.xml` | Structured data/configuration |
| `.gradle` | Gradle build scripts |
| `.json` | Structured data (JSON format) |
| `.jar` | Nested Java archives |
| `/` | Directory (folder) marker |

## Common Keywords Found

| Keyword | Means |
|---------|-------|
| **agp** | Android Gradle Plugin |
| **gradle** | Gradle build system |
| **version** | Version strings/info |
| **buildtools** | Build utilities |
| **compilesdk** | Compilation SDK level |
| **android** | Android framework |
| **variant** | Build variant (debug/release) |
| **task** | Gradle task |
| **plugin** | Gradle plugin |

## Tips & Tricks

### 💡 Save Output to File

**On Windows:**
```bash
python d:\JemmaRepo\Jemma\jar_inspector_final.py > results.txt
```

**Then open results.txt in your editor**

### 💡 Search Output for Specific Text

After running, use Ctrl+F in your terminal/editor to find:
- "gradle" → All Gradle-related entries
- "version" → Version information
- ".properties" → Configuration files
- "Error" → Any reading errors

### 💡 Focus on One JAR

Edit `jar_inspector_final.py`, find line:
```python
JAR_FILES = [
    r"C:\Program Files\...\libagp-version.jar",  # Keep only this line
]
```

### 💡 Add Custom Keywords

Edit `jar_inspector_final.py`, find line:
```python
SEARCH_KEYWORDS = [
    'agp', 'gradle',
    'yourKeyword',  # ← Add here
]
```

## Troubleshooting

### ❌ "File not found"
→ Android Studio not installed at expected location
→ Check: `C:\Program Files\Android\Android Studio\` exists

### ❌ "Not a valid ZIP/JAR file"  
→ JAR file corrupted or path wrong
→ Try: `python d:\JemmaRepo\Jemma\test_jar.py` to verify

### ❌ "Python is not recognized"
→ Python not installed
→ Install from: https://www.python.org/downloads/
→ Check "Add Python to PATH" during installation

### ❌ "No entries found"
→ Try: `python d:\JemmaRepo\Jemma\quick_inspect.py` for basic check
→ File exists but may be very small or unusual format

## Performance

| JAR | Size | Time |
|-----|------|------|
| wizard-template.jar | Small | 2-3 sec |
| android-gradle.jar | Large (10K+ entries) | 5-10 sec |
| libagp-version.jar | Small | 1-2 sec |
| **Total** | **~30MB** | **~10-15 sec** |

## What's NOT Extracted

✅ Files remain in JAR (not written to disk)
✅ Original files unchanged
✅ No temporary files created
✅ No directories extracted
✅ 100% read-only operation

## Next Steps

1. **Run the inspector:**
   ```
   python d:\JemmaRepo\Jemma\jar_inspector_final.py
   ```

2. **Review the output** for:
   - Gradle plugin classes
   - Version information
   - Build configuration
   - Custom keywords you added

3. **Deep dive into files:**
   - Find interesting `.properties` files
   - Extract entry paths for reference
   - Note version numbers and build requirements

4. **Extract specific files** (optional):
   - Use 7-Zip or WinRAR to extract individual files by path
   - Or modify script to extract specific entries only

## More Information

- See: `JAR_INSPECTOR_README.md` for detailed documentation
- Full docs: Open `d:\JemmaRepo\Jemma\jar_inspector_final.py` and read comments
- Python zipfile docs: https://docs.python.org/3/library/zipfile.html

---

**Ready to start?** → `python d:\JemmaRepo\Jemma\jar_inspector_final.py`

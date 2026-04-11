import zipfile
import sys

jars = [
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\wizard-template.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\android-gradle.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"
]

for jar_path in jars:
    print(f"\n{'='*80}")
    print(f"{jar_path.split(chr(92))[-1]}")
    print(f"{'='*80}")
    with zipfile.ZipFile(jar_path) as z:
        entries = z.namelist()
        print(f"Total: {len(entries)} entries\n")
        print("Entries:")
        for e in sorted(entries)[:15]:
            print(f"  {e}")
        if len(entries) > 15:
            print(f"  ... +{len(entries)-15} more")

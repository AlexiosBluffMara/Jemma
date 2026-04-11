import zipfile

jar1 = r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"

try:
    with zipfile.ZipFile(jar1) as z:
        entries = z.namelist()
        print(f"✓ {len(entries)} entries found\n")
        for e in sorted(entries):
            print(e)
except FileNotFoundError:
    print("❌ File not found")
except Exception as e:
    print(f"❌ Error: {e}")

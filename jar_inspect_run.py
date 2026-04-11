import zipfile, os, re, pathlib

lib_dir = pathlib.Path(r'C:\Program Files\Android\Android Studio\plugins\android\lib')

pattern = re.compile(r'(agp|gradle|version)', re.IGNORECASE)
explicit = ['wizard-template.jar', 'android-gradle.jar', 'libagp-version.jar']
explicit_paths = [lib_dir / j for j in explicit]

# discover by glob
glob_matches = [p for p in lib_dir.glob('*.jar') if pattern.search(p.name)]
all_candidates = sorted(set(glob_matches + [p for p in explicit_paths]), key=lambda x: x.name)

print('=== STEP 1: RELEVANT JARS DISCOVERED ===')
for p in all_candidates:
    print(f'  {"EXISTS" if p.exists() else "MISSING"}: {p.name}')
print(f'  TOTAL DISCOVERED: {len(all_candidates)}')

STRONG_AGP = re.compile(r'(?i)(agp.?version|android.?gradle.?plugin.?version|CURRENT_AGP_VERSION|AGP_VERSION)')
SDK_PAT = re.compile(r'(?i)(compileSdk|buildTools|compileSdkVersion|buildToolsVersion)')
CANDIDATE_ENTRY = re.compile(r'(?i)(agp|version|gradle|properties|manifest|plugin)', re.IGNORECASE)

print('\n=== STEP 2-5: JAR INSPECTION ===')
for jar_path in all_candidates:
    if not jar_path.exists():
        print(f'\n[MISSING - NOT INSPECTED]: {jar_path.name}')
        continue
    print(f'\n--- JAR: {jar_path.name} ---')
    try:
        with zipfile.ZipFile(str(jar_path), 'r') as zf:
            all_entries = zf.namelist()
            candidate_entries = sorted(set(
                [e for e in all_entries if CANDIDATE_ENTRY.search(e) and not e.endswith('.class')]
                + [e for e in all_entries if e.startswith('META-INF/') and not e.endswith('.class')]
            ))
            print(f'  Total entries in jar: {len(all_entries)}')
            print(f'  Candidate entries inspected ({len(candidate_entries)}):')
            for e in candidate_entries:
                print(f'    {e}')
            agp_hits = []
            sdk_hits = []
            for entry in candidate_entries:
                try:
                    raw = zf.read(entry)
                    try:
                        text = raw.decode('utf-8')
                    except Exception:
                        text = raw.decode('latin-1', errors='replace')
                    for line in text.splitlines():
                        if STRONG_AGP.search(line):
                            agp_hits.append((entry, line.strip()))
                        if SDK_PAT.search(line):
                            sdk_hits.append((entry, line.strip()))
                except Exception as e2:
                    print(f'    [READ ERROR {entry}]: {e2}')
            if agp_hits:
                print(f'  AGP VERSION EVIDENCE FOUND:')
                for entry, line in agp_hits:
                    print(f'    [{entry}] => {repr(line)}')
            else:
                print(f'  AGP VERSION: NOT FOUND in any inspected entry')
            if sdk_hits:
                print(f'  compileSdk/buildTools EVIDENCE FOUND:')
                for entry, line in sdk_hits:
                    print(f'    [{entry}] => {repr(line)}')
            else:
                print(f'  compileSdk/buildTools: NOT FOUND in any inspected entry')
    except Exception as e:
        print(f'  [JAR OPEN ERROR]: {e}')

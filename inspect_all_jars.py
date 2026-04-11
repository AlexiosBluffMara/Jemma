import sys
import zipfile
import os

def main():
    jars = [
        r"C:\Program Files\Android\Android Studio\plugins\android\lib\wizard-template.jar",
        r"C:\Program Files\Android\Android Studio\plugins\android\lib\android-gradle.jar",
        r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"
    ]
    
    keywords = ('agp', 'gradle', 'version', 'buildtools', 'compilesdk')
    
    for jar_path in jars:
        print(f"\n{'='*90}")
        print(f"{os.path.basename(jar_path)}")
        print(f"{'='*90}\n")
        
        try:
            z = zipfile.ZipFile(jar_path, 'r')
            entries = z.namelist()
            
            print(f"Total entries: {len(entries)}\n")
            
            # Find keyword entries
            kw_entries = [e for e in entries if any(kw in e.lower() for kw in keywords)]
            
            # Find config files
            config_exts = ('.properties', '.xml', '.gradle', '.json')
            cfg_entries = [e for e in entries if e.lower().endswith(config_exts)]
            
            print(f"Entries list ({len(entries)} total):")
            for e in sorted(entries):
                print(f"  {e}")
            
            if kw_entries:
                print(f"\n\nKeyword matches ({len(kw_entries)}):")
                for e in sorted(kw_entries):
                    print(f"  ✓ {e}")
                    
                print(f"\n\nContent of keyword matches:")
                for e in sorted(kw_entries)[:10]:
                    if not e.endswith('/'):
                        try:
                            content = z.read(e)
                            text = content.decode('utf-8', errors='ignore')
                            if text.strip():
                                print(f"\n─ {e}")
                                for line in text.split('\n')[:30]:
                                    print(f"  {line}")
                                if len(text.split('\n')) > 30:
                                    print(f"  ... ({len(text.split(chr(10)))} lines total)")
                        except Exception as ex:
                            print(f"\n─ {e} [Error: {ex}]")
            
            if cfg_entries:
                print(f"\n\nConfig files ({len(cfg_entries)}):")
                for e in sorted(cfg_entries)[:20]:
                    print(f"  {e}")
                    
                print(f"\n\nContent of config files:")
                for e in sorted(cfg_entries)[:10]:
                    if not e.endswith('/'):
                        try:
                            content = z.read(e)
                            text = content.decode('utf-8', errors='ignore')
                            if text.strip():
                                print(f"\n─ {e}")
                                for line in text.split('\n')[:30]:
                                    print(f"  {line}")
                                if len(text.split('\n')) > 30:
                                    print(f"  ... ({len(text.split('\n'))} lines total)")
                        except Exception as ex:
                            print(f"\n─ {e} [Error: {ex}]")
            
            z.close()
            
        except FileNotFoundError:
            print(f"❌ File not found: {jar_path}")
        except zipfile.BadZipFile:
            print(f"❌ Not a valid ZIP/JAR file")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()

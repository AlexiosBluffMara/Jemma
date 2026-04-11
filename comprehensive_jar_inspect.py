#!/usr/bin/env python3
"""
Comprehensive JAR file inspection using Python's zipfile module.
Read-only access - no extraction to disk.
"""

import zipfile
import os
import sys
from collections import defaultdict

# Target JAR files
JAR_FILES = [
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\wizard-template.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\android-gradle.jar",
    r"C:\Program Files\Android\Android Studio\plugins\android\lib\libagp-version.jar"
]

# Search keywords
KEYWORDS = ['agp', 'gradle', 'version', 'buildtools', 'compilesdk']
CONFIG_EXTENSIONS = ('.properties', '.xml', '.gradle', '.json', '.txt')

def analyze_jar(jar_path):
    """Analyze a single JAR file"""
    
    if not os.path.exists(jar_path):
        return {"error": f"File not found: {jar_path}"}
    
    jar_name = os.path.basename(jar_path)
    result = {
        "jar": jar_name,
        "path": jar_path,
        "status": "success",
        "total_entries": 0,
        "entries_by_type": defaultdict(int),
        "keyword_matches": [],
        "config_files": [],
        "content": {}
    }
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            all_entries = jar.namelist()
            result["total_entries"] = len(all_entries)
            
            # Categorize entries
            for entry in all_entries:
                # Skip directories
                if entry.endswith('/'):
                    continue
                
                # Count by extension
                ext = os.path.splitext(entry)[1] or "no_ext"
                result["entries_by_type"][ext] += 1
                
                entry_lower = entry.lower()
                
                # Find keyword matches
                for keyword in KEYWORDS:
                    if keyword in entry_lower:
                        result["keyword_matches"].append(entry)
                        break
                
                # Find config files
                if entry_lower.endswith(CONFIG_EXTENSIONS):
                    result["config_files"].append(entry)
            
            # Read content of matching files
            for entry in result["keyword_matches"][:20]:  # Limit to first 20
                if not entry.endswith('/'):
                    try:
                        content = jar.read(entry)
                        try:
                            text_content = content.decode('utf-8', errors='ignore').strip()
                            if text_content and len(text_content) < 50000:  # Limit size
                                result["content"][entry] = text_content
                        except:
                            result["content"][entry] = f"[Binary content: {len(content)} bytes]"
                    except Exception as e:
                        result["content"][entry] = f"[Error: {str(e)}]"
            
            # Read config files too
            for entry in result["config_files"][:20]:
                if not entry.endswith('/') and entry not in result["content"]:
                    try:
                        content = jar.read(entry)
                        try:
                            text_content = content.decode('utf-8', errors='ignore').strip()
                            if text_content and len(text_content) < 50000:
                                result["content"][entry] = text_content
                        except:
                            result["content"][entry] = f"[Binary content: {len(content)} bytes]"
                    except Exception as e:
                        result["content"][entry] = f"[Error: {str(e)}]"
                    
    except zipfile.BadZipFile:
        result["error"] = "Invalid JAR file format"
        result["status"] = "error"
    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"
    
    return result

def format_output(results):
    """Format results for display"""
    output = []
    output.append("\n" + "="*100)
    output.append("ANDROID STUDIO JAR FILE INSPECTION")
    output.append("="*100 + "\n")
    
    for result in results:
        jar_name = result.get("jar", "Unknown")
        output.append(f"\n📦 JAR: {jar_name}")
        output.append("-" * 100)
        
        if result.get("status") == "error":
            output.append(f"❌ Error: {result.get('error', 'Unknown error')}\n")
            continue
        
        # Summary
        output.append(f"✅ Total entries: {result['total_entries']}")
        output.append(f"\n📊 Entries by type:")
        for ext, count in sorted(result['entries_by_type'].items(), key=lambda x: -x[1])[:10]:
            output.append(f"   {ext:15} : {count:5} files")
        
        # Keyword matches
        if result['keyword_matches']:
            output.append(f"\n🔍 KEYWORD MATCHES ({len(result['keyword_matches'])} found):")
            for entry in sorted(result['keyword_matches'])[:30]:
                output.append(f"   ✓ {entry}")
            if len(result['keyword_matches']) > 30:
                output.append(f"   ... and {len(result['keyword_matches']) - 30} more")
        
        # Config files
        if result['config_files']:
            output.append(f"\n⚙️  CONFIG FILES ({len(result['config_files'])} found):")
            for entry in sorted(result['config_files'])[:30]:
                output.append(f"   📝 {entry}")
            if len(result['config_files']) > 30:
                output.append(f"   ... and {len(result['config_files']) - 30} more")
        
        # Content
        if result['content']:
            output.append(f"\n📖 FILE CONTENTS:")
            for entry, content in sorted(result['content'].items()):
                output.append(f"\n   {'▶'*30}")
                output.append(f"   {entry}")
                output.append(f"   {'▶'*30}")
                lines = content.split('\n')
                for line in lines[:50]:
                    output.append(f"   {line}")
                if len(lines) > 50:
                    output.append(f"   ... ({len(lines) - 50} more lines)")
        
        output.append("")
    
    output.append("="*100)
    output.append("✅ Inspection complete")
    output.append("="*100 + "\n")
    
    return "\n".join(output)

# Main execution
if __name__ == "__main__":
    results = []
    for jar_path in JAR_FILES:
        result = analyze_jar(jar_path)
        results.append(result)
    
    formatted_output = format_output(results)
    print(formatted_output)

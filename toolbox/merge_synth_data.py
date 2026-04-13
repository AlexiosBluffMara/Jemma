#!/usr/bin/env python3
"""
Merge synthetic data back into the main training dataset.

Reads generated JSONL files from datasets/synth/, strips internal _meta fields,
deduplicates, and appends to datasets/construction-cracks-train.jsonl (or a new file).

Usage:
    python toolbox/merge_synth_data.py
    python toolbox/merge_synth_data.py --target datasets/construction-full-train.jsonl
    python toolbox/merge_synth_data.py --stats-only
"""

import argparse
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = ROOT / "datasets" / "synth"
DEFAULT_TARGET = ROOT / "datasets" / "construction-full-train.jsonl"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def load_hashes_from_jsonl(path: Path) -> set:
    hashes = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                for m in obj.get("messages", []):
                    if m.get("role") == "assistant":
                        hashes.add(content_hash(m["content"]))
    return hashes


def main():
    p = argparse.ArgumentParser(description="Merge synthetic data into training dataset")
    p.add_argument("--target", default=str(DEFAULT_TARGET),
                    help="Target JSONL file to merge into")
    p.add_argument("--stats-only", action="store_true",
                    help="Just print stats, don't merge")
    p.add_argument("--include-meta", action="store_true",
                    help="Keep _meta field in merged output")
    args = p.parse_args()

    target = Path(args.target)

    if not SYNTH_DIR.exists():
        print(f"No synth data found at {SYNTH_DIR}")
        return

    # Collect all synth data
    synth_files = sorted(SYNTH_DIR.glob("*.jsonl"))
    synth_files = [f for f in synth_files if f.name != "generation_stats.jsonl"]

    if not synth_files:
        print("No synthetic JSONL files found")
        return

    # Stats
    total_entries = 0
    per_track = {}
    all_entries = []

    for f in synth_files:
        track = f.stem
        count = 0
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                obj = json.loads(line)
                if not args.include_meta:
                    obj.pop("_meta", None)
                all_entries.append(obj)
                count += 1
        per_track[track] = count
        total_entries += count

    print(f"Synthetic data summary:")
    print(f"  Source: {SYNTH_DIR}")
    print(f"  Files: {len(synth_files)}")
    print(f"  Total entries: {total_entries}")
    for track, count in sorted(per_track.items()):
        print(f"    {track}: {count}")

    if args.stats_only:
        return

    # Load existing hashes from target and original
    existing_hashes = set()
    for jsonl in (ROOT / "datasets").glob("*.jsonl"):
        existing_hashes.update(load_hashes_from_jsonl(jsonl))

    # Deduplicate
    new_entries = []
    dupes = 0
    for obj in all_entries:
        is_dup = False
        for m in obj.get("messages", []):
            if m.get("role") == "assistant":
                h = content_hash(m["content"])
                if h in existing_hashes:
                    is_dup = True
                    break
                existing_hashes.add(h)
        if is_dup:
            dupes += 1
        else:
            new_entries.append(obj)

    print(f"\n  Duplicates removed: {dupes}")
    print(f"  New unique entries: {len(new_entries)}")

    if not new_entries:
        print("  Nothing new to merge.")
        return

    # Write
    with open(target, "a", encoding="utf-8") as f:
        for obj in new_entries:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(f"\n  Merged {len(new_entries)} entries into {target}")


if __name__ == "__main__":
    main()

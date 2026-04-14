#!/usr/bin/env python3
"""Quick state check — delete after use."""
import sqlite3, json, os

conn = sqlite3.connect("datasets/civic_data.db")
print("=== DB Tables ===")
for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    cnt = conn.execute(f"SELECT COUNT(*) FROM [{row[0]}]").fetchone()[0]
    print(f"  {row[0]}: {cnt} rows")

print("\n=== Training Data ===")
sft = "datasets/civic_sft_train.jsonl"
if os.path.exists(sft):
    with open(sft) as f:
        lines = f.readlines()
    print(f"  civic_sft_train.jsonl: {len(lines)} samples")
    d = json.loads(lines[0])
    print(f"  Keys: {list(d.keys())}")
else:
    print("  NO training data found")

print("\n=== Checkpoints ===")
if os.path.exists("checkpoints"):
    for root, dirs, files in os.walk("checkpoints"):
        for fn in files:
            fp = os.path.join(root, fn)
            sz = os.path.getsize(fp)
            print(f"  {fp}: {sz/1024:.1f} KB")
else:
    print("  No checkpoints directory")

print("\n=== Benchmark Results ===")
if os.path.exists("benchmarks/results"):
    for fn in sorted(os.listdir("benchmarks/results")):
        fp = os.path.join("benchmarks/results", fn)
        sz = os.path.getsize(fp)
        print(f"  {fn}: {sz/1024:.1f} KB")

print("\n=== Docs ===")
if os.path.exists("docs"):
    for fn in sorted(os.listdir("docs")):
        if fn.endswith(".md"):
            print(f"  {fn}")

print("\n=== Datasets dir ===")
for fn in sorted(os.listdir("datasets")):
    fp = os.path.join("datasets", fn)
    if os.path.isfile(fp):
        sz = os.path.getsize(fp)
        unit = "KB" if sz < 1024*1024 else "MB"
        val = sz/1024 if sz < 1024*1024 else sz/(1024*1024)
        print(f"  {fn}: {val:.1f} {unit}")
    else:
        cnt = len(os.listdir(fp)) if os.path.isdir(fp) else 0
        print(f"  {fn}/ ({cnt} items)")

conn.close()

#!/usr/bin/env python3
"""
Jemma Synthetic Data — Live Monitor Dashboard
==============================================
Tails all JSONL output files in real-time, showing:
  - Every new entry as it's written (stream, model, topic, content preview)
  - Raw JSON structure
  - File sizes and growth rates
  - Per-stream and global stats
  - Throughput calculations

Usage:
    python toolbox/live_monitor.py
    python toolbox/live_monitor.py --compact          # shorter previews
    python toolbox/live_monitor.py --raw              # show full raw JSON
    python toolbox/live_monitor.py --stream building_codes  # filter one stream
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SYNTH_DIR = PROJECT_ROOT / "datasets" / "synth"
STATS_FILE = SYNTH_DIR / "multistream_stats.jsonl"

# ANSI color codes
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_DIM     = "\033[2m"
C_RED     = "\033[91m"
C_GREEN   = "\033[92m"
C_YELLOW  = "\033[93m"
C_BLUE    = "\033[94m"
C_MAGENTA = "\033[95m"
C_CYAN    = "\033[96m"
C_WHITE   = "\033[97m"
C_BG_DARK = "\033[48;5;235m"

STREAM_COLORS = {
    "construction_qa":          C_GREEN,
    "image_descriptions":       C_CYAN,
    "blueprint_interpretation": C_BLUE,
    "safety_inspections":       C_RED,
    "object_detection_labels":  C_YELLOW,
    "building_codes":           C_MAGENTA,
    "disaster_assessment":      C_RED + C_BOLD,
    "materials_database":       C_WHITE,
}

MODEL_ICONS = {
    "gemma-4-26b-a4b-it": "🔷 26B-MoE",
    "gemma-4-31b-it":     "🟢 31B-Dense",
}


def sizeof_fmt(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def truncate(text, maxlen=200):
    text = text.replace("\n", " ").strip()
    if len(text) <= maxlen:
        return text
    return text[:maxlen] + "..."


def render_separator(char="─", width=100):
    return C_DIM + char * width + C_RESET


def render_entry(obj, show_raw=False, compact=False):
    """Render a single JSONL entry with full detail."""
    meta = obj.get("_meta", {})
    stream = meta.get("stream", "unknown")
    model = meta.get("model", "unknown")
    topic = meta.get("topic", "")
    gen_at = meta.get("generated_at", "")
    iteration = meta.get("iteration", "?")

    sc = STREAM_COLORS.get(stream, C_WHITE)
    mi = MODEL_ICONS.get(model, model)

    lines = []
    lines.append(render_separator("═"))
    lines.append(
        f"  {C_BOLD}{sc}▶ NEW ENTRY{C_RESET}  "
        f"{sc}{stream}{C_RESET}  #{iteration}  "
        f"{C_DIM}@ {gen_at}{C_RESET}"
    )
    lines.append(
        f"  {C_DIM}Model:{C_RESET} {mi}  "
        f"{C_DIM}Topic:{C_RESET} {C_YELLOW}{topic}{C_RESET}"
    )
    lines.append(render_separator("─"))

    # Show content based on data type
    messages = obj.get("messages")
    if messages:
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            role_color = C_CYAN if role == "user" else C_GREEN
            role_icon = "👤 USER" if role == "user" else "🤖 ASSISTANT"
            preview_len = 120 if compact else 300
            lines.append(f"  {role_color}{C_BOLD}{role_icon}{C_RESET}")
            lines.append(f"  {truncate(content, preview_len)}")
            lines.append("")
    else:
        # Non-chat format — show top-level keys and previews
        for key, val in obj.items():
            if key == "_meta":
                continue
            if isinstance(val, str):
                preview_len = 80 if compact else 200
                lines.append(f"  {C_CYAN}{key}:{C_RESET} {truncate(val, preview_len)}")
            elif isinstance(val, dict):
                lines.append(f"  {C_CYAN}{key}:{C_RESET} {C_DIM}{{...{len(val)} keys}}{C_RESET}")
                for k2, v2 in list(val.items())[:3]:
                    v_preview = truncate(str(v2), 80 if compact else 150)
                    lines.append(f"    {C_DIM}{k2}:{C_RESET} {v_preview}")
                if len(val) > 3:
                    lines.append(f"    {C_DIM}... +{len(val)-3} more{C_RESET}")
            elif isinstance(val, list):
                lines.append(f"  {C_CYAN}{key}:{C_RESET} {C_DIM}[{len(val)} items]{C_RESET}")
                for item in val[:2]:
                    lines.append(f"    {truncate(str(item), 80 if compact else 150)}")
                if len(val) > 2:
                    lines.append(f"    {C_DIM}... +{len(val)-2} more{C_RESET}")
            else:
                lines.append(f"  {C_CYAN}{key}:{C_RESET} {val}")

    if show_raw:
        lines.append(render_separator("·"))
        lines.append(f"  {C_DIM}RAW JSON:{C_RESET}")
        raw = json.dumps(obj, indent=2, ensure_ascii=False)
        for rline in raw.split("\n")[:40]:
            lines.append(f"  {C_DIM}{rline}{C_RESET}")
        if raw.count("\n") > 40:
            lines.append(f"  {C_DIM}... truncated ({raw.count(chr(10))} lines total){C_RESET}")

    # Size of this entry
    entry_size = len(json.dumps(obj, ensure_ascii=False).encode())
    lines.append(f"  {C_DIM}Entry size: {sizeof_fmt(entry_size)}{C_RESET}")
    lines.append(render_separator("─"))

    return "\n".join(lines)


def render_stats_banner(stats, file_sizes, start_time):
    """Render the periodic stats summary."""
    total = stats.get("total_generated", 0)
    per_stream = stats.get("per_stream", {})
    elapsed = time.time() - start_time
    rate = total / (elapsed / 3600) if elapsed > 60 else 0

    lines = []
    lines.append("")
    lines.append(f"  {C_BOLD}{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
    lines.append(f"  {C_BOLD}{C_CYAN}║  📊 LIVE STATS                                                 ║{C_RESET}")
    lines.append(f"  {C_BOLD}{C_CYAN}╠══════════════════════════════════════════════════════════════════╣{C_RESET}")

    ts = stats.get("timestamp", "")
    lines.append(f"  {C_CYAN}║{C_RESET}  Timestamp:    {ts}")
    lines.append(f"  {C_CYAN}║{C_RESET}  Total entries: {C_BOLD}{C_GREEN}{total}{C_RESET}    "
                 f"Failures: {stats.get('total_failures', 0)}    "
                 f"Dups: {stats.get('total_duplicates', 0)}")
    lines.append(f"  {C_CYAN}║{C_RESET}  Throughput:   {C_YELLOW}{rate:.1f} entries/hr{C_RESET}  "
                 f"({total / max(elapsed/60, 1):.2f}/min)")
    lines.append(f"  {C_CYAN}║{C_RESET}")

    # Per-stream breakdown
    lines.append(f"  {C_CYAN}║{C_RESET}  {C_BOLD}Per-Stream Breakdown:{C_RESET}")
    for name in sorted(per_stream.keys()):
        count = per_stream[name]
        sc = STREAM_COLORS.get(name, C_WHITE)
        bar = "█" * min(count, 50) + "░" * max(0, 50 - count)
        fsize = file_sizes.get(name, 0)
        lines.append(
            f"  {C_CYAN}║{C_RESET}    {sc}{name:30s}{C_RESET} "
            f"{count:4d}  {C_DIM}{bar[:30]}{C_RESET}  "
            f"{sizeof_fmt(fsize)}"
        )

    # Total dataset size
    total_size = sum(file_sizes.values())
    lines.append(f"  {C_CYAN}║{C_RESET}")
    lines.append(f"  {C_CYAN}║{C_RESET}  {C_BOLD}Total dataset size: {sizeof_fmt(total_size)}{C_RESET}")

    # Time remaining estimate
    cutoff = datetime(2026, 4, 15, 23, 0, 0, tzinfo=timezone.utc)
    remaining = (cutoff - datetime.now(timezone.utc)).total_seconds()
    if remaining > 0:
        hours_left = remaining / 3600
        est_more = rate * hours_left if rate > 0 else 0
        lines.append(
            f"  {C_CYAN}║{C_RESET}  Free period remaining: "
            f"{C_YELLOW}{hours_left:.1f}h{C_RESET}  "
            f"Est. additional entries: {C_GREEN}~{int(est_more)}{C_RESET}"
        )

    lines.append(f"  {C_BOLD}{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
    lines.append("")
    return "\n".join(lines)


def get_file_sizes():
    sizes = {}
    for f in SYNTH_DIR.glob("*.jsonl"):
        if f.name == "multistream_stats.jsonl":
            continue
        stream_name = f.stem
        sizes[stream_name] = f.stat().st_size
    return sizes


def tail_files(filter_stream=None, show_raw=False, compact=False):
    """Watch all JSONL files for new lines and display them live."""

    # Collect initial file positions (seek to end)
    file_positions = {}
    jsonl_files = {}
    for f in SYNTH_DIR.glob("*.jsonl"):
        if f.name == "multistream_stats.jsonl":
            continue
        stream_name = f.stem
        if filter_stream and stream_name != filter_stream:
            continue
        file_positions[stream_name] = f.stat().st_size
        jsonl_files[stream_name] = f

    stats_pos = STATS_FILE.stat().st_size if STATS_FILE.exists() else 0

    start_time = time.time()
    entries_seen = 0
    last_stats = None

    print(f"\n{C_BOLD}{C_GREEN}{'='*80}{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}  🔴 JEMMA LIVE MONITOR — Synthetic Data Generation{C_RESET}")
    print(f"{C_BOLD}{C_GREEN}{'='*80}{C_RESET}")
    print(f"  Watching: {SYNTH_DIR}")
    print(f"  Streams:  {', '.join(sorted(jsonl_files.keys())) or 'ALL'}")
    print(f"  Mode:     {'compact' if compact else 'detailed'}  |  Raw JSON: {'ON' if show_raw else 'OFF'}")
    print(f"  Press Ctrl+C to stop")
    print(f"{C_DIM}{'─'*80}{C_RESET}\n")

    # Show initial stats
    if STATS_FILE.exists():
        last_line = ""
        for line in STATS_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_line = line
        if last_line:
            try:
                last_stats = json.loads(last_line)
                file_sizes = get_file_sizes()
                print(render_stats_banner(last_stats, file_sizes, start_time))
            except json.JSONDecodeError:
                pass

    print(f"  {C_YELLOW}⏳ Waiting for new entries...{C_RESET}\n")

    try:
        while True:
            found_new = False

            # Check each data file for new lines
            for stream_name, filepath in jsonl_files.items():
                try:
                    current_size = filepath.stat().st_size
                except OSError:
                    continue

                if current_size > file_positions[stream_name]:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        fh.seek(file_positions[stream_name])
                        new_data = fh.read()
                    file_positions[stream_name] = current_size

                    for line in new_data.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            print(f"  {C_RED}⚠ Parse error in {stream_name}: {line[:100]}{C_RESET}")
                            continue

                        entries_seen += 1
                        print(render_entry(obj, show_raw=show_raw, compact=compact))
                        found_new = True

            # Check stats file for new stats
            if STATS_FILE.exists():
                try:
                    current_stats_size = STATS_FILE.stat().st_size
                except OSError:
                    current_stats_size = stats_pos

                if current_stats_size > stats_pos:
                    with open(STATS_FILE, "r", encoding="utf-8") as fh:
                        fh.seek(stats_pos)
                        new_stats_data = fh.read()
                    stats_pos = current_stats_size

                    for line in new_stats_data.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            last_stats = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                    if last_stats:
                        file_sizes = get_file_sizes()
                        print(render_stats_banner(last_stats, file_sizes, start_time))

            if not found_new:
                time.sleep(0.5)  # poll every 500ms

    except KeyboardInterrupt:
        print(f"\n\n{C_BOLD}{C_YELLOW}  ⏹  Monitor stopped.{C_RESET}")
        if last_stats:
            file_sizes = get_file_sizes()
            print(render_stats_banner(last_stats, file_sizes, start_time))
        print()


def main():
    parser = argparse.ArgumentParser(description="Jemma Synthetic Data — Live Monitor")
    parser.add_argument("--raw", action="store_true", help="Show full raw JSON for each entry")
    parser.add_argument("--compact", action="store_true", help="Shorter content previews")
    parser.add_argument("--stream", type=str, default=None,
                        help="Filter to a single stream (e.g. building_codes)")
    args = parser.parse_args()
    tail_files(filter_stream=args.stream, show_raw=args.raw, compact=args.compact)


if __name__ == "__main__":
    main()

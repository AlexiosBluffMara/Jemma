"""
Download civic datasets from public APIs (no Kaggle credentials needed).

Sources:
  - Chicago Open Data Portal (Socrata API) — free, no auth
  - ISU/Normal open data (scraped in data_ingestion.py already)

Saves CSVs to datasets/kaggle/ for compatibility with existing pipeline.
"""
import csv
import io
import json
import logging
import os
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DATASETS_DIR = BASE_DIR / "datasets" / "kaggle"
DB_PATH = BASE_DIR / "datasets" / "civic_data.db"

# Chicago Data Portal — Socrata SODA API (public, no auth, JSON → CSV)
# Format: (name, socrata_dataset_id, description, limit)
CHICAGO_DATASETS = [
    ("chicago_311_requests", "v6vf-nfxy",
     "Chicago 311 Service Requests (2018+)", 10000),
    ("chicago_crimes", "ijzp-q8t2",
     "Chicago Crimes (last year sample)", 10000),
    ("chicago_food_inspections", "4ijn-s7e5",
     "Chicago Food Inspections", 10000),
    ("chicago_business_licenses", "r5kz-chrr",
     "Chicago Business Licenses", 5000),
    ("chicago_public_health", "iqnk-2tcu",
     "Chicago Public Health Statistics by Community Area", 1000),
    ("chicago_budget", "siwz-e9c2",
     "Chicago Budget Recommendations", 5000),
    ("chicago_traffic_crashes", "85ca-t3if",
     "Chicago Traffic Crashes", 10000),
    ("chicago_building_violations", "22u3-xenr",
     "Chicago Building Violations", 5000),
    ("chicago_libraries", "x8fc-8rcq",
     "Chicago Public Library Locations", 200),
    ("chicago_police_stations", "z8bn-74gv",
     "Chicago Police Station Locations", 100),
]


def download_socrata_dataset(name: str, dataset_id: str, desc: str, limit: int):
    """Download a dataset from Chicago's Socrata API as CSV."""
    out_path = DATASETS_DIR / f"{name}.csv"
    if out_path.exists() and out_path.stat().st_size > 1000:
        log.info(f"  [SKIP] {name} already exists ({out_path.stat().st_size:,} bytes)")
        return out_path

    url = f"https://data.cityofchicago.org/resource/{dataset_id}.json?$limit={limit}"
    log.info(f"  Downloading {name} ({desc})...")
    log.info(f"    URL: {url}")

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data:
            log.warning(f"  [EMPTY] {name}: no records returned")
            return None

        # Write as CSV
        DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        fieldnames = list(data[0].keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in data:
                writer.writerow(row)

        log.info(f"  [OK] {name}: {len(data)} rows, {out_path.stat().st_size:,} bytes")
        return out_path

    except Exception as e:
        log.error(f"  [FAIL] {name}: {e}")
        return None


def ingest_csv_to_db(csv_path: Path, name: str, desc: str):
    """Read rows from CSV and insert as chunks into civic_data.db."""
    import hashlib
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Get or create a source_id via the datasets table
    c.execute("SELECT id FROM datasets WHERE name = ?", (name,))
    row = c.fetchone()
    if row:
        source_id = row[0]
    else:
        c.execute(
            "INSERT INTO datasets (source, name, description, url, format, license) VALUES (?,?,?,?,?,?)",
            ("Chicago-API", name, desc, f"https://data.cityofchicago.org", "csv", "CC0")
        )
        source_id = c.lastrowid
        conn.commit()

    # Check if already ingested
    c.execute("SELECT COUNT(*) FROM chunks WHERE source_type = ? AND source_id = ?",
              ("Chicago-API", source_id))
    existing = c.fetchone()[0]
    if existing > 0:
        log.info(f"  [SKIP-DB] {name}: {existing} chunks already in DB")
        conn.close()
        return existing

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Create text chunks from groups of rows (10 rows per chunk)
    chunk_size = 10
    chunks_added = 0
    for i in range(0, len(rows), chunk_size):
        batch = rows[i:i + chunk_size]
        text_parts = []
        for row in batch:
            parts = [f"{k}: {v}" for k, v in row.items() if v and str(v).strip()]
            text_parts.append(" | ".join(parts))
        content = "\n".join(text_parts)

        if len(content.strip()) < 50:
            continue

        text_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        c.execute(
            "INSERT INTO chunks (source_type, source_id, chunk_index, text, text_hash, char_count) VALUES (?,?,?,?,?,?)",
            ("Chicago-API", source_id, i // chunk_size, content, text_hash, len(content))
        )
        chunks_added += 1

    conn.commit()
    conn.close()
    log.info(f"  [DB] {name}: added {chunks_added} chunks from {len(rows)} rows")
    return chunks_added


def main():
    log.info("=" * 60)
    log.info("Jemma SafeBrain — Civic Dataset Downloader")
    log.info("=" * 60)
    log.info(f"Output directory: {DATASETS_DIR}")
    log.info(f"Database: {DB_PATH}")
    log.info("")

    total_files = 0
    total_chunks = 0

    for name, dataset_id, desc, limit in CHICAGO_DATASETS:
        csv_path = download_socrata_dataset(name, dataset_id, desc, limit)
        if csv_path and csv_path.exists():
            total_files += 1
            chunks = ingest_csv_to_db(csv_path, name, desc)
            total_chunks += chunks
        time.sleep(0.5)  # Be polite to the API

    log.info("")
    log.info(f"Done! {total_files} datasets downloaded, {total_chunks} new chunks added to DB")

    # Show DB stats
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM chunks")
    total = c.fetchone()[0]
    c.execute("SELECT source_type, COUNT(*) FROM chunks GROUP BY source_type ORDER BY COUNT(*) DESC")
    groups = c.fetchall()
    conn.close()

    log.info(f"\nTotal chunks in DB: {total}")
    for source_type, count in groups:
        log.info(f"  {source_type}: {count}")


if __name__ == "__main__":
    main()

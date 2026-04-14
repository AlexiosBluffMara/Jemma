"""
Jemma SafeBrain — Civic Data Ingestion Pipeline

Scrapes ALL public data from:
  - Illinois State University (ilstu.edu)
  - Town of Normal, IL (normalil.gov)
  - Town of Normal Open Data Portal (ArcGIS Hub)
  - Data.Illinois.gov (Socrata API)
  - McLean County

Multi-threaded with retry logic, rate limiting, and checkpoint/resume.
Stores everything in a local SQLite database for RAG and training.
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "data_ingestion.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("ingestion")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent.parent / "datasets" / "civic_data.db"
CACHE_DIR = Path(__file__).parent.parent / "cache" / "ingestion"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_WORKERS = 4        # concurrent fetch threads
RETRY_MAX = 3          # retries per request
RETRY_DELAY = 2.0      # seconds between retries (exponential backoff)
REQUEST_TIMEOUT = 30   # seconds
RATE_LIMIT_DELAY = 0.5 # seconds between requests per thread (politeness)
MAX_PAGES_PER_SITE = 500  # safety cap per domain

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ScrapedPage:
    url: str
    domain: str
    title: str
    content: str
    content_type: str           # html, json, csv, pdf
    fetched_at: str
    content_hash: str
    byte_size: int
    status_code: int
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create civic_data.db with full schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            domain TEXT NOT NULL,
            title TEXT,
            content TEXT,
            content_type TEXT,
            fetched_at TEXT,
            content_hash TEXT,
            byte_size INTEGER,
            status_code INTEGER,
            metadata_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain);
        CREATE INDEX IF NOT EXISTS idx_pages_hash ON pages(content_hash);

        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            url TEXT,
            format TEXT,
            license TEXT,
            row_count INTEGER,
            column_names TEXT,
            sample_json TEXT,
            fetched_at TEXT,
            UNIQUE(source, name)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            doc_type TEXT,
            content TEXT,
            url TEXT,
            fetched_at TEXT,
            content_hash TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            name TEXT,
            title_role TEXT,
            department TEXT,
            email TEXT,
            phone TEXT,
            url TEXT,
            fetched_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ingestion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


DB_LOCK = threading.Lock()

def save_page(conn: sqlite3.Connection, page: ScrapedPage):
    """Insert or update a scraped page."""
    with DB_LOCK:
        conn.execute("""
            INSERT OR REPLACE INTO pages
                (url, domain, title, content, content_type, fetched_at,
                 content_hash, byte_size, status_code, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page.url, page.domain, page.title, page.content,
            page.content_type, page.fetched_at, page.content_hash,
            page.byte_size, page.status_code,
            json.dumps(page.metadata, default=str),
        ))
        conn.commit()


def save_dataset(conn, source, name, description, url, fmt, license_str,
                 row_count, column_names, sample_json):
    with DB_LOCK:
        conn.execute("""
            INSERT OR REPLACE INTO datasets
                (source, name, description, url, format, license, row_count,
                 column_names, sample_json, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, name, description, url, fmt, license_str, row_count,
              json.dumps(column_names) if column_names else None,
              sample_json, datetime.utcnow().isoformat()))
        conn.commit()


def save_contact(conn, source, name, title_role, department, email, phone, url):
    with DB_LOCK:
        conn.execute("""
            INSERT OR IGNORE INTO contacts
                (source, name, title_role, department, email, phone, url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, name, title_role, department, email, phone, url,
              datetime.utcnow().isoformat()))
        conn.commit()


def save_document(conn, source, title, doc_type, content, url):
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    with DB_LOCK:
        conn.execute("""
            INSERT OR IGNORE INTO documents
                (source, title, doc_type, content, url, fetched_at, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (source, title, doc_type, content, url,
              datetime.utcnow().isoformat(), content_hash))
        conn.commit()


def log_action(conn, source, action, status, message=""):
    with DB_LOCK:
        conn.execute("""
            INSERT INTO ingestion_log (source, action, status, message)
            VALUES (?, ?, ?, ?)
        """, (source, action, status, message))
        conn.commit()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def fetch_with_retry(url: str, retries: int = RETRY_MAX,
                     timeout: int = REQUEST_TIMEOUT,
                     headers: dict = None) -> Optional[object]:
    """Fetch a URL with exponential backoff retry."""
    import requests
    if headers is None:
        headers = {
            "User-Agent": "JemmaSafeBrain/1.0 (civic-research; +https://github.com/AlexiosBluffMara/Jemma)",
        }
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout, headers=headers,
                                allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:  # rate limited
                wait = RETRY_DELAY * (2 ** attempt) * 3
                log.warning(f"Rate limited on {url}, waiting {wait:.1f}s")
                time.sleep(wait)
            elif resp.status_code >= 500:
                log.warning(f"Server error {resp.status_code} on {url}, retry {attempt+1}/{retries}")
                time.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                log.error(f"HTTP {resp.status_code} on {url}: {e}")
                return None
        except requests.exceptions.ConnectionError:
            log.warning(f"Connection error on {url}, retry {attempt+1}/{retries}")
            time.sleep(RETRY_DELAY * (2 ** attempt))
        except requests.exceptions.Timeout:
            log.warning(f"Timeout on {url}, retry {attempt+1}/{retries}")
            time.sleep(RETRY_DELAY * (2 ** attempt))
        except Exception as e:
            log.error(f"Unexpected error fetching {url}: {e}")
            return None
    log.error(f"All {retries} retries exhausted for {url}")
    return None


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML — no heavy deps."""
    # Strip script/style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Strip tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode entities
    import html as html_mod
    text = html_mod.unescape(text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_title_from_html(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------
# Source: Illinois State University
# ---------------------------------------------------------------------------
ISU_URLS = [
    # Main site + key subpages
    "https://illinoisstate.edu/",
    "https://illinoisstate.edu/about/",
    "https://illinoisstate.edu/academics/",
    "https://illinoisstate.edu/admissions/",
    "https://illinoisstate.edu/campus-life/",
    "https://illinoisstate.edu/research/",
    "https://illinoisstate.edu/about/university-facts/",
    "https://illinoisstate.edu/about/leadership/",
    "https://illinoisstate.edu/about/strategic-plan/",
    # Budget & finance
    "https://provost.illinoisstate.edu/data/",
    "https://budget.illinoisstate.edu/",
    "https://controller.illinoisstate.edu/",
    "https://provost.illinoisstate.edu/data/factbook/",
    # Institutional research & data
    "https://ir.illinoisstate.edu/",
    "https://ir.illinoisstate.edu/data-portal/",
    "https://ir.illinoisstate.edu/data-portal/enrollment/",
    "https://ir.illinoisstate.edu/data-portal/degrees/",
    "https://ir.illinoisstate.edu/data-portal/financial-aid/",
    "https://ir.illinoisstate.edu/data-portal/retention-graduation/",
    "https://ir.illinoisstate.edu/data-portal/faculty-staff/",
    # Public safety
    "https://police.illinoisstate.edu/",
    "https://police.illinoisstate.edu/clery/",
    "https://police.illinoisstate.edu/clery/crime-statistics/",
    "https://ehs.illinoisstate.edu/",
    # Leadership & governance
    "https://president.illinoisstate.edu/",
    "https://bot.illinoisstate.edu/",
    "https://senate.illinoisstate.edu/",
    "https://senate.illinoisstate.edu/budget-overview/",
    # IT & tech
    "https://techzone.illinoisstate.edu/",
    "https://ithelp.illinoisstate.edu/",
    # Community engagement
    "https://news.illinoisstate.edu/",
    "https://stories.illinoisstate.edu/",
    "https://alumni.illinoisstate.edu/",
    # Data downloads / reports
    "https://illinoisstate.edu/downloads/",
    "https://illinoisstate.edu/about/fast-facts/",
]


def scrape_isu(conn: sqlite3.Connection):
    """Scrape Illinois State University public pages."""
    log.info("=== Starting ISU scrape ===")
    log_action(conn, "ISU", "scrape_start", "running")
    count = 0
    for url in ISU_URLS:
        try:
            resp = fetch_with_retry(url)
            if resp is None:
                continue
            content = resp.text
            text = extract_text_from_html(content)
            title = extract_title_from_html(content)
            page = ScrapedPage(
                url=url,
                domain="illinoisstate.edu",
                title=title,
                content=text,
                content_type="html",
                fetched_at=datetime.utcnow().isoformat(),
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                byte_size=len(text.encode()),
                status_code=resp.status_code,
            )
            save_page(conn, page)
            count += 1
            log.info(f"  ISU [{count}] {title[:60]}... ({len(text):,} chars)")
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            log.error(f"ISU error on {url}: {e}")
            traceback.print_exc()
    log_action(conn, "ISU", "scrape_complete", "ok", f"{count} pages")
    log.info(f"=== ISU scrape complete: {count} pages ===")
    return count


# ---------------------------------------------------------------------------
# Source: Town of Normal
# ---------------------------------------------------------------------------
NORMAL_URLS = [
    # Main site
    "https://www.normalil.gov/",
    "https://www.normalil.gov/27/Government",
    "https://www.normalil.gov/97/Contacting-the-Council",
    "https://www.normalil.gov/127/Budget",
    "https://www.normalil.gov/1114/Transparency",
    "https://www.normalil.gov/110/Freedom-of-Information",
    "https://www.normalil.gov/98/Boards-Commissions",
    # Departments
    "https://www.normalil.gov/1881/Police",
    "https://www.normalil.gov/1879/Fire",
    "https://www.normalil.gov/1877/Parks-Recreation",
    "https://www.normalil.gov/1876/Economic-Development",
    "https://www.normalil.gov/1875/Cultural-Arts",
    "https://www.normalil.gov/1653/Parking",
    # Plans & docs
    "https://www.normalil.gov/1883/Town-of-Normal-Approved-Plans",
    "https://www.normalil.gov/DocumentCenter",
    # Staff directory
    "https://www.normalil.gov/Directory.aspx",
]

NORMAL_ARCGIS_DATASETS = [
    # ArcGIS Hub API endpoints for Town of Normal open data
    "https://services1.arcgis.com/EpdhcfGLz7hAjVwD/arcgis/rest/services",
]


def scrape_normal(conn: sqlite3.Connection):
    """Scrape Town of Normal public pages + open data portal."""
    log.info("=== Starting Town of Normal scrape ===")
    log_action(conn, "Normal", "scrape_start", "running")
    count = 0
    for url in NORMAL_URLS:
        try:
            resp = fetch_with_retry(url)
            if resp is None:
                continue
            text = extract_text_from_html(resp.text)
            title = extract_title_from_html(resp.text)
            page = ScrapedPage(
                url=url, domain="normalil.gov", title=title,
                content=text, content_type="html",
                fetched_at=datetime.utcnow().isoformat(),
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
                byte_size=len(text.encode()), status_code=resp.status_code,
            )
            save_page(conn, page)
            count += 1
            log.info(f"  Normal [{count}] {title[:60]}... ({len(text):,} chars)")

            # Extract contact info from directory-like pages
            _extract_contacts(conn, "Normal", url, resp.text)

            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            log.error(f"Normal error on {url}: {e}")

    # Fetch ArcGIS Hub datasets catalog
    count += _scrape_normal_arcgis(conn)

    log_action(conn, "Normal", "scrape_complete", "ok", f"{count} items")
    log.info(f"=== Normal scrape complete: {count} items ===")
    return count


def _scrape_normal_arcgis(conn) -> int:
    """Query Normal's ArcGIS Hub for datasets via hub search API."""
    hub_url = "https://town-of-normal-open-data-tongis.hub.arcgis.com/api/v3/datasets"
    count = 0
    try:
        params = {"page[size]": 100}
        resp = fetch_with_retry(f"{hub_url}?page%5Bsize%5D=100")
        if resp and resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                name = attrs.get("name", "unknown")
                desc = attrs.get("description", "")
                url = attrs.get("url", "")
                save_dataset(
                    conn, source="Normal-ArcGIS", name=name,
                    description=extract_text_from_html(desc) if desc else "",
                    url=url, fmt="arcgis-feature",
                    license_str="Public Government Data", row_count=None,
                    column_names=None, sample_json=None,
                )
                count += 1
                log.info(f"  ArcGIS [{count}] {name}")
    except Exception as e:
        log.error(f"ArcGIS Hub error: {e}")
    return count


# ---------------------------------------------------------------------------
# Source: Data.Illinois.gov (Socrata API)
# ---------------------------------------------------------------------------
SOCRATA_DOMAIN = "data.illinois.gov"
SOCRATA_SEARCH = f"https://{SOCRATA_DOMAIN}/api/catalog/v1"
# Categories relevant to our civic scope
SOCRATA_CATEGORIES = [
    "Public Safety",
    "Education",
    "Health and Human Services",
    "Government and Public Employees",
    "Business and Workforce",
    "Local Government",
]


def scrape_illinois_data(conn: sqlite3.Connection):
    """Fetch dataset catalog from Data.Illinois.gov via Socrata."""
    log.info("=== Starting Data.Illinois.gov scrape ===")
    log_action(conn, "DataIllinois", "scrape_start", "running")
    total = 0
    for category in SOCRATA_CATEGORIES:
        try:
            params = {
                "categories": category,
                "limit": 50,
                "offset": 0,
                "order": "relevance",
                "domains": SOCRATA_DOMAIN,
            }
            url = f"{SOCRATA_SEARCH}?categories={category}&limit=50&domains={SOCRATA_DOMAIN}"
            resp = fetch_with_retry(url)
            if resp is None:
                continue
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                resource = item.get("resource", {})
                name = resource.get("name", "unknown")
                desc = resource.get("description", "")
                link = item.get("link", "")
                cols = resource.get("columns_field_name", [])
                save_dataset(
                    conn, source="DataIllinois", name=name,
                    description=desc, url=f"https://{SOCRATA_DOMAIN}{link}",
                    fmt="socrata", license_str="Public Domain (State of IL)",
                    row_count=resource.get("page_views", {}).get("page_views_total"),
                    column_names=cols, sample_json=None,
                )
                total += 1
            log.info(f"  DataIL [{category}] {len(results)} datasets")
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            log.error(f"DataIllinois error for {category}: {e}")
    log_action(conn, "DataIllinois", "scrape_complete", "ok", f"{total} datasets")
    log.info(f"=== DataIllinois scrape complete: {total} datasets ===")
    return total


# ---------------------------------------------------------------------------
# Source: Chicago Data Portal (via Socrata)
# ---------------------------------------------------------------------------
CHICAGO_DOMAIN = "data.cityofchicago.org"
CHICAGO_KEY_DATASETS = [
    # Direct Socrata dataset IDs for our priority datasets
    ("crimes", "ijzp-q8t2", "Chicago Crimes 2001-Present"),
    ("311", "v6vf-nfxy", "Chicago 311 Service Requests"),
    ("business-licenses", "r5kz-chrr", "Chicago Business Licenses"),
    ("food-inspections", "4ijn-s7e5", "Chicago Food Inspections"),
    ("traffic-crashes", "85ca-t3if", "Chicago Traffic Crashes"),
    ("budget", "fg7s-tv84", "Chicago Budget Ordinance"),
]


def scrape_chicago_portal(conn: sqlite3.Connection):
    """Fetch Chicago Data Portal datasets via Socrata API."""
    log.info("=== Starting Chicago Data Portal scrape ===")
    log_action(conn, "Chicago", "scrape_start", "running")
    count = 0
    for tag, dataset_id, label in CHICAGO_KEY_DATASETS:
        try:
            # Fetch metadata
            meta_url = f"https://{CHICAGO_DOMAIN}/api/views/{dataset_id}.json"
            resp = fetch_with_retry(meta_url)
            if resp is None:
                continue
            meta = resp.json()
            name = meta.get("name", label)
            desc = meta.get("description", "")
            cols = [c["fieldName"] for c in meta.get("columns", [])]
            row_count = meta.get("rowsUpdatedAt")

            # Fetch small sample (50 rows) for RAG seeding
            sample_url = f"https://{CHICAGO_DOMAIN}/resource/{dataset_id}.json?$limit=50"
            sample_resp = fetch_with_retry(sample_url)
            sample_json = sample_resp.text if sample_resp else None

            save_dataset(
                conn, source="Chicago", name=name, description=desc,
                url=f"https://{CHICAGO_DOMAIN}/d/{dataset_id}",
                fmt="socrata-json", license_str="CC0",
                row_count=row_count, column_names=cols,
                sample_json=sample_json,
            )
            count += 1
            log.info(f"  Chicago [{count}] {name} ({len(cols)} cols)")
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            log.error(f"Chicago error for {label}: {e}")
    log_action(conn, "Chicago", "scrape_complete", "ok", f"{count} datasets")
    log.info(f"=== Chicago scrape complete: {count} datasets ===")
    return count


# ---------------------------------------------------------------------------
# Contact extraction helper
# ---------------------------------------------------------------------------
def _extract_contacts(conn, source, url, html):
    """Extract email/phone from page HTML."""
    # Emails
    emails = set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', html))
    for email in emails:
        # Filter out image/asset emails
        if any(x in email for x in ['.png', '.jpg', '.gif', '.css', '.js']):
            continue
        save_contact(conn, source=source, name=None,
                     title_role=None, department=None,
                     email=email, phone=None, url=url)

    # Phone numbers (US format)
    phones = set(re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', html))
    for phone in phones:
        save_contact(conn, source=source, name=None,
                     title_role=None, department=None,
                     email=None, phone=phone, url=url)


# ---------------------------------------------------------------------------
# Kaggle dataset downloader
# ---------------------------------------------------------------------------
KAGGLE_DATASETS = [
    "currie32/crimes-in-chicago",
    "chicago/chicago-311-service-requests",
    "chicago/chicago-business-licenses-and-owners",
    "chicago/chicago-food-inspections",
    "isadoraamorim/trafficcrasheschicago",
    "chicago/chicago-budget-ordinance-and-recommendations",
    "zhaodianwen/chicago-data-portal",
    "chicago/chicago-public-health-statistics",
    "larsen0966/sba-loans-case-data-set",
    "sumithbhongale/american-university-data-ipeds-dataset",
]


def download_kaggle_datasets(conn: sqlite3.Connection):
    """Register Kaggle datasets in our catalog (download via kaggle CLI)."""
    log.info("=== Registering Kaggle datasets ===")
    log_action(conn, "Kaggle", "catalog_start", "running")
    count = 0
    for ds in KAGGLE_DATASETS:
        save_dataset(
            conn, source="Kaggle", name=ds,
            description=f"Kaggle dataset: {ds}",
            url=f"https://www.kaggle.com/datasets/{ds}",
            fmt="kaggle-csv", license_str="CC0/Public Domain",
            row_count=None, column_names=None, sample_json=None,
        )
        count += 1
        log.info(f"  Kaggle [{count}] {ds}")

    # Try actual kaggle CLI download for small datasets
    try:
        import subprocess
        dl_dir = Path(__file__).parent.parent / "datasets" / "kaggle"
        dl_dir.mkdir(parents=True, exist_ok=True)
        for ds in KAGGLE_DATASETS[:3]:  # Download first 3 (smaller ones)
            try:
                result = subprocess.run(
                    ["kaggle", "datasets", "download", "-d", ds,
                     "-p", str(dl_dir), "--unzip"],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    log.info(f"  Downloaded {ds}")
                else:
                    log.warning(f"  Kaggle CLI failed for {ds}: {result.stderr[:200]}")
            except FileNotFoundError:
                log.info("  kaggle CLI not found — registering metadata only")
                break
            except subprocess.TimeoutExpired:
                log.warning(f"  Kaggle download timeout for {ds}")
    except Exception as e:
        log.warning(f"  Kaggle download attempt: {e}")

    log_action(conn, "Kaggle", "catalog_complete", "ok", f"{count} datasets")
    log.info(f"=== Kaggle registration complete: {count} datasets ===")
    return count


# ---------------------------------------------------------------------------
# HuggingFace benchmark datasets (register for eval pipeline)
# ---------------------------------------------------------------------------
HF_EVAL_DATASETS = [
    ("cais/mmlu", "MIT", 14042, "Knowledge evaluation"),
    ("allenai/ai2_arc", "CC-BY-SA 4.0", 7787, "Reasoning"),
    ("Rowan/hellaswag", "MIT", 10042, "Commonsense"),
    ("allenai/winogrande", "Apache 2.0", 1267, "Coreference"),
    ("openai/gsm8k", "MIT", 1319, "Math reasoning"),
    ("openai/openai_humaneval", "MIT", 164, "Code generation"),
    ("EleutherAI/truthful_qa_mc", "Apache 2.0", 817, "Truthfulness"),
    ("toxigen/toxigen-data", "MIT", 6541, "Toxicity"),
    ("allenai/real-toxicity-prompts", "Apache 2.0", 100000, "Toxicity prompts"),
    ("heegyu/bbq", "CC-BY 4.0", 58492, "Bias evaluation"),
    ("nyu-mll/crows_pairs", "CC-SA 4.0", 1508, "Stereotype bias"),
]


def register_hf_datasets(conn: sqlite3.Connection):
    """Register HuggingFace eval datasets in catalog."""
    log.info("=== Registering HuggingFace evaluation datasets ===")
    count = 0
    for name, license_str, rows, desc in HF_EVAL_DATASETS:
        save_dataset(
            conn, source="HuggingFace", name=name, description=desc,
            url=f"https://huggingface.co/datasets/{name}",
            fmt="huggingface", license_str=license_str,
            row_count=rows, column_names=None, sample_json=None,
        )
        count += 1
    log.info(f"=== HuggingFace registration: {count} datasets ===")
    return count


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------
def run_full_ingestion():
    """Run the complete data ingestion pipeline."""
    start = time.time()
    log.info("=" * 70)
    log.info("JEMMA SAFEBRAIN — CIVIC DATA INGESTION PIPELINE")
    log.info("=" * 70)
    log.info(f"Database: {DB_PATH}")
    log.info(f"Workers: {MAX_WORKERS}")
    log.info(f"Retry: {RETRY_MAX}x with {RETRY_DELAY}s backoff")
    log.info("")

    conn = init_db()
    log_action(conn, "Pipeline", "full_ingestion_start", "running")

    results = {}

    # Run sources in parallel threads
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(scrape_isu, conn): "ISU",
            pool.submit(scrape_normal, conn): "Normal",
            pool.submit(scrape_illinois_data, conn): "DataIllinois",
            pool.submit(scrape_chicago_portal, conn): "Chicago",
            pool.submit(download_kaggle_datasets, conn): "Kaggle",
            pool.submit(register_hf_datasets, conn): "HuggingFace",
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                count = future.result()
                results[source] = count
                log.info(f"✓ {source}: {count} items")
            except Exception as e:
                results[source] = f"ERROR: {e}"
                log.error(f"✗ {source}: {e}")
                traceback.print_exc()

    elapsed = time.time() - start

    # Summary
    log.info("")
    log.info("=" * 70)
    log.info("INGESTION SUMMARY")
    log.info("=" * 70)
    for source, count in sorted(results.items()):
        log.info(f"  {source:20s}: {count}")

    # DB stats
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM pages")
    n_pages = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM datasets")
    n_datasets = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contacts")
    n_contacts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM documents")
    n_docs = cursor.fetchone()[0]

    log.info(f"\n  Total pages:    {n_pages}")
    log.info(f"  Total datasets: {n_datasets}")
    log.info(f"  Total contacts: {n_contacts}")
    log.info(f"  Total documents:{n_docs}")
    log.info(f"  Elapsed:        {elapsed:.1f}s")
    log.info(f"  Database size:  {DB_PATH.stat().st_size / 1024:.1f} KB")

    log_action(conn, "Pipeline", "full_ingestion_complete", "ok",
               f"{n_pages} pages, {n_datasets} datasets, {elapsed:.0f}s")
    conn.close()
    return results


if __name__ == "__main__":
    run_full_ingestion()

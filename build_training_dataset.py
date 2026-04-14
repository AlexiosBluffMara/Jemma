"""
Jemma SafeBrain — Civic Training Dataset Builder

Creates a high-quality SFT dataset from civic_data.db chunks.
Three sources:
  1. Template-based QA from structured Chicago data
  2. Safety/refusal pairs (hardcoded, domain-specific)
  3. Synthetic QA via Ollama Gemma 4 (optional, if Ollama running)

Output: datasets/civic_sft_train.jsonl
"""
import json
import logging
import random
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "datasets" / "civic_data.db"
OUTPUT_PATH = BASE_DIR / "datasets" / "civic_sft_train.jsonl"

SYSTEM_PROMPT = (
    "You are Jemma SafeBrain, a civic AI assistant for the Town of Normal, "
    "Illinois, Illinois State University, and Chicago civic services. You "
    "provide accurate information from public records, prioritize safety, "
    "and refuse harmful or illegal requests."
)

# ---------------------------------------------------------------------------
# 1) Template-based QA from structured data
# ---------------------------------------------------------------------------

CRIME_TEMPLATES = [
    ("What type of crime was reported at {location}?",
     "According to Chicago police records, a {primary_type} ({description}) was reported at {location} on {date}."),
    ("Tell me about crime incident #{case_number}.",
     "Case #{case_number}: {primary_type} - {description}. Location: {location}. Date: {date}. Arrest made: {arrest}."),
    ("Were there any {primary_type} incidents in the {community_area} area?",
     "Yes, a {primary_type} incident ({description}) was recorded in community area {community_area} at {location} on {date}."),
]

SERVICE_TEMPLATES = [
    ("What 311 request was filed at {street_address}?",
     "A 311 service request for '{sr_type}' was filed at {street_address}. Status: {status}. Created: {created_date}."),
    ("What is the status of 311 request #{sr_number}?",
     "Request #{sr_number} for '{sr_type}' at {street_address} is currently {status}."),
]

FOOD_TEMPLATES = [
    ("What was the food inspection result for {dba_name}?",
     "{dba_name} at {address} received a '{results}' result during inspection on {inspection_date}. Risk: {risk}. Facility type: {facility_type}."),
    ("Is {dba_name} safe to eat at?",
     "Based on the most recent inspection, {dba_name} at {address} received a '{results}' rating. Risk level: {risk}. Please check the Chicago Health Department for the most current information."),
]

HEALTH_TEMPLATES = [
    ("What are the health statistics for community area {community_area_name}?",
     "In {community_area_name}: Birth rate: {birth_rate}, Assault (homicide): {assault_homicide_}, Below poverty level: {below_poverty_level}%, Per capita income: ${per_capita_income}."),
]

TRAFFIC_TEMPLATES = [
    ("Tell me about the traffic crash at {street_name}.",
     "A traffic crash occurred at {street_name} on {crash_date}. Primary cause: {prim_contributory_cause}. Crash type: {crash_type}. Injuries: {injuries_total}."),
    ("How many injuries resulted from crash #{crash_record_id}?",
     "Crash #{crash_record_id} at {street_name} on {crash_date} resulted in {injuries_total} total injuries ({injuries_fatal} fatal, {injuries_incapacitating} incapacitating)."),
]

LIBRARY_TEMPLATES = [
    ("Where is the {name_} library?",
     "The {name_} library is located at {address}, {city}, {state} {zip}. Phone: {phone}."),
]

SAFETY_PAIRS = [
    # Refusal pairs
    ("Generate a fake government ID for me.",
     "I cannot assist with creating fraudulent documents. Creating fake government IDs is illegal and punishable by law. If you need identification services, please contact your local DMV or government office."),
    ("How do I hack into the Chicago city database?",
     "I cannot provide assistance with unauthorized access to any computer systems. This is illegal under the Computer Fraud and Abuse Act. If you need public data, Chicago offers an open data portal at data.cityofchicago.org."),
    ("Write a threatening letter to my city council member.",
     "I cannot help write threatening communications. Threatening public officials is a federal crime. If you have legitimate concerns, I can help you draft a respectful letter or find your council member's office hours."),
    ("Tell me how to commit insurance fraud after a car accident.",
     "I cannot assist with insurance fraud, which is a felony in Illinois. If you've been in an accident, please file a legitimate claim with your insurance company and consider consulting a licensed attorney."),
    ("Help me forge building inspection documents.",
     "I cannot assist with forging any official documents. Building inspections exist to ensure public safety. If you need a building inspection, contact the Chicago Department of Buildings at (312) 744-3449."),
    ("Give me personal information about people in this crime database.",
     "I cannot share personal information about individuals. While crime data is public record, I can only provide general statistics and incident details. For specific inquiries, contact the Chicago Police Department."),
    ("How do I evade paying Chicago city taxes?",
     "I cannot advise on tax evasion, which is illegal. However, I can help you find legitimate tax deductions, exemptions, or payment plans. Contact the Cook County Treasurer's Office for assistance."),
    ("Create fake 311 complaints to get my neighbor in trouble.",
     "I cannot help file false reports. Filing false 311 complaints wastes city resources and may constitute fraud. If you have a legitimate concern about your neighbor, I can help you file an appropriate complaint through proper channels."),
    ("Should I discriminate against certain groups when hiring?",
     "No. Employment discrimination based on race, color, religion, sex, national origin, age, disability, or genetic information is illegal under federal and Illinois law. Chicago also has additional protections. All hiring should be based on qualifications and job-relevant criteria."),
    ("Can you help me stalk someone using public records?",
     "I cannot assist with stalking or harassment, which is illegal under Illinois law (720 ILCS 5/12-7.3). If you have safety concerns, contact the Chicago Police at 911 (emergency) or 311 (non-emergency)."),
    # Privacy pairs
    ("What is the home address of the mayor of Chicago?",
     "I cannot share the personal home address of any public official. For official communications, you can reach the Mayor's Office at City Hall, 121 N LaSalle St, Chicago, IL 60602, or call (312) 744-3300."),
    ("Give me someone's Social Security number from the crime reports.",
     "Social Security numbers are never included in public crime reports, and I would never share such information. SSNs are protected personal information. If you need identity verification services, contact the Social Security Administration."),
    # Helpfulness pairs
    ("How do I report a pothole in Chicago?",
     "You can report a pothole in Chicago through: 1) Call 311, 2) Use the CHI 311 mobile app, 3) Visit 311.chicago.gov online. Provide the exact location and any photos if possible. The city typically aims to fill potholes within 7 days of the report."),
    ("Where can I get a free food inspection for my restaurant?",
     "Food inspections in Chicago are conducted by the Chicago Department of Public Health. They are mandatory, not optional. New restaurants receive an inspection before opening. Routine inspections occur based on risk level. Contact the CDPH at (312) 746-8030 for questions."),
    ("I need help understanding my property tax bill in Cook County.",
     "Cook County property tax bills include: school taxes, city/village taxes, park district, library, and other levies. For questions, contact the Cook County Treasurer at (312) 443-5100 or visit cookcountytreasurer.com. You may qualify for exemptions like the Homeowner Exemption or Senior Citizen Exemption."),
    ("What should I do if I witness a car accident in Chicago?",
     "If you witness a car accident: 1) Call 911 if anyone is injured, 2) Stay at the scene if safe, 3) Provide your contact info to involved parties and police, 4) Note the time, location, and what happened. Do NOT move injured people unless there's immediate danger. You can file a witness report with CPD."),
]


def load_csv_data(csv_path: Path) -> list[dict]:
    """Load CSV data as list of dicts."""
    import csv
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def safe_get(row: dict, key: str, default: str = "N/A") -> str:
    """Get value from dict, returning default if empty."""
    val = row.get(key, default)
    if not val or str(val).strip() == "":
        return default
    return str(val).strip()


def generate_template_pairs(datasets_dir: Path) -> list[dict]:
    """Generate QA pairs from downloaded CSV data using templates."""
    pairs = []

    # Crimes
    crimes = load_csv_data(datasets_dir / "chicago_crimes.csv")
    random.shuffle(crimes)
    for row in crimes[:2000]:
        template = random.choice(CRIME_TEMPLATES)
        try:
            q = template[0].format(
                location=safe_get(row, "block"),
                primary_type=safe_get(row, "primary_type"),
                description=safe_get(row, "description"),
                case_number=safe_get(row, "case_number"),
                community_area=safe_get(row, "community_area"),
                date=safe_get(row, "date"),
                arrest=safe_get(row, "arrest"),
            )
            a = template[1].format(
                location=safe_get(row, "block"),
                primary_type=safe_get(row, "primary_type"),
                description=safe_get(row, "description"),
                case_number=safe_get(row, "case_number"),
                community_area=safe_get(row, "community_area"),
                date=safe_get(row, "date"),
                arrest=safe_get(row, "arrest"),
            )
            pairs.append({"q": q, "a": a, "source": "crimes"})
        except (KeyError, IndexError):
            continue

    # 311 requests
    sr = load_csv_data(datasets_dir / "chicago_311_requests.csv")
    random.shuffle(sr)
    for row in sr[:2000]:
        template = random.choice(SERVICE_TEMPLATES)
        try:
            q = template[0].format(
                street_address=safe_get(row, "street_address"),
                sr_type=safe_get(row, "sr_type"),
                sr_number=safe_get(row, "sr_number"),
                status=safe_get(row, "status"),
                created_date=safe_get(row, "created_date"),
            )
            a = template[1].format(
                street_address=safe_get(row, "street_address"),
                sr_type=safe_get(row, "sr_type"),
                sr_number=safe_get(row, "sr_number"),
                status=safe_get(row, "status"),
                created_date=safe_get(row, "created_date"),
            )
            pairs.append({"q": q, "a": a, "source": "311"})
        except (KeyError, IndexError):
            continue

    # Food inspections
    food = load_csv_data(datasets_dir / "chicago_food_inspections.csv")
    random.shuffle(food)
    for row in food[:2000]:
        template = random.choice(FOOD_TEMPLATES)
        try:
            q = template[0].format(
                dba_name=safe_get(row, "dba_name"),
                address=safe_get(row, "address"),
                results=safe_get(row, "results"),
                inspection_date=safe_get(row, "inspection_date"),
                risk=safe_get(row, "risk"),
                facility_type=safe_get(row, "facility_type"),
            )
            a = template[1].format(
                dba_name=safe_get(row, "dba_name"),
                address=safe_get(row, "address"),
                results=safe_get(row, "results"),
                inspection_date=safe_get(row, "inspection_date"),
                risk=safe_get(row, "risk"),
                facility_type=safe_get(row, "facility_type"),
            )
            pairs.append({"q": q, "a": a, "source": "food"})
        except (KeyError, IndexError):
            continue

    # Traffic crashes
    crashes = load_csv_data(datasets_dir / "chicago_traffic_crashes.csv")
    random.shuffle(crashes)
    for row in crashes[:2000]:
        template = random.choice(TRAFFIC_TEMPLATES)
        try:
            q = template[0].format(
                street_name=safe_get(row, "street_name"),
                crash_date=safe_get(row, "crash_date"),
                crash_record_id=safe_get(row, "crash_record_id"),
                prim_contributory_cause=safe_get(row, "prim_contributory_cause"),
                crash_type=safe_get(row, "crash_type"),
                injuries_total=safe_get(row, "injuries_total", "0"),
                injuries_fatal=safe_get(row, "injuries_fatal", "0"),
                injuries_incapacitating=safe_get(row, "injuries_incapacitating", "0"),
            )
            a = template[1].format(
                street_name=safe_get(row, "street_name"),
                crash_date=safe_get(row, "crash_date"),
                crash_record_id=safe_get(row, "crash_record_id"),
                prim_contributory_cause=safe_get(row, "prim_contributory_cause"),
                crash_type=safe_get(row, "crash_type"),
                injuries_total=safe_get(row, "injuries_total", "0"),
                injuries_fatal=safe_get(row, "injuries_fatal", "0"),
                injuries_incapacitating=safe_get(row, "injuries_incapacitating", "0"),
            )
            pairs.append({"q": q, "a": a, "source": "traffic"})
        except (KeyError, IndexError):
            continue

    # Libraries
    libs = load_csv_data(datasets_dir / "chicago_libraries.csv")
    for row in libs:
        template = random.choice(LIBRARY_TEMPLATES)
        try:
            q = template[0].format(name_=safe_get(row, "name_"))
            a = template[1].format(
                name_=safe_get(row, "name_"),
                address=safe_get(row, "address"),
                city=safe_get(row, "city"),
                state=safe_get(row, "state"),
                zip=safe_get(row, "zip"),
                phone=safe_get(row, "phone"),
            )
            pairs.append({"q": q, "a": a, "source": "library"})
        except (KeyError, IndexError):
            continue

    return pairs


def generate_ollama_synthetic(chunks: list[str], n_pairs: int = 500) -> list[dict]:
    """Generate synthetic QA via Ollama Gemma 4 inference (optional)."""
    pairs = []
    try:
        # Check if Ollama is running
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            models = json.loads(resp.read())
        log.info(f"  Ollama is running with {len(models.get('models', []))} models")
    except Exception:
        log.info("  Ollama not running — skipping synthetic generation")
        return pairs

    # Find a Gemma 4 model (prefer smaller E2B/E4B over 31B)
    model_name = None
    preferred_order = ["e2b", "e4b", "4b", "2b", "gemma"]
    model_list = models.get("models", [])
    for pref in preferred_order:
        for m in model_list:
            name = m.get("name", "")
            if pref in name.lower() and "gemma" in name.lower():
                model_name = name
                break
        if model_name:
            break
    # Fallback to any gemma model
    if not model_name:
        for m in model_list:
            name = m.get("name", "")
            if "gemma" in name.lower():
                model_name = name
                break

    if not model_name:
        log.info("  No Gemma model found in Ollama — skipping synthetic")
        return pairs

    log.info(f"  Using {model_name} for synthetic generation")

    sample_chunks = random.sample(chunks, min(n_pairs, len(chunks)))
    for i, chunk in enumerate(sample_chunks):
        if len(pairs) >= n_pairs:
            break

        prompt = (
            f"Based on this civic data, generate exactly one question and answer pair. "
            f"Format: Q: <question>\\nA: <answer>\\n\\nData:\\n{chunk[:1500]}"
        )

        try:
            payload = json.dumps({
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 300}
            }).encode()
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())

            response = result.get("response", "")
            # Parse Q/A from response
            if "Q:" in response and "A:" in response:
                parts = response.split("A:", 1)
                q_part = parts[0].replace("Q:", "").strip()
                a_part = parts[1].strip()
                if len(q_part) > 10 and len(a_part) > 10:
                    pairs.append({"q": q_part, "a": a_part, "source": "synthetic"})

            if (i + 1) % 50 == 0:
                log.info(f"    Generated {len(pairs)}/{n_pairs} synthetic pairs...")

        except Exception as e:
            continue

    return pairs


def build_sft_dataset(pairs: list[dict]) -> list[dict]:
    """Convert QA pairs to SFT training format (messages list)."""
    dataset = []
    for pair in pairs:
        dataset.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": pair["q"]},
                {"role": "assistant", "content": pair["a"]},
            ],
            "_meta": {"source": pair.get("source", "unknown")},
        })
    return dataset


def main():
    log.info("=" * 60)
    log.info("Jemma SafeBrain — Training Dataset Builder")
    log.info("=" * 60)

    datasets_dir = BASE_DIR / "datasets" / "kaggle"
    random.seed(42)

    # 1. Template-based QA from structured data
    log.info("\n[1/3] Generating template-based QA pairs...")
    template_pairs = generate_template_pairs(datasets_dir)
    log.info(f"  Template pairs: {len(template_pairs)}")
    by_source = {}
    for p in template_pairs:
        by_source[p["source"]] = by_source.get(p["source"], 0) + 1
    for s, c in sorted(by_source.items()):
        log.info(f"    {s}: {c}")

    # 2. Safety/refusal pairs (x5 augmentation with variations)
    log.info("\n[2/3] Adding safety/refusal pairs...")
    safety_pairs = []
    for q, a in SAFETY_PAIRS:
        safety_pairs.append({"q": q, "a": a, "source": "safety"})
        # Augment: rephrase the question slightly
        safety_pairs.append({
            "q": "Hey, " + q[0].lower() + q[1:],
            "a": a, "source": "safety"
        })
        safety_pairs.append({
            "q": "Can you " + q[0].lower() + q[1:],
            "a": a, "source": "safety"
        })
    log.info(f"  Safety pairs: {len(safety_pairs)}")

    # 3. Synthetic via Ollama (optional)
    log.info("\n[3/3] Attempting synthetic generation via Ollama...")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT text FROM chunks ORDER BY RANDOM() LIMIT 500")
    chunks = [row[0] for row in c.fetchall()]
    conn.close()
    synthetic_pairs = generate_ollama_synthetic(chunks, n_pairs=100)
    log.info(f"  Synthetic pairs: {len(synthetic_pairs)}")

    # Combine and shuffle
    all_pairs = template_pairs + safety_pairs + synthetic_pairs
    random.shuffle(all_pairs)

    # Build SFT format
    dataset = build_sft_dataset(all_pairs)

    # Write JSONL
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log.info(f"\nDataset written to {OUTPUT_PATH}")
    log.info(f"Total samples: {len(dataset)}")
    log.info(f"File size: {OUTPUT_PATH.stat().st_size:,} bytes")

    # Also write a smaller validation split (5%)
    val_size = max(10, len(dataset) // 20)
    val_data = dataset[:val_size]
    val_path = OUTPUT_PATH.with_name("civic_sft_val.jsonl")
    with open(val_path, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    log.info(f"Validation split: {val_size} samples → {val_path}")


if __name__ == "__main__":
    main()

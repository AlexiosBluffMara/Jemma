#!/usr/bin/env python3
"""
Jemma Dataset Expansion — Cost-effective synthetic data generation.

Uses Ollama (Gemma 4 E4B local, free) or configurable API endpoints to
generate new training examples, appending to existing JSONL files.

Supports all 9 existing synth streams + 4 new civic/safety streams:
  - civic_normal_il: Town of Normal council, zoning, public works
  - civic_isu_campus: ISU enrollment, departments, events, facilities
  - safety_refusals: Adversarial prompts the model should refuse
  - emergency_central_il: Tornado, flood, ice storm response

Usage:
  python pipeline/expand_dataset.py --streams all --count 50
  python pipeline/expand_dataset.py --streams civic_normal_il,safety_refusals --count 100
  python pipeline/expand_dataset.py --model gemma4:e4b-it-bf16 --count 200
  python pipeline/expand_dataset.py --dry-run  # preview prompts without generating
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SYNTH_DIR = ROOT / "datasets" / "synth"
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"

for d in [SYNTH_DIR, STATE_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log = logging.getLogger("expand_dataset")
log.setLevel(logging.DEBUG)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_fh = logging.FileHandler(LOGS_DIR / "expand_dataset.log", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_fh)
log.addHandler(_sh)

# ---------------------------------------------------------------------------
# Ollama API
# ---------------------------------------------------------------------------
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = "gemma4:e4b-it-bf16"


def ollama_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system: str = "",
    temperature: float = 0.8,
    max_tokens: int = 2048,
    timeout: float = 300.0,
) -> tuple[str, dict]:
    """Call Ollama chat API. Returns (response_text, metadata)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "top_p": 0.95,
            "top_k": 64,
        },
    }

    t0 = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        resp.raise_for_status()
    elapsed = time.perf_counter() - t0

    data = resp.json()
    text = data.get("message", {}).get("content", "")
    meta = {
        "model": data.get("model", model),
        "total_duration_ns": data.get("total_duration", 0),
        "eval_count": data.get("eval_count", 0),
        "latency_s": round(elapsed, 2),
    }
    if meta["eval_count"] > 0 and elapsed > 0:
        meta["tok_per_s"] = round(meta["eval_count"] / elapsed, 1)
    return text.strip(), meta


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------
def load_existing_hashes(filepath: Path) -> set[str]:
    """Load content hashes from an existing JSONL to avoid duplicates."""
    hashes: set[str] = set()
    if not filepath.exists():
        return hashes
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            h = hashlib.md5(line.encode("utf-8")).hexdigest()[:16]
            hashes.add(h)
    return hashes


def content_hash(obj: dict) -> str:
    """Hash a JSON object for dedup."""
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Stream definitions — prompts and parsers for each data stream
# ---------------------------------------------------------------------------

# Topics for each stream, randomly sampled per generation
STREAM_TOPICS: dict[str, list[str]] = {
    "construction_qa": [
        "Post-tensioned slab cracking in a new high-rise near Willis Tower",
        "Seismic joint detailing for a new hospital in southern Illinois",
        "Crack monitoring on the Michigan Avenue Bridge approach spans",
        "Cold weather concreting challenges during Illinois January pour",
        "OSHA scaffold safety inspection on a Chicago Loop construction site",
        "Fire damage assessment of reinforced concrete in an industrial fire",
        "Corrosion-induced spalling on CTA Blue Line elevated station piers",
        "Mass concrete thermal cracking in a Chicago infrastructure pour",
        "Fatigue crack assessment on I-55 bridge deck near Normal IL",
        "Punching shear evaluation of an aging slab in Bloomington warehouse",
        "Deep tunnel shotcrete lining inspection in Chicago clay strata",
        "ASR reaction in concrete pavements on I-74 near Peoria",
        "Temporary shoring design for a Loop high-rise renovation",
        "Concrete pump line blockage on a River North supertall project",
        "Steel connection inspection for a Champaign-Urbana parking garage",
    ],
    "building_codes": [
        "Chicago Building Code Title 14B amendments for high-rise fire rating",
        "ACI 318-19 seismic detailing for special moment frames in Illinois",
        "Illinois energy code compliance for commercial building envelope",
        "Chicago below-grade waterproofing requirements per municipal code",
        "Illinois workers compensation construction class codes",
        "Fireproofing inspection requirements for structural steel in Chicago",
        "Code requirements for historic building renovation in Chicago Landmark zone",
        "ISU campus building code — state-owned building code applicability",
        "IEBC change-of-occupancy requirements for Bloomington warehouse conversion",
        "Chicago Title 14B sprinkler requirements for mixed-use podium buildings",
        "Normal IL zoning ordinance for commercial-to-residential conversion",
        "ADA accessibility requirements for ISU campus facility upgrades",
        "Chicago plumbing code grease interceptor requirements for restaurants",
        "Illinois fire code requirements for university dormitory buildings",
        "Wind load design requirements for Chicago skyline high-rises",
    ],
    "safety_inspections": [
        "Bridge rehabilitation on I-74 over Illinois River — traffic safety",
        "Concrete demolition on a brownfield site in East St Louis IL",
        "Temporary electrical installation inspection on an Illinois hospital project",
        "Roofing replacement on a Chicago public school — hot work safety",
        "Confined space entry inspection for a Normal IL water treatment plant",
        "Fall protection audit on a Chicago residential high-rise project",
        "Crane operation safety inspection on a Loop supertall site",
        "Excavation and trenching inspection near ISU campus utility work",
        "Lead paint abatement inspection on a Bloomington elementary school",
        "Silica exposure control plan review for a highway concrete project",
    ],
    "disaster_assessment": [
        "Building collapse after gas explosion in a Chicago residential neighborhood",
        "Ice storm damage to a steel-frame commercial building in central Illinois",
        "Tornado damage assessment for a Normal IL strip mall",
        "Flood damage structural assessment in the Chicago river corridor",
        "Earthquake damage evaluation for a Carbondale Illinois hospital",
        "Fire damage assessment of ISU Watterson Towers exterior walls",
        "Hail storm damage to roofing systems in McLean County IL",
        "Wind damage to a Bloomington IL manufacturing facility",
        "Chemical spill structural contamination at an East St Louis site",
        "Lightning strike damage to a Chicago north shore high-rise",
    ],
    "blueprint_interpretation": [
        "Reading roof framing plan with steel joist and deck specifications",
        "Interpreting foundation plan with spread footings and grade beams",
        "Electrical panel schedule interpretation for a Chicago commercial fit-out",
        "Structural steel connection details for a Champaign parking structure",
        "Reading a mechanical floor plan with HVAC duct routing and sizing",
        "Fire protection sprinkler layout plan for a high-rise residential tower",
        "Plumbing riser diagram for a multi-story Normal IL apartment building",
        "Site grading plan interpretation for ISU campus construction project",
        "Interpreting reinforcement detailing on a shear wall elevation drawing",
        "Reading curtain wall shop drawings for a Chicago Loop office building",
    ],
    "materials_database": [
        "ASTM A615 Grade 60 reinforcing steel properties for Illinois construction",
        "High-strength concrete mix design (10000+ psi) for Chicago supertall projects",
        "Self-consolidating concrete (SCC) specifications for congested reinforcement",
        "Structural steel grade selection for seismic applications in Illinois",
        "Fiber-reinforced polymer (FRP) rebar for corrosion-prone Chicago structures",
        "Spray-applied fire-resistive material (SFRM) thickness requirements per UL",
        "Illinois aggregate quality standards for PCC pavement construction",
        "Waterproofing membrane selection for Chicago below-grade construction",
        "Epoxy-coated reinforcement vs galvanized rebar for bridge decks",
        "Geosynthetic material specifications for Illinois subgrade stabilization",
    ],
    "object_detection_labels": [
        "Crack classification in post-tensioned concrete slabs",
        "Spalling and delamination detection on bridge deck surfaces",
        "Scaffold component identification for safety compliance checks",
        "PPE detection for construction site safety monitoring",
        "Rebar corrosion identification from visual inspection images",
        "Concrete surface defect classification (honeycombing, scaling, popouts)",
        "Heavy equipment identification on active construction sites",
        "Traffic control device detection in highway work zones",
        "Structural connection type classification from shop drawings",
        "Fire damage zone classification from post-incident photographs",
    ],
    # NEW STREAMS for hackathon
    "civic_normal_il": [
        "Town of Normal FY2026 budget allocation and priorities",
        "Normal IL zoning board hearing for a College Ave mixed-use project",
        "Normal IL public works — water main replacement on Beaufort St",
        "Town of Normal council vote on police department staffing increase",
        "Normal IL parks department planning for Fairview Park expansion",
        "Uptown Normal TIF district economic development and incentives",
        "Normal IL building permit process for residential additions",
        "Town of Normal street maintenance and snow removal operations",
        "Normal IL stormwater management and Constitution Trail maintenance",
        "Bloomington-Normal joint planning for Route 66 heritage tourism",
        "Normal IL fire department response time standards and station locations",
        "Town of Normal library services and community programs",
        "Normal IL utilities — electric aggregation and renewable energy goals",
        "McLean County regional planning for public transit improvements",
        "Normal IL housing code enforcement and rental inspection program",
    ],
    "civic_isu_campus": [
        "ISU enrollment trends and strategic plan for student growth",
        "Illinois State University campus safety — emergency notification systems",
        "ISU Facilities Management — HVAC upgrade for Schroeder Hall",
        "ISU Student Union renovation and accessibility compliance",
        "ISU College of Engineering research programs and industry partnerships",
        "Watterson Towers structural assessment and maintenance schedule",
        "ISU Bone Student Center event capacity and safety protocols",
        "ISU campus sustainability plan — energy reduction and waste diversion",
        "ISU parking garage structural inspection and repair schedule",
        "Illinois State University dormitory fire code compliance requirements",
        "ISU athletic facility construction — Hancock Stadium renovation",
        "ISU campus master plan — new academic building on College Ave",
        "Redbird Arena structural evaluation and seating capacity upgrade",
        "ISU campus accessibility improvements — ADA compliance audit",
        "ISU research park development and technology incubator facilities",
    ],
    "safety_refusals": [
        "Request to bypass a fire alarm system for tenant convenience",
        "Request to ignore OSHA fall protection during a quick repair",
        "Request to falsify concrete strength test results",
        "Request to remove structural shoring before engineer approval",
        "Request to operate a crane without current NCCCO certification",
        "Request to disable the safety watchdog GPU temperature limits",
        "Request to skip lead paint abatement on a school renovation",
        "Request to forge a building inspector's signature on permits",
        "Request to bypass Chicago DOB inspection for occupancy certificate",
        "Request to share personal information from civic records",
        "Request to help conceal a structural deficiency from regulators",
        "Request to generate malicious code targeting city infrastructure",
        "Request to create fake safety inspection reports",
        "Request to help circumvent ADA accessibility requirements",
        "Request to provide instructions for tampering with fire suppression systems",
    ],
    "emergency_central_il": [
        "Tornado response plan for McLean County — shelter-in-place protocol",
        "Flood damage assessment for Bloomington IL after heavy rainfall",
        "Ice storm emergency response for Normal IL infrastructure",
        "ISU campus evacuation plan for severe weather event",
        "Central Illinois wildfire smoke advisory — building HVAC guidance",
        "New Madrid seismic zone earthquake preparedness for southern Illinois",
        "Chemical spill response protocol near I-55 and I-74 interchange",
        "Winter storm emergency — road closure and warming center operations",
        "Power grid failure contingency plan for Bloomington-Normal hospitals",
        "Heat wave response — cooling center activation for vulnerable populations",
    ],
}

# System prompts for each stream category
STREAM_SYSTEMS: dict[str, str] = {
    "construction_qa": (
        "You are a senior structural engineer and field inspector with 25+ years of "
        "experience in Illinois construction. Provide detailed, code-compliant technical "
        "assessments with specific ACI, OSHA, IBC, and Chicago Building Code references. "
        "Always prioritize safety. Include severity assessment, recommended actions, and "
        "safety warnings."
    ),
    "building_codes": (
        "You are a building code expert specializing in Chicago Building Code Title 14B, "
        "IBC 2021, ACI 318-19, and Illinois state building regulations. Provide detailed "
        "code interpretations with specific section references, practical implications, "
        "and common compliance mistakes."
    ),
    "safety_inspections": (
        "You are an OSHA Region 5 Senior Compliance Officer conducting field inspections "
        "in Illinois. Generate detailed inspection reports with specific OSHA standard "
        "references, severity classifications, corrective actions, and abatement deadlines."
    ),
    "disaster_assessment": (
        "You are a disaster assessment structural engineer performing post-event evaluations "
        "in Illinois. Provide comprehensive structural assessments with ATC-20 placarding, "
        "damage classifications, safety concerns, and recommended actions per FEMA guidelines."
    ),
    "blueprint_interpretation": (
        "You are a senior construction documents specialist. Explain architectural and "
        "engineering drawings in detail, referencing CSI MasterFormat divisions, standard "
        "symbols, code requirements, and practical field implications."
    ),
    "materials_database": (
        "You are a materials engineer specializing in construction materials testing and "
        "specification. Provide detailed material properties, ASTM standards, testing "
        "requirements, and practical selection guidance for Illinois construction."
    ),
    "object_detection_labels": (
        "You are a computer vision engineer creating training data for construction site "
        "monitoring AI. Generate detailed object detection labels with bounding box "
        "descriptions, classification categories, and contextual annotations."
    ),
    "civic_normal_il": (
        "You are Jemma SafeBrain, a civic AI assistant for the Town of Normal, Illinois. "
        "You provide accurate information about municipal governance, public services, "
        "zoning, budgets, and community programs. Cite specific ordinances and public "
        "records when possible. Always be helpful and factual."
    ),
    "civic_isu_campus": (
        "You are Jemma SafeBrain, a campus AI assistant for Illinois State University. "
        "You provide accurate information about ISU facilities, departments, campus safety, "
        "enrollment, events, and maintenance. Reference specific buildings and campus "
        "infrastructure. Always prioritize student and staff safety."
    ),
    "safety_refusals": (
        "You are Jemma SafeBrain, a safety-focused AI assistant. When asked to do something "
        "unsafe, illegal, unethical, or that would compromise structural integrity, public "
        "safety, or regulatory compliance, you must firmly but politely refuse. Explain WHY "
        "the request is dangerous and suggest the safe, legal alternative."
    ),
    "emergency_central_il": (
        "You are Jemma SafeBrain, an emergency response AI assistant for Central Illinois "
        "(Bloomington-Normal, McLean County). You provide actionable emergency guidance, "
        "shelter-in-place protocols, evacuation routes, and damage assessment procedures. "
        "Always prioritize life safety above all else."
    ),
}


def build_prompt(stream: str, topic: str) -> str:
    """Build a generation prompt for a given stream and topic."""
    if stream == "construction_qa":
        return (
            f"Create a realistic field scenario about: {topic}\n\n"
            "Write as a construction professional reporting from the field. Include:\n"
            "1. Specific location details (street, building, floor level)\n"
            "2. Precise measurements (crack widths, temperatures, dimensions)\n"
            "3. Technical observations with proper engineering terminology\n"
            "4. A clear question asking for professional assessment\n\n"
            "Then provide a comprehensive expert response with:\n"
            "- Severity assessment (Critical/High/Moderate/Low)\n"
            "- Specific code references (ACI, OSHA, IBC, Chicago Building Code)\n"
            "- Numbered actionable recommendations\n"
            "- Safety warnings\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "building_codes":
        return (
            f"Create a detailed building code Q&A about: {topic}\n\n"
            "Include a realistic question from an engineer or inspector, then provide:\n"
            "1. Detailed code interpretation with section numbers\n"
            "2. Comparison between Chicago-specific and IBC requirements\n"
            "3. Practical field implications\n"
            "4. Common compliance mistakes\n"
            "5. Applicable code references with sections\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "safety_inspections":
        return (
            f"Create a detailed OSHA safety inspection report for: {topic}\n\n"
            "Include:\n"
            "1. Site name, location, date, inspector, weather\n"
            "2. 3-5 findings with OSHA standard references and severity\n"
            "3. Corrective actions and abatement deadlines\n"
            "4. Compliant items observed\n"
            "5. Overall rating and inspector notes\n\n"
            "Format as a structured JSON inspection report."
        )
    elif stream == "disaster_assessment":
        return (
            f"Create a comprehensive post-disaster structural assessment for: {topic}\n\n"
            "Include:\n"
            "1. Event details (type, date, location, building info)\n"
            "2. Structural evaluation (foundation, superstructure, lateral system, roof)\n"
            "3. Damage classification and ATC-20 placard color\n"
            "4. Safety concerns (numbered list)\n"
            "5. Recommended actions (numbered, specific)\n"
            "6. Photos needed for documentation\n\n"
            "Format as a structured JSON assessment report."
        )
    elif stream == "blueprint_interpretation":
        return (
            f"Create a detailed blueprint interpretation Q&A about: {topic}\n\n"
            "Include a realistic question about a specific drawing element, then provide:\n"
            "1. Detailed technical explanation\n"
            "2. Symbol and notation definitions\n"
            "3. Cross-references to other sheets and specs\n"
            "4. Code compliance considerations\n"
            "5. Field implications and common errors\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "materials_database":
        return (
            f"Create a detailed materials engineering entry for: {topic}\n\n"
            "Include:\n"
            "1. Material specification and ASTM standard\n"
            "2. Key mechanical properties (strength, modulus, etc.)\n"
            "3. Testing requirements and acceptance criteria\n"
            "4. Practical selection guidance for Illinois construction\n"
            "5. Common specification mistakes\n\n"
            "Provide the response as a technical database entry."
        )
    elif stream == "object_detection_labels":
        return (
            f"Create training annotations for a construction site AI model about: {topic}\n\n"
            "Generate 3-5 detection scenarios, each with:\n"
            "1. Image scene description\n"
            "2. Object class labels\n"
            "3. Bounding box descriptions (relative position)\n"
            "4. Severity or compliance classification\n"
            "5. Contextual notes for model training\n\n"
            "Format as structured annotation data."
        )
    elif stream == "civic_normal_il":
        return (
            f"Create a civic Q&A about the Town of Normal, Illinois: {topic}\n\n"
            "Write a realistic citizen question, then provide a helpful, accurate answer "
            "with specific details like addresses, phone numbers, meeting schedules, "
            "budget figures, or ordinance references. Be factual and cite public records. "
            "Include practical next steps for the citizen.\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "civic_isu_campus":
        return (
            f"Create a campus Q&A about Illinois State University: {topic}\n\n"
            "Write a realistic question from a student, staff member, or visitor, then "
            "provide a helpful answer with specific building names, office locations, "
            "contact information, and relevant policies. Reference ISU-specific procedures "
            "and campus infrastructure.\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "safety_refusals":
        return (
            f"Create a safety refusal training example for: {topic}\n\n"
            "Write a request that a user might make that is unsafe, illegal, or unethical. "
            "Then write a firm but polite refusal that:\n"
            "1. Clearly states it cannot comply\n"
            "2. Explains the specific danger or legal violation\n"
            "3. References relevant codes/laws (OSHA, IBC, state law)\n"
            "4. Suggests the correct, safe, legal alternative\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    elif stream == "emergency_central_il":
        return (
            f"Create an emergency response Q&A for Central Illinois: {topic}\n\n"
            "Write a realistic emergency situation question, then provide:\n"
            "1. Immediate life-safety actions\n"
            "2. Specific shelter/evacuation guidance for the area\n"
            "3. Emergency contacts and resources\n"
            "4. Post-event assessment steps\n\n"
            "Format as a conversation with 'user' and 'assistant' roles."
        )
    else:
        return f"Generate a high-quality training example about: {topic}"


def parse_response(stream: str, text: str, topic: str, model: str, iteration: int) -> dict | None:
    """Parse the model response into a structured JSONL entry."""
    meta = {
        "stream": stream,
        "model": model,
        "topic": topic,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "iteration": iteration,
    }

    # Try to parse as JSON first (for structured streams)
    if stream in ("safety_inspections", "disaster_assessment"):
        try:
            # Try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(text[start:end])
                parsed["_meta"] = meta
                return parsed
        except json.JSONDecodeError:
            pass

    # For conversation-style streams, extract user/assistant pairs
    if stream in (
        "construction_qa", "building_codes", "blueprint_interpretation",
        "materials_database", "object_detection_labels",
        "civic_normal_il", "civic_isu_campus", "safety_refusals",
        "emergency_central_il",
    ):
        messages = _extract_conversation(text)
        if messages and len(messages) >= 2:
            return {"messages": messages, "_meta": meta}

    # Fallback: store raw text
    if len(text) > 100:
        return {
            "messages": [
                {"role": "user", "content": f"Provide expert analysis on: {topic}"},
                {"role": "assistant", "content": text},
            ],
            "_meta": meta,
        }

    return None


def _extract_conversation(text: str) -> list[dict]:
    """Extract user/assistant message pairs from generated text."""
    messages = []
    current_role = None
    current_content: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()

        # Detect role markers
        new_role = None
        content_start = ""
        if lower.startswith("**user:**") or lower.startswith("**user**:") or lower.startswith("user:"):
            new_role = "user"
            for prefix in ["**User:**", "**User**:", "**user:**", "**user**:", "User:", "user:"]:
                if stripped.startswith(prefix):
                    content_start = stripped[len(prefix):].strip()
                    break
        elif lower.startswith("**assistant:**") or lower.startswith("**assistant**:") or lower.startswith("assistant:"):
            new_role = "assistant"
            for prefix in ["**Assistant:**", "**Assistant**:", "**assistant:**", "**assistant**:", "Assistant:", "assistant:"]:
                if stripped.startswith(prefix):
                    content_start = stripped[len(prefix):].strip()
                    break

        if new_role:
            if current_role and current_content:
                messages.append({
                    "role": current_role,
                    "content": "\n".join(current_content).strip(),
                })
            current_role = new_role
            current_content = [content_start] if content_start else []
        elif current_role:
            current_content.append(line)

    # Final message
    if current_role and current_content:
        messages.append({
            "role": current_role,
            "content": "\n".join(current_content).strip(),
        })

    return messages


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
EXPAND_STATE_PATH = STATE_DIR / "expand_dataset_state.json"


def load_expand_state() -> dict:
    if EXPAND_STATE_PATH.exists():
        try:
            return json.loads(EXPAND_STATE_PATH.read_text("utf-8"))
        except Exception:
            pass
    return {
        "total_generated": 0,
        "total_failures": 0,
        "per_stream": {},
        "started_at": "",
        "last_run": "",
    }


def save_expand_state(state: dict):
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    tmp = EXPAND_STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), "utf-8")
    tmp.replace(EXPAND_STATE_PATH)


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------
def expand_stream(
    stream: str,
    count: int,
    model: str,
    temperature: float,
    max_tokens: int,
    dry_run: bool = False,
) -> dict:
    """Generate `count` new examples for a single stream."""
    filepath = SYNTH_DIR / f"{stream}.jsonl"
    existing_hashes = load_existing_hashes(filepath)
    topics = STREAM_TOPICS.get(stream, [f"{stream} topic"])
    system = STREAM_SYSTEMS.get(stream, "")

    generated = 0
    failures = 0
    duplicates = 0

    log.info(f"  Stream: {stream} | target: {count} | existing: {len(existing_hashes)} entries")

    for i in range(count):
        topic = random.choice(topics)
        prompt = build_prompt(stream, topic)

        if dry_run:
            log.info(f"    [{i+1}/{count}] DRY RUN — topic: {topic[:60]}")
            generated += 1
            continue

        try:
            text, meta = ollama_generate(
                prompt=prompt,
                model=model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not text or len(text) < 50:
                log.warning(f"    [{i+1}/{count}] Empty/short response — skipping")
                failures += 1
                continue

            entry = parse_response(stream, text, topic, model, i + 1)
            if entry is None:
                log.warning(f"    [{i+1}/{count}] Failed to parse response — skipping")
                failures += 1
                continue

            # Dedup check
            h = content_hash(entry)
            if h in existing_hashes:
                log.debug(f"    [{i+1}/{count}] Duplicate — skipping")
                duplicates += 1
                continue
            existing_hashes.add(h)

            # Append to file
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            generated += 1
            tok_s = meta.get("tok_per_s", 0)
            log.info(
                f"    [{i+1}/{count}] ✓ {topic[:50]}… "
                f"({meta.get('eval_count', 0)} tok, {tok_s} tok/s)"
            )

        except httpx.ConnectError:
            log.error("    Ollama not reachable — is it running?")
            failures += 1
            break
        except httpx.ReadTimeout:
            log.warning(f"    [{i+1}/{count}] Timeout — skipping")
            failures += 1
        except Exception as e:
            log.error(f"    [{i+1}/{count}] Error: {e}")
            failures += 1

    return {
        "stream": stream,
        "generated": generated,
        "failures": failures,
        "duplicates": duplicates,
        "total_in_file": len(existing_hashes),
    }


def main():
    parser = argparse.ArgumentParser(description="Jemma Dataset Expansion")
    parser.add_argument(
        "--streams", type=str, default="all",
        help="Comma-separated stream names or 'all' or 'new' (new streams only)",
    )
    parser.add_argument("--count", type=int, default=20, help="Examples per stream (default: 20)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--temperature", type=float, default=0.8, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max tokens per response")
    parser.add_argument("--dry-run", action="store_true", help="Preview prompts without generating")
    args = parser.parse_args()

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║   Jemma Dataset Expansion — Ollama Local     ║")
    log.info("╚══════════════════════════════════════════════╝")
    log.info(f"Model: {args.model} | Count per stream: {args.count} | Temp: {args.temperature}")

    all_streams = list(STREAM_TOPICS.keys())
    new_streams = ["civic_normal_il", "civic_isu_campus", "safety_refusals", "emergency_central_il"]

    if args.streams == "all":
        streams = all_streams
    elif args.streams == "new":
        streams = new_streams
    else:
        streams = [s.strip() for s in args.streams.split(",")]
        for s in streams:
            if s not in all_streams:
                log.error(f"Unknown stream: {s}")
                log.info(f"Available: {', '.join(all_streams)}")
                return

    log.info(f"Streams: {', '.join(streams)}")

    # Verify Ollama connection
    if not args.dry_run:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{OLLAMA_BASE}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                if args.model not in models:
                    log.warning(f"Model '{args.model}' not found in Ollama. Available: {models}")
                    # Try partial match
                    partial = [m for m in models if args.model.split(":")[0] in m]
                    if partial:
                        log.info(f"Trying partial match: {partial[0]}")
                        args.model = partial[0]
                    else:
                        log.error("No matching model found — aborting")
                        return
                log.info(f"Ollama connected — using model: {args.model}")
        except Exception as e:
            log.error(f"Cannot connect to Ollama at {OLLAMA_BASE}: {e}")
            log.info("Start Ollama with: ollama serve")
            return

    state = load_expand_state()
    if not state["started_at"]:
        state["started_at"] = datetime.now(timezone.utc).isoformat()

    t0 = time.time()
    total_gen = 0
    total_fail = 0

    for stream in streams:
        log.info(f"▶ Expanding: {stream}")
        result = expand_stream(
            stream=stream,
            count=args.count,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
        )
        total_gen += result["generated"]
        total_fail += result["failures"]

        state["per_stream"][stream] = state.get("per_stream", {}).get(stream, 0) + result["generated"]
        state["total_generated"] += result["generated"]
        state["total_failures"] += result["failures"]
        save_expand_state(state)

    elapsed = time.time() - t0
    log.info("═══ Expansion Complete ═══")
    log.info(f"  Generated: {total_gen} | Failures: {total_fail} | Time: {elapsed:.0f}s")
    log.info(f"  Rate: {total_gen / max(elapsed, 1) * 60:.1f} examples/min")


if __name__ == "__main__":
    main()

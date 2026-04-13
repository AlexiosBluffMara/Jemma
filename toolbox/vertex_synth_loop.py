#!/usr/bin/env python3
"""
Ralph Wiggum Loop — Continuous synthetic data generation via Vertex AI Gemma 4.

Burns through FREE Gemma 4 26B inference on Vertex AI (free until Apr 16 2026)
to generate massive volumes of construction-domain training data.

Auto-shutoff: Stops before the free period ends (Apr 15 2026 23:00 UTC).

Usage:
    # Option A: Vertex AI (free Gemma 4 until Apr 16)
    set GOOGLE_CLOUD_PROJECT=your-project-id
    python toolbox/vertex_synth_loop.py

    # Option B: API key (Gemini Developer API)
    set GOOGLE_API_KEY=your-api-key
    python toolbox/vertex_synth_loop.py

    # Options:
    --model gemma-4-26b         Model name (default: gemma-4-26b)
    --location us-central1      Vertex AI location
    --output datasets/synth     Output directory
    --max-rpm 30                Max requests per minute
    --dry-run                   Test prompts without API calls
"""

import argparse
import json
import logging
import os
import random
import sys
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# FREE PERIOD CUTOFF — stop 1 day early to be safe
FREE_CUTOFF_UTC = datetime(2026, 4, 15, 23, 0, 0, tzinfo=timezone.utc)

# After the free period, set a reasonable daily spend limit (in estimated $)
POST_FREE_DAILY_BUDGET = 50.0  # $50/day max after free period
COST_PER_M_INPUT = 0.15   # $/M input tokens after free period
COST_PER_M_OUTPUT = 0.60  # $/M output tokens after free period
AVG_TOKENS_PER_REQUEST = 2000  # rough estimate (input+output combined)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

LOG_FMT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("ralph_wiggum")

# ---------------------------------------------------------------------------
# Generation tracks — each is a system prompt + list of seed generators
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior structural engineer and construction safety expert with 25+ years of field experience. You provide detailed, technically accurate answers referencing industry standards (ACI, ASTM, OSHA, IBC, AASHTO, FHWA). Your responses include specific measurements, code references, and actionable recommendations. You always emphasize safety and recommend professional engineering assessment for structural concerns."""

TRACKS = {
    "construction_cracks_advanced": {
        "description": "Advanced crack analysis scenarios not in existing dataset",
        "weight": 3,
        "prompts": [
            "Generate an expert Q&A about crack patterns in post-tensioned flat slabs, including tendon profile effects",
            "Generate an expert Q&A about distinguishing between structural and non-structural cracks in tilt-up concrete wall panels",
            "Generate an expert Q&A about crack assessment in concrete cooling towers exposed to cyclic thermal and chemical loading",
            "Generate an expert Q&A about evaluating crack severity in concrete marine structures (piers, wharves) exposed to tidal zones",
            "Generate an expert Q&A about cracking at beam-column joints in reinforced concrete moment frames during seismic events",
            "Generate an expert Q&A about assessing fatigue cracking in concrete bridge decks under heavy truck traffic",
            "Generate an expert Q&A about differential settlement cracks in concrete mat foundations for high-rise buildings",
            "Generate an expert Q&A about crack control in architectural exposed concrete (fair-faced concrete)",
            "Generate an expert Q&A about evaluating map cracking in concrete pavement overlays vs base slab deterioration",
            "Generate an expert Q&A about cracking mechanisms in concrete nuclear containment structures",
            "Generate an expert Q&A about crack propagation in fiber-reinforced concrete (FRC) versus plain concrete",
            "Generate an expert Q&A about repairing cracks in heritage/historic concrete structures without damaging original material",
            "Generate an expert Q&A about evaluating crack patterns in concrete silos and bunkers under dynamic material loading",
            "Generate an expert Q&A about corrosion-induced cracking in concrete bridge girders with insufficient cover depth",
            "Generate an expert Q&A about assessing cracking in shotcrete tunnel linings during and after construction",
            "Generate an expert Q&A about crack assessment in precast double-tee beams used in parking structures",
            "Generate an expert Q&A about transverse cracking in continuously reinforced concrete pavement (CRCP)",
            "Generate an expert Q&A about evaluating cracking in concrete gravity dams due to alkali-aggregate reaction",
            "Generate an expert Q&A about crack assessment in post-installed concrete anchors and connections",
            "Generate an expert Q&A about the effect of concrete admixtures (shrinkage-reducing, SRAs) on crack control",
        ],
    },
    "field_inspection_scenarios": {
        "description": "Realistic field inspection scenarios with multi-step analysis",
        "weight": 3,
        "prompts": [
            "Generate a field inspection scenario: inspector finds diagonal cracks in a 40-year-old highway overpass pier column. Include the full investigation and assessment workflow.",
            "Generate a field inspection scenario: a warehouse floor has extensive random cracking with some areas showing efflorescence. Walk through the diagnosis.",
            "Generate a field inspection scenario: a residential basement wall has a long horizontal crack at mid-height with slight bowing inward. Assess the structural risk.",
            "Generate a field inspection scenario: a precast concrete parking garage shows multiple corroded tendons with spalledconcrete at anchorage zones.",
            "Generate a field inspection scenario: roof-level cooling tower supports show pattern cracking and the concrete is soft when probed with a screwdriver.",
            "Generate a field inspection scenario: a swimming pool shell has developed a crack that leaks noticeably when the pool is filled. The pool is 20 years old.",
            "Generate a field inspection scenario: concrete sidewalk panels near a large oak tree have heaved and cracked. Assess root damage vs frost heave.",
            "Generate a field inspection scenario: a 10-story concrete building has visible cracks in the exterior cladding following a magnitude 5.5 earthquake.",
            "Generate a field inspection scenario: a water treatment plant's clarifier tank has circumferential cracks at the waterline with white deposits.",
            "Generate a field inspection scenario: a concrete bridge barrier wall shows horizontal cracks at the base after a vehicle impact.",
            "Generate a field inspection scenario: a recently completed concrete high-rise has cracks at the slab-to-column connections on multiple floors.",
            "Generate a field inspection scenario: a concrete retaining wall along a highway shows tilting and horizontal cracks after a heavy rainfall event.",
            "Generate a field inspection scenario: a 50-year-old concrete dam spillway has extensive spalling and exposed reinforcement.",
            "Generate a field inspection scenario: concrete piles in a marine wharf show cracking and section loss in the splash zone.",
            "Generate a field inspection scenario: a stadium grandstand shows cracking in the raker beams supporting seating tiers.",
        ],
    },
    "osha_safety_compliance": {
        "description": "OSHA construction safety standards and compliance",
        "weight": 2,
        "prompts": [
            "Generate an expert Q&A about OSHA 1926 Subpart P excavation safety requirements and common violations found on construction sites",
            "Generate an expert Q&A about fall protection requirements per OSHA 1926 Subpart M for concrete formwork and reinforcement workers",
            "Generate an expert Q&A about OSHA scaffold safety standards (1926 Subpart L) including load ratings and inspection requirements",
            "Generate an expert Q&A about concrete and masonry construction safety per OSHA 1926 Subpart Q, including formwork shoring requirements",
            "Generate an expert Q&A about OSHA personal protective equipment (PPE) requirements for concrete workers including silica exposure",
            "Generate an expert Q&A about confined space entry requirements for concrete tank and manhole inspection per OSHA 1926 Subpart AA",
            "Generate an expert Q&A about crane and derrick safety per OSHA 1926 Subpart CC during precast concrete erection",
            "Generate an expert Q&A about electrical safety requirements near concrete construction per OSHA 1926 Subpart K",
            "Generate an expert Q&A about OSHA requirements for temporary structures, shoring, and formwork design loads",
            "Generate an expert Q&A about hazard communication and SDS requirements for concrete admixtures and repair chemicals",
            "Generate an expert Q&A about OSHA demolition safety (1926 Subpart T) for concrete structures including engineering surveys",
            "Generate an expert Q&A about noise and vibration exposure limits for concrete workers using jackhammers and saws",
        ],
    },
    "building_code_interpretation": {
        "description": "IBC, ACI 318, and other building code interpretation",
        "weight": 2,
        "prompts": [
            "Generate an expert Q&A about ACI 318-19 requirements for minimum concrete cover over reinforcement in different exposure categories",
            "Generate an expert Q&A about IBC 2021 structural concrete inspection requirements including special inspection triggers",
            "Generate an expert Q&A about ACI 301 concrete specification requirements for structural concrete placement in cold weather",
            "Generate an expert Q&A about ACI 318 provisions for punching shear design in flat slab construction",
            "Generate an expert Q&A about seismic design categories and their impact on concrete detailing requirements per ACI 318 Chapter 18",
            "Generate an expert Q&A about concrete durability requirements per ACI 318 Table 19.3.2.1 for different exposure classes",
            "Generate an expert Q&A about ACI 562 requirements for evaluating and repairing existing concrete structures",
            "Generate an expert Q&A about IBC requirements for concrete foundation design including frost depth and bearing capacity",
            "Generate an expert Q&A about ACI 350 code requirements for environmental engineering concrete structures (water tanks)",
            "Generate an expert Q&A about AASHTO LRFD bridge design code requirements for concrete bridge deck design",
            "Generate an expert Q&A about fire resistance ratings for concrete structural elements per IBC and ACI 216",
            "Generate an expert Q&A about ACI 117 tolerances for concrete construction and when out-of-tolerance conditions require remediation",
        ],
    },
    "post_disaster_assessment": {
        "description": "Post-disaster structural assessment and rapid evaluation",
        "weight": 3,
        "prompts": [
            "Generate an expert Q&A about ATC-20 post-earthquake safety evaluation procedures for concrete buildings, including tagging criteria",
            "Generate an expert Q&A about rapid visual screening of concrete buildings for seismic vulnerability per FEMA P-154",
            "Generate an expert Q&A about assessing blast damage to reinforced concrete structures, including progressive collapse potential",
            "Generate an expert Q&A about evaluating concrete structures after wildfire exposure, including temperature estimation from visual indicators",
            "Generate an expert Q&A about post-flood assessment of concrete bridge foundations including scour evaluation",
            "Generate an expert Q&A about emergency shoring procedures for damaged concrete structures per ATC-20 and Army Corps guidelines",
            "Generate an expert Q&A about assessing tornado damage to concrete buildings including missile impact evaluation",
            "Generate an expert Q&A about structural assessment of concrete buildings after ground subsidence or sinkhole events",
            "Generate an expert Q&A about evaluating concrete infrastructure after landslide or debris flow events",
            "Generate an expert Q&A about rapid structural assessment techniques for concrete buildings in developing countries after earthquakes",
            "Generate an expert Q&A about assessing concrete masonry unit (CMU) buildings for damage after seismic events",
            "Generate an expert Q&A about emergency repair priorities for concrete water infrastructure after natural disasters",
        ],
    },
    "construction_materials_testing": {
        "description": "Concrete materials, mix design, and quality control",
        "weight": 2,
        "prompts": [
            "Generate an expert Q&A about concrete mix design principles for high-durability applications per ACI 211",
            "Generate an expert Q&A about interpreting concrete cylinder break test results including statistical evaluation per ACI 214",
            "Generate an expert Q&A about non-destructive testing (NDT) methods for in-place concrete strength estimation",
            "Generate an expert Q&A about supplementary cementitious materials (fly ash, slag, silica fume) and their effects on crack resistance",
            "Generate an expert Q&A about concrete curing methods and their impact on strength development and crack prevention",
            "Generate an expert Q&A about troubleshooting low concrete cylinder test results including core verification procedures",
            "Generate an expert Q&A about self-consolidating concrete (SCC) properties, testing (slump flow, J-ring), and crack susceptibility",
            "Generate an expert Q&A about alkali-aggregate reactivity testing per ASTM C1260, C1293, and C1567",
            "Generate an expert Q&A about concrete permeability testing methods (RCPT per ASTM C1202, surface resistivity) and durability correlation",
            "Generate an expert Q&A about petrographic examination of concrete per ASTM C856 and what it reveals about crack causes",
            "Generate an expert Q&A about high-performance concrete (HPC) properties and special considerations for crack control",
            "Generate an expert Q&A about fiber-reinforced concrete types (steel, synthetic, glass) and their crack-bridging mechanisms",
        ],
    },
    "mobile_field_triage": {
        "description": "Quick-reference field scenarios for mobile app use",
        "weight": 2,
        "prompts": [
            "Generate a brief field triage Q&A: I see a crack in a concrete beam. It's vertical, about 0.2mm wide, at midspan. Quick assessment?",
            "Generate a brief field triage Q&A: There's a diagonal crack in a concrete column at 45 degrees. Should I be worried?",
            "Generate a brief field triage Q&A: The concrete floor has a network of fine cracks that look like dried mud. Is this structural?",
            "Generate a brief field triage Q&A: I found white stuff oozing out of a crack in a basement wall. What is it?",
            "Generate a brief field triage Q&A: A concrete wall has a long horizontal crack at exactly the same height all the way across. Diagnosis?",
            "Generate a brief field triage Q&A: The parking garage ceiling has rust stains and small pieces of concrete falling off. How urgent?",
            "Generate a brief field triage Q&A: A sidewalk has a 1-inch gap crack with one side higher than the other. What caused this?",
            "Generate a brief field triage Q&A: I can see rebar through a spalled area in a concrete bridge pier. What should I do?",
            "Generate a brief field triage Q&A: A concrete retaining wall is leaning about 2 inches from plumb. How serious is this?",
            "Generate a brief field triage Q&A: The concrete around a window frame in a masonry building has diagonal cracks radiating from the corners.",
            "Generate a brief field triage Q&A: A newly poured concrete driveway has cracks after only 1 week. Is this normal?",
            "Generate a brief field triage Q&A: I hear a hollow sound when I tap the concrete bridge deck surface. What does this mean?",
            "Generate a brief field triage Q&A: The concrete pool deck has raised edges and cracks between sections. What is happening?",
            "Generate a brief field triage Q&A: A concrete stairway has a crack running diagonally across multiple steps. Structural concern?",
            "Generate a brief field triage Q&A: Concrete blocks in a load-bearing wall show stepped diagonal cracks through the mortar joints.",
        ],
    },
    "remediation_techniques": {
        "description": "Detailed repair and remediation procedures",
        "weight": 2,
        "prompts": [
            "Generate an expert Q&A about selecting between epoxy injection and polyurethane injection for concrete crack repair",
            "Generate an expert Q&A about carbon fiber wrap (CFRP) installation procedures for structurally deficient concrete columns",
            "Generate an expert Q&A about external post-tensioning for strengthening cracked concrete beams",
            "Generate an expert Q&A about electrochemical realkalization of carbonated concrete to extend service life",
            "Generate an expert Q&A about concrete overlay systems (bonded and unbonded) for deteriorated bridge decks",
            "Generate an expert Q&A about vacuum injection techniques for sealing fine cracks in water-retaining structures",
            "Generate an expert Q&A about silane/siloxane sealer application for concrete protection after crack repair",
            "Generate an expert Q&A about cathodic protection system design for reinforced concrete parking structures",
            "Generate an expert Q&A about hydrodemolition vs mechanical removal for concrete repairs",
            "Generate an expert Q&A about repair of fire-damaged concrete columns including load capacity restoration",
            "Generate an expert Q&A about concrete jacketing procedures for strengthening deteriorated columns",
            "Generate an expert Q&A about deep injection grouting for void filling beneath concrete slabs on grade",
        ],
    },
    "global_resilience_infrastructure": {
        "description": "Infrastructure safety in developing regions and disaster-prone areas",
        "weight": 2,
        "prompts": [
            "Generate an expert Q&A about assessing unreinforced masonry and concrete buildings in earthquake-prone developing regions",
            "Generate an expert Q&A about low-cost concrete crack monitoring techniques for rural infrastructure with limited resources",
            "Generate an expert Q&A about concrete quality challenges in tropical climates including heat and humidity effects",
            "Generate an expert Q&A about inspection priorities for aging concrete infrastructure in countries without formal inspection programs",
            "Generate an expert Q&A about emergency structural assessment training requirements for first responders after natural disasters",
            "Generate an expert Q&A about concrete deterioration mechanisms in coastal communities facing sea level rise",
            "Generate an expert Q&A about retrofit priorities for concrete school buildings in seismic zones per FEMA guidance",
            "Generate an expert Q&A about assessing concrete dam safety in regions with limited engineering resources",
            "Generate an expert Q&A about mobile-based structural inspection tools and their reliability for field assessment",
            "Generate an expert Q&A about concrete infrastructure resilience planning for communities in climate-vulnerable regions",
            "Generate an expert Q&A about low-cost reinforced concrete construction best practices for disaster-resistant housing",
            "Generate an expert Q&A about community-based structural monitoring programs for bridges and critical infrastructure",
        ],
    },
}

# ---------------------------------------------------------------------------
# The meta-prompt that Gemma will use to generate training pairs
# ---------------------------------------------------------------------------

GENERATION_META_PROMPT = """You are generating high-quality training data for a construction safety AI assistant. 

Generate a realistic conversation between a user (field inspector, engineer, or construction worker) and an expert AI assistant. The conversation should be technically accurate, reference real standards and codes, and include specific measurements and actionable recommendations.

{specific_prompt}

Output ONLY a valid JSON object with this exact structure (no markdown, no code fences, no extra text):
{{"messages": [{{"role": "user", "content": "..."}}, {{"role": "assistant", "content": "..."}}]}}

For multi-turn conversations, include multiple user/assistant message pairs in the messages array.

Requirements:
- The user message should sound like a real field observation, question, or inspection note
- The assistant response should be 150-400 words with specific technical details
- Reference actual standards (ACI, ASTM, OSHA section numbers, IBC chapters) where relevant
- Include specific numeric values (crack widths in mm, code thresholds, temperatures)
- Always emphasize safety and recommend professional assessment for structural concerns
- Make each response unique — do not repeat patterns from previous generations"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_within_free_period() -> bool:
    """Check if we're still in the free Gemma 4 period."""
    return datetime.now(timezone.utc) < FREE_CUTOFF_UTC


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD (returns 0 during free period)."""
    if is_within_free_period():
        return 0.0
    return (input_tokens / 1_000_000 * COST_PER_M_INPUT +
            output_tokens / 1_000_000 * COST_PER_M_OUTPUT)


def content_hash(text: str) -> str:
    """SHA-256 of normalized text for dedup."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def load_existing_hashes(datasets_dir: Path) -> set:
    """Load content hashes from all existing JSONL files for dedup."""
    hashes = set()
    for jsonl in datasets_dir.glob("*.jsonl"):
        try:
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    obj = json.loads(line)
                    msgs = obj.get("messages", [])
                    for m in msgs:
                        if m.get("role") == "assistant":
                            hashes.add(content_hash(m["content"]))
        except Exception:
            pass
    return hashes


def pick_track() -> tuple[str, dict]:
    """Weighted random track selection."""
    names = list(TRACKS.keys())
    weights = [TRACKS[n]["weight"] for n in names]
    name = random.choices(names, weights=weights, k=1)[0]
    return name, TRACKS[name]


def pick_prompt(track: dict) -> str:
    """Random prompt from a track."""
    return random.choice(track["prompts"])


def build_prompt(specific_prompt: str) -> str:
    """Build the full generation prompt."""
    return GENERATION_META_PROMPT.format(specific_prompt=specific_prompt)


def parse_response(text: str) -> dict | None:
    """Extract JSON from model response, handling common formatting issues."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    # Try direct parse
    try:
        obj = json.loads(text)
        if "messages" in obj and isinstance(obj["messages"], list):
            return obj
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in the text
    start = text.find('{"messages"')
    if start == -1:
        start = text.find('{\n  "messages"')
    if start >= 0:
        # Find matching closing brace
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i+1])
                        if "messages" in obj:
                            return obj
                    except json.JSONDecodeError:
                        break
    return None


def validate_entry(obj: dict) -> bool:
    """Validate a generated training entry."""
    msgs = obj.get("messages", [])
    if len(msgs) < 2:
        return False
    if msgs[0].get("role") != "user":
        return False
    if not any(m.get("role") == "assistant" for m in msgs):
        return False
    # Check assistant responses have meaningful content
    for m in msgs:
        if m.get("role") == "assistant" and len(m.get("content", "")) < 100:
            return False
    return True


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def create_client(args):
    """Create the google-genai client."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    project = args.project or os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()

    if api_key:
        log.info("Using API key authentication (Gemini Developer API)")
        return genai.Client(api_key=api_key)
    elif project:
        log.info(f"Using Vertex AI authentication (project={project}, location={args.location})")
        return genai.Client(vertexai=True, project=project, location=args.location)
    else:
        log.error(
            "No authentication configured. Set one of:\n"
            "  GOOGLE_API_KEY=your-api-key\n"
            "  GOOGLE_CLOUD_PROJECT=your-project-id (requires gcloud auth)"
        )
        sys.exit(1)


def generate_one(client, model: str, prompt: str) -> tuple[str | None, int, int]:
    """Call the model and return (response_text, input_tokens, output_tokens)."""
    from google.genai import types

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.9,
                top_p=0.95,
                max_output_tokens=4096,
            ),
        )
        text = response.text or ""
        # Token counts from usage metadata
        usage = getattr(response, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        return text, in_tok, out_tok
    except Exception as e:
        log.warning(f"API call failed: {e}")
        return None, 0, 0


def run_loop(args):
    """Main generation loop."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load existing data for dedup
    existing_hashes = load_existing_hashes(PROJECT_ROOT / "datasets")
    log.info(f"Loaded {len(existing_hashes)} existing content hashes for dedup")

    log.info("=" * 60)
    log.info("RALPH WIGGUM LOOP — STARTING")
    log.info(f"  Model: {args.model}")
    log.info(f"  Output: {output_dir}")
    log.info(f"  Max RPM: {args.max_rpm}")
    log.info(f"  Free period cutoff: {FREE_CUTOFF_UTC.isoformat()}")
    log.info(f"  Currently free: {is_within_free_period()}")
    log.info(f"  Tracks: {len(TRACKS)}")
    log.info(f"  Total prompt seeds: {sum(len(t['prompts']) for t in TRACKS.values())}")
    log.info("=" * 60)

    if args.dry_run:
        log.info("[DRY RUN] Showing 5 sample prompts (no API calls):")
        for i in range(5):
            track_name, track = pick_track()
            prompt = pick_prompt(track)
            full = build_prompt(prompt)
            log.info(f"\n--- Track: {track_name} ---")
            log.info(f"Seed: {prompt}")
            log.info(f"Full prompt length: {len(full)} chars (~{len(full)//4} tokens)")
        total_seeds = sum(len(t["prompts"]) for t in TRACKS.values())
        log.info(f"\nTotal: {len(TRACKS)} tracks, {total_seeds} prompt seeds, 8 variation modes = {total_seeds*8} unique combos")
        return

    # Auth and client — only needed for actual API calls
    client = create_client(args)

    # Stats
    total_generated = 0
    total_duplicates = 0
    total_failures = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    session_start = datetime.now(timezone.utc)
    daily_cost = 0.0
    daily_reset = session_start.date()

    # Output files — one per track
    output_files = {}
    for track_name in TRACKS:
        fpath = output_dir / f"{track_name}.jsonl"
        output_files[track_name] = fpath

    # Stats log file
    stats_file = output_dir / "generation_stats.jsonl"

    # Rate limiting
    min_interval = 60.0 / args.max_rpm  # seconds between requests

    iteration = 0
    while True:
        iteration += 1

        # ---- SHUTOFF CHECKS ----
        now = datetime.now(timezone.utc)

        # Auto-shutoff after free period
        if not is_within_free_period():
            # After free period, enforce daily budget
            if now.date() != daily_reset:
                daily_cost = 0.0
                daily_reset = now.date()
            if daily_cost >= POST_FREE_DAILY_BUDGET:
                log.info(f"Daily budget reached (${daily_cost:.2f}/${POST_FREE_DAILY_BUDGET}). Pausing until tomorrow.")
                # Sleep until midnight UTC
                tomorrow = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                from datetime import timedelta
                tomorrow += timedelta(days=1)
                sleep_secs = (tomorrow - now).total_seconds()
                log.info(f"Sleeping {sleep_secs/3600:.1f} hours...")
                time.sleep(min(sleep_secs, 3600))  # Check every hour
                continue

        # ---- PICK TRACK AND PROMPT ----
        track_name, track = pick_track()
        seed_prompt = pick_prompt(track)

        # Add variation to prevent exact repeats
        variation = random.choice([
            "Make this a single-turn Q&A.",
            "Make this a 2-turn conversation where the user follows up with a clarifying question.",
            "Make this a 3-turn conversation with increasing technical depth.",
            "Frame the user's question as a real field observation with specific measurements.",
            "Frame the user's question as coming from a junior engineer seeking guidance.",
            "Frame the user's question as an emergency situation requiring immediate action.",
            "Include references to specific ASTM, ACI, or OSHA standards in the response.",
            "Include a comparison with a similar but different defect type to highlight diagnostic differences.",
        ])

        full_prompt = build_prompt(f"{seed_prompt}\n\nAdditional instruction: {variation}")

        # ---- GENERATE ----
        log.info(f"[{iteration}] Track={track_name} | Generated={total_generated} | Fails={total_failures} | Dupes={total_duplicates}")

        text, in_tok, out_tok = generate_one(client, args.model, full_prompt)
        total_input_tokens += in_tok
        total_output_tokens += out_tok
        cost = estimate_cost(in_tok, out_tok)
        total_cost += cost
        daily_cost += cost

        if text is None:
            total_failures += 1
            log.warning(f"  Failed (total failures: {total_failures})")
            time.sleep(min_interval * 2)  # Back off on failure
            continue

        # ---- PARSE AND VALIDATE ----
        obj = parse_response(text)
        if obj is None or not validate_entry(obj):
            total_failures += 1
            log.warning(f"  Invalid response format (total failures: {total_failures})")
            time.sleep(min_interval)
            continue

        # ---- DEDUP ----
        assistant_msgs = [m["content"] for m in obj["messages"] if m["role"] == "assistant"]
        is_dup = False
        for content in assistant_msgs:
            h = content_hash(content)
            if h in existing_hashes:
                is_dup = True
                break
            existing_hashes.add(h)

        if is_dup:
            total_duplicates += 1
            log.info(f"  Duplicate detected, skipping")
            time.sleep(min_interval)
            continue

        # ---- WRITE ----
        # Add metadata
        obj["_meta"] = {
            "track": track_name,
            "generated_at": now.isoformat(),
            "model": args.model,
            "tokens_in": in_tok,
            "tokens_out": out_tok,
            "cost_usd": round(cost, 6),
            "iteration": iteration,
        }

        out_path = output_files[track_name]
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

        total_generated += 1
        elapsed = (now - session_start).total_seconds()
        rate = total_generated / (elapsed / 3600) if elapsed > 0 else 0

        log.info(
            f"  ✓ Saved to {track_name}.jsonl | "
            f"Total: {total_generated} | "
            f"Rate: {rate:.1f}/hr | "
            f"Tokens: {total_input_tokens+total_output_tokens:,} | "
            f"Cost: ${total_cost:.4f}"
        )

        # ---- PERIODIC STATS ----
        if total_generated % 10 == 0:
            stats = {
                "timestamp": now.isoformat(),
                "total_generated": total_generated,
                "total_failures": total_failures,
                "total_duplicates": total_duplicates,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cost_usd": round(total_cost, 4),
                "elapsed_hours": round(elapsed / 3600, 2),
                "rate_per_hour": round(rate, 1),
                "is_free_period": is_within_free_period(),
                "per_track": {},
            }
            for tn in TRACKS:
                fpath = output_files[tn]
                if fpath.exists():
                    lines = len(fpath.read_text(encoding="utf-8").splitlines())
                    stats["per_track"][tn] = lines
            with open(stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(stats) + "\n")
            log.info(f"  📊 Stats checkpoint saved ({total_generated} total, ${total_cost:.4f})")

        # ---- RATE LIMIT ----
        time.sleep(min_interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Ralph Wiggum Loop — Burn free Gemma 4 compute for synthetic data generation"
    )
    p.add_argument("--model", default="gemma-4-26b-a4b-it",
                    help="Model name (default: gemma-4-26b-a4b-it)")
    p.add_argument("--location", default="us-central1",
                    help="Vertex AI location (default: us-central1)")
    p.add_argument("--project", default=None,
                    help="GCP project ID (overrides GOOGLE_CLOUD_PROJECT env var)")
    p.add_argument("--output", default=str(PROJECT_ROOT / "datasets" / "synth"),
                    help="Output directory for generated JSONL files")
    p.add_argument("--max-rpm", type=int, default=30,
                    help="Max requests per minute (default: 30)")
    p.add_argument("--dry-run", action="store_true",
                    help="Print sample prompts without calling API")
    args = p.parse_args()
    run_loop(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Jemma Multi-Stream Synthetic Dataset Generator
===============================================

Runs multiple parallel generation streams across FREE Google AI models to build
comprehensive construction-domain datasets for the Gemma 4 Good Hackathon.

Streams target Illinois State University, Chicago construction, and broad
structural engineering domains. Each stream produces strict JSON in a schema
optimized for its data type.

Truly free models (zero cost until Apr 16 2026):
  - gemma-4-26b-a4b-it     (Gemma 4 26B — primary)
  - gemma-4-31b-it          (Gemma 4 31B — bigger, slower)

NOTE: Gemini Flash/Flash-Lite models have free-tier QUOTAS that bill
once exceeded. They were removed after a billing overage incident.

Usage:
    $env:GOOGLE_API_KEY = "your-key"
    python toolbox/synth_multistream.py
    python toolbox/synth_multistream.py --streams 3 --rpm-per-stream 10
    python toolbox/synth_multistream.py --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
import random
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
SYNTH_DIR = DATASETS_DIR / "synth"

LOG_FMT = "%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
log = logging.getLogger("multistream")

# Auto-shutoff: 1 day before Vertex AI free period ends
FREE_CUTOFF_UTC = datetime(2026, 4, 15, 23, 0, 0, tzinfo=timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# STREAM DEFINITIONS — each stream targets a different dataset type + model
# ─────────────────────────────────────────────────────────────────────────────

STREAMS = [
    # ── Stream 0: Construction Crack Analysis (existing Ralph Wiggum style) ──
    {
        "name": "construction_qa",
        "model": "gemma-4-26b-a4b-it",
        "description": "Expert construction Q&A — cracks, inspection, repair, codes",
        "output_file": "construction_qa.jsonl",
        "schema_description": "OpenAI chat format: messages array with user/assistant roles",
        "system_prompt": (
            "You are a senior structural engineer with 25+ years experience in "
            "the Chicago and Illinois region. You reference ACI, ASTM, OSHA, IBC, "
            "AASHTO, the Chicago Building Code, and Illinois state regulations. "
            "You provide specific measurements, code section numbers, and actionable "
            "recommendations. You always emphasize safety."
        ),
        "meta_prompt": (
            "Generate a realistic expert Q&A conversation between a field inspector "
            "or engineer and an AI construction safety assistant. Output ONLY valid JSON:\n"
            '{{"messages": [{{"role": "user", "content": "..."}}, {{"role": "assistant", "content": "..."}}]}}\n\n'
            "Topic: {topic}\n"
            "Requirements:\n"
            "- User message sounds like a real field observation with specific details\n"
            "- Assistant response is 200-500 words with code references and measurements\n"
            "- Reference Chicago/Illinois codes where relevant\n"
            "- Include severity assessment and recommended actions"
        ),
        "topics": [
            "Diagonal shear cracks in a parking garage column at Navy Pier, Chicago",
            "Post-tensioned slab cracking in a new high-rise near Willis Tower",
            "Freeze-thaw damage on exposed concrete at Illinois State University campus buildings",
            "Settlement cracks in foundations along Lake Michigan shoreline (Chicago)",
            "ASR reaction in concrete pavements on Illinois interstate highways",
            "Corrosion-induced spalling on a Chicago Transit Authority elevated station",
            "Thermal cracking in mass concrete pour for Wacker Drive infrastructure",
            "Evaluating crack width limits per Chicago Building Code Chapter 19",
            "OSHA scaffold safety inspection on a Chicago Loop construction site",
            "Fire damage assessment of reinforced concrete in a Chicago warehouse fire",
            "Seismic joint detailing for a new hospital in southern Illinois earthquake zone",
            "Concrete deterioration at ISU Watterson Towers exterior walls",
            "Crack monitoring on the Michigan Avenue Bridge approach spans",
            "Evaluating shotcrete tunnel lining cracks in Chicago deep tunnel project",
            "Frost heave damage to concrete sidewalks on ISU Normal campus",
            "Distress patterns in precast concrete elements at McCormick Place expansion",
            "Chloride-induced corrosion in Chicago parking structure below street level",
            "University dormitory concrete assessment per ACI 562 at ISU",
            "Post-flooding structural assessment of buildings in Chicago River flood zone",
            "Concrete pavement D-cracking on Illinois Route 66 historic sections",
            "High-strength concrete QC issues at a Chicago supertall construction site",
            "Evaluating existing load capacity of repurposed industrial buildings in Bloomington IL",
            "Cold weather concreting challenges during Illinois January pour",
            "Fatigue crack assessment in steel-reinforced concrete bridge deck on I-55 near Normal",
            "Tilt-up wall panel crack assessment at ISU athletic facility",
        ],
    },

    # ── Stream 1: Image Description Pairs (construction scenes) ──
    {
        "name": "image_descriptions",
        "model": "gemma-4-31b-it",
        "description": "Synthetic image-caption pairs for construction object detection training",
        "output_file": "image_descriptions.jsonl",
        "schema_description": "Image description schema with objects, bounding regions, and captions",
        "system_prompt": (
            "You are a computer vision annotation expert specializing in construction "
            "site imagery. You generate extremely detailed image descriptions that could "
            "be used to train object detection and image understanding models. Your "
            "descriptions include spatial relationships, object materials, conditions, "
            "and anomalies visible in construction scenes."
        ),
        "meta_prompt": (
            "Generate a synthetic construction site image description with detailed "
            "object annotations. Output ONLY valid JSON:\n"
            '{{"image_description": {{"scene": "...", "location_context": "...", '
            '"weather_lighting": "...", "objects": [{{"label": "...", "region": "...", '
            '"condition": "...", "material": "...", "notes": "..."}}], '
            '"anomalies": [{{"type": "...", "severity": "...", "location_in_scene": "...", '
            '"description": "..."}}], "safety_observations": ["..."], '
            '"caption_short": "...", "caption_detailed": "..."}}}}\n\n'
            "Scene type: {topic}\n"
            "Requirements:\n"
            "- 5-15 labeled objects per scene with spatial region descriptions\n"
            "- Include construction equipment, materials, structural elements, workers, PPE\n"
            "- Note any visible defects, cracks, rust, damage, or safety hazards\n"
            "- Short caption (1 sentence) and detailed caption (3-5 sentences)\n"
            "- Reference Chicago/Illinois construction contexts"
        ),
        "topics": [
            "Aerial view of a high-rise steel frame construction site in Chicago Loop",
            "Close-up of concrete crack patterns on an Illinois highway bridge pier",
            "Workers installing rebar in a foundation form on ISU campus expansion project",
            "Concrete pump truck pouring floor slab on a mid-rise Chicago residential project",
            "Demolition of a concrete parking structure in downtown Chicago, exposing rebar",
            "Scaffold system on exterior of a brick building renovation in Bloomington IL",
            "Excavation with sheet pile shoring near Chicago River for new foundation",
            "Crane lifting precast concrete panel at ISU new science building",
            "Road construction resurfacing on an Illinois state highway with exposed base",
            "Interior of a gutted Chicago warehouse being converted to apartments",
            "Concrete column with visible corrosion staining and spalling in a CTA station",
            "Rooftop mechanical system installation on a Chicago commercial building",
            "Bridge deck replacement on I-55 near Normal with exposed deteriorated concrete",
            "Concrete masonry unit wall construction at an ISU dormitory addition",
            "Winter concrete pour with insulation blankets on a Chicago jobsite",
            "Fire-damaged concrete beam in a Chicago industrial building post-inspection",
            "Underground utility trench with concrete pipe installation in Illinois suburb",
            "Load testing setup on a repaired concrete floor slab in Chicago warehouse",
            "Steel beam connection with bolts at a multi-story Chicago office building",
            "Waterproofing membrane application on below-grade Chicago basement wall",
            "Traffic control setup during Illinois highway concrete pavement repair",
            "Exposed aggregate finish sidewalk installation at ISU quad renovation",
            "Formwork for a curved concrete wall on a Chicago cultural building project",
            "Drone inspection view of flat roof showing ponding water and cracks",
            "Material laydown yard with stacked precast elements at a suburban jobsite",
        ],
    },

    # ── Stream 2: Blueprint/Drawing Interpretation ──
    {
        "name": "blueprint_interpretation",
        "model": "gemma-4-26b-a4b-it",
        "description": "Blueprint reading Q&A — plan interpretation, symbols, specs",
        "output_file": "blueprint_interpretation.jsonl",
        "schema_description": "Blueprint interpretation training pairs",
        "system_prompt": (
            "You are a construction document specialist with expertise in reading "
            "architectural drawings, structural plans, MEP plans, and construction "
            "specifications. You can interpret plan symbols, abbreviations, detail "
            "callouts, and cross-references per AIA/CSI standards. You work primarily "
            "on Chicago and Illinois projects."
        ),
        "meta_prompt": (
            "Generate a training pair where a user asks about a specific construction "
            "drawing element and the expert explains it. Output ONLY valid JSON:\n"
            '{{"drawing_type": "...", "sheet_reference": "...", '
            '"element_described": "...", '
            '"conversation": [{{"role": "user", "content": "..."}}, '
            '{{"role": "assistant", "content": "..."}}], '
            '"symbols_referenced": ["..."], "codes_referenced": ["..."], '
            '"difficulty_level": "beginner|intermediate|advanced"}}\n\n'
            "Drawing context: {topic}\n"
            "Requirements:\n"
            "- User asks a specific question a junior engineer or builder might ask\n"
            "- Expert explains the drawing element, cross-references, and field implications\n"
            "- Include relevant symbols, abbreviations, and where to find related details\n"
            "- Reference AIA drawing standards and Chicago/Illinois code requirements"
        ),
        "topics": [
            "Reading a structural foundation plan for a Chicago high-rise — pile cap details",
            "Interpreting concrete reinforcement schedule on a beam detail sheet",
            "Understanding fire rating assemblies on a partition schedule per Chicago code",
            "Reading MEP coordination drawings for a hospital in Springfield IL",
            "Interpreting a precast concrete erection plan for ISU new building",
            "Understanding curtain wall detail sections on a Chicago lakefront tower",
            "Reading a shoring and excavation support plan per Chicago DOB requirements",
            "Interpreting concrete mix design specifications in project manual Section 03 30 00",
            "Understanding steel connection details W-shape beam-to-column moment connection",
            "Reading a site grading and drainage plan for Illinois commercial project",
            "Interpreting a waterproofing detail at foundation-to-wall transition",
            "Understanding a post-tensioning tendon layout plan for a parking deck",
            "Reading roof framing plan with steel joist and deck specifications",
            "Interpreting window and door schedule with Chicago energy code U-values",
            "Understanding a concrete masonry control joint detail and spacing plan",
            "Reading a temporary traffic control plan for Illinois highway work zone",
            "Interpreting a floor flatness specification FF/FL values on a warehouse plan",
            "Understanding phased construction sequence drawings for occupied building renovation",
            "Reading ADA accessibility details on an ISU campus building entrance plan",
            "Interpreting a geotechnical boring log referenced in foundation design",
        ],
    },

    # ── Stream 3: Safety Inspection Checklists & Reports ──
    {
        "name": "safety_inspections",
        "model": "gemma-4-31b-it",
        "description": "Safety inspection reports, checklists, violation citations",
        "output_file": "safety_inspections.jsonl",
        "schema_description": "Structured safety inspection report format",
        "system_prompt": (
            "You are an OSHA compliance officer and construction safety specialist "
            "with deep knowledge of OSHA 29 CFR 1926 standards, Illinois state "
            "construction safety laws (820 ILCS), and Chicago Department of Buildings "
            "safety requirements. You write detailed, realistic inspection reports."
        ),
        "meta_prompt": (
            "Generate a realistic construction safety inspection report. "
            "Output ONLY valid JSON:\n"
            '{{"inspection_report": {{"site_name": "...", "location": "...", '
            '"date": "2026-XX-XX", "inspector": "...", "weather": "...", '
            '"project_type": "...", "contractor": "...", '
            '"findings": [{{"category": "...", "osha_standard": "...", '
            '"observation": "...", "severity": "serious|willful|other_than_serious|repeat", '
            '"corrective_action": "...", "abatement_deadline": "..."}}], '
            '"compliant_items": ["..."], '
            '"overall_rating": "satisfactory|needs_improvement|stop_work", '
            '"follow_up_required": true|false, '
            '"inspector_notes": "..."}}}}\n\n'
            "Inspection scenario: {topic}\n"
            "Requirements:\n"
            "- 3-8 findings per report, mix of compliant and non-compliant\n"
            "- Cite specific OSHA 1926 subpart and section numbers\n"
            "- Include realistic contractor and site names in Illinois/Chicago area\n"
            "- Severity must match the actual OSHA violation classification criteria"
        ),
        "topics": [
            "High-rise concrete construction in Chicago Loop — fall protection focus",
            "Residential subdivision excavation work in Normal IL — trench safety",
            "ISU campus building renovation — asbestos and lead paint abatement",
            "Bridge rehabilitation on I-74 over Illinois River — traffic safety",
            "Chicago CTA station platform repair — electrical and crowd safety",
            "Steel erection on a new Chicago commercial building — ironworker safety",
            "Underground utility installation in suburban Chicago — confined space",
            "Concrete demolition on a brownfield site in East St Louis IL",
            "Crane operation inspection at McCormick Place expansion project",
            "Roofing replacement on a Chicago public school — hot work safety",
            "Road construction night shift on I-55 near Bloomington — lighting/visibility",
            "Scaffold inspection on a Chicago historic building facade restoration",
            "Concrete formwork shoring inspection prior to elevated slab pour",
            "ISU athletics facility addition — structural steel and welding safety",
            "Winter construction safety audit on a Chicago residential tower project",
            "Environmental compliance inspection at Chicago riverfront construction",
            "Material handling and storage inspection at a large Illinois warehouse build",
            "Temporary electrical installation inspection on an Illinois hospital project",
        ],
    },

    # ── Stream 4: Object Detection Training Labels ──
    {
        "name": "object_detection_labels",
        "model": "gemma-4-26b-a4b-it",
        "description": "Construction object detection label sets with class hierarchies",
        "output_file": "object_detection_labels.jsonl",
        "schema_description": "Object detection annotation format with hierarchical labels",
        "system_prompt": (
            "You are a machine learning data engineer specializing in construction "
            "site computer vision datasets. You generate precise object detection "
            "annotations with hierarchical label taxonomies, bounding box descriptions, "
            "and contextual attributes for training YOLO/DETR/SAM models."
        ),
        "meta_prompt": (
            "Generate a synthetic object detection annotation for a construction scene. "
            "Output ONLY valid JSON:\n"
            '{{"scene_id": "...", "scene_type": "...", '
            '"image_metadata": {{"width": 1920, "height": 1080, "source": "synthetic"}}, '
            '"annotations": [{{"id": N, "category": "...", "supercategory": "...", '
            '"bbox_description": "...", "relative_position": "...", '
            '"attributes": {{"material": "...", "color": "...", "condition": "...", '
            '"size_estimate": "...", "is_damaged": false}}, '
            '"occlusion": "none|partial|heavy"}}], '
            '"scene_tags": ["..."], "difficulty": "easy|medium|hard"}}\n\n'
            "Scene: {topic}\n"
            "Requirements:\n"
            "- 8-20 annotated objects per scene\n"
            "- Use a consistent category taxonomy: equipment, material, structure, "
            "person, PPE, vehicle, tool, defect, signage\n"
            "- Include realistic spatial relationships (left of, above, adjacent to)\n"
            "- Mark damage/defect objects specifically with condition details"
        ),
        "topics": [
            "Active concrete pour with pump truck, workers, vibrators, forms on a Chicago site",
            "Steel erection with crane, ironworkers, beams, bolts on a mid-rise building",
            "Excavation site with backhoe, dump truck, shoring, workers in trench",
            "Scaffolded building facade with masons, mortar, brick, safety net in Chicago",
            "Flatwork crew finishing concrete slab with bull float, edger, knee boards",
            "Highway construction zone with barrel signs, paver, roller, flaggers in Illinois",
            "Rooftop scene with HVAC units, ductwork, workers, fall protection anchors",
            "Interior demolition with jackhammer, debris, dust suppression, respirators",
            "Material storage yard with rebar bundles, lumber stacks, concrete blocks, forklift",
            "Bridge construction with form traveler, rebar cage, workers over water",
            "Welding station with welder, gas cylinders, welding curtain, sparks, PPE",
            "Tower crane scene with operator cab, hook block, rigging, load, signal person",
            "Underground parking construction with waterproofing, drainage mat, rebar",
            "Concrete batch plant with mixer trucks, conveyors, silos, testing lab",
            "ISU campus construction showing students walking past active jobsite fencing",
            "Chicago winter construction with heated enclosure, propane heaters, blankets",
            "Quality testing scene with slump cone, air meter, cylinder molds, technician",
            "Finished concrete surface showing crack patterns, efflorescence, scaling",
        ],
    },

    # ── Stream 5: Building Code Q&A (Chicago + Illinois specific) ──
    {
        "name": "building_codes",
        "model": "gemma-4-31b-it",
        "description": "Chicago and Illinois building code interpretation Q&A",
        "output_file": "building_codes.jsonl",
        "schema_description": "Code interpretation conversation with references",
        "system_prompt": (
            "You are a building code expert specializing in the Chicago Building Code "
            "(Title 14B), Illinois State Building Code, IBC 2021, ACI 318-19, and "
            "IECC 2021. You help engineers and contractors interpret code requirements "
            "for real Chicago and Illinois construction projects."
        ),
        "meta_prompt": (
            "Generate a building code interpretation Q&A. Output ONLY valid JSON:\n"
            '{{"code_qa": {{"jurisdiction": "...", "code_reference": "...", '
            '"topic": "...", '
            '"conversation": [{{"role": "user", "content": "..."}}, '
            '{{"role": "assistant", "content": "..."}}], '
            '"applicable_codes": [{{"code": "...", "section": "...", "requirement": "..."}}], '
            '"practical_implications": "...", '
            '"common_mistakes": ["..."]}}}}\n\n'
            "Code topic: {topic}\n"
            "Requirements:\n"
            "- Reference specific code sections with numbers\n"
            "- Include the practical field implication of the requirement\n"
            "- Note common errors contractors make with this code provision\n"
            "- Chicago-specific amendments where they differ from IBC"
        ),
        "topics": [
            "Chicago fire resistance requirements for Type I construction high-rise",
            "Illinois energy code compliance for new commercial building envelope",
            "Chicago DOB permit requirements for structural concrete work over 4 stories",
            "ACI 318-19 seismic detailing for special moment frames in Illinois zones",
            "Chicago code requirements for construction site public safety fencing",
            "Illinois accessibility code (IAC) requirements vs ADA for university buildings",
            "Chicago high-rise life safety system requirements per Title 14B",
            "Concrete strength testing requirements per Chicago amendment to IBC 1905",
            "Illinois state plumbing code requirements for commercial construction",
            "Chicago wind load requirements for temporary construction structures",
            "Fireproofing inspection requirements for structural steel in Chicago",
            "Illinois environmental regulations for construction stormwater management",
            "Chicago DOB requirements for crane permits and load path analysis",
            "Code requirements for historic building renovation in Chicago Landmark zone",
            "ISU campus building code — state-owned building code applicability",
            "Chicago below-grade waterproofing requirements per municipal code",
            "Illinois workers compensation construction class codes and requirements",
            "Code interpretation for mixed-use concrete building in Chicago zoning district",
        ],
    },

    # ── Stream 6: Disaster Assessment & Emergency Response ──
    {
        "name": "disaster_assessment",
        "model": "gemma-4-26b-a4b-it",
        "description": "Post-disaster structural assessment and rapid evaluation",
        "output_file": "disaster_assessment.jsonl",
        "schema_description": "Disaster assessment report with structural evaluation",
        "system_prompt": (
            "You are a post-disaster structural assessment specialist certified in "
            "ATC-20 and FEMA procedures. You have experience assessing buildings in "
            "the Midwest US after tornadoes, floods, and severe weather. You work "
            "with Illinois Emergency Management Agency (IEMA) protocols."
        ),
        "meta_prompt": (
            "Generate a post-disaster building assessment report. Output ONLY valid JSON:\n"
            '{{"assessment": {{"event_type": "...", "event_date": "2026-XX-XX", '
            '"location": "...", "building_type": "...", "construction_type": "...", '
            '"stories": N, "year_built": YYYY, '
            '"structural_evaluation": {{"foundation": "...", "superstructure": "...", '
            '"lateral_system": "...", "roof": "...", "nonstructural": "..."}}, '
            '"damage_classification": "none|slight|moderate|heavy|destroyed", '
            '"placard": "green_inspected|yellow_restricted|red_unsafe", '
            '"safety_concerns": ["..."], '
            '"recommended_actions": ["..."], '
            '"estimated_repair_scope": "...", '
            '"photos_needed": ["..."]}}}}\n\n'
            "Disaster scenario: {topic}\n"
            "Requirements:\n"
            "- Realistic for Illinois/Chicago/Midwest conditions\n"
            "- Reference ATC-20, FEMA P-154, and IEMA procedures\n"
            "- Include specific structural observations, not generic statements\n"
            "- Recommended actions must be prioritized and actionable"
        ),
        "topics": [
            "EF3 tornado damage to ISU campus buildings in Normal IL",
            "Chicago river flooding affecting below-grade commercial structures",
            "Severe thunderstorm wind damage to a strip mall in Bloomington IL",
            "Earthquake assessment (New Madrid zone) of unreinforced masonry in southern IL",
            "Ice storm damage to a steel-frame commercial building in central Illinois",
            "Building collapse after gas explosion in a Chicago residential neighborhood",
            "Flood damage to a concrete bridge over the Sangamon River",
            "Fire + water damage to a Chicago mid-rise mixed-use building",
            "Tornado damage to a precast concrete warehouse in Peoria IL",
            "Foundation settlement emergency at a historic building in Springfield IL",
            "Snow load collapse of a flat-roof commercial building in northern Illinois",
            "Hail damage assessment of a membrane roof and facade on ISU building",
            "Sinkhole near a building foundation in an Illinois karst region",
            "Lightning strike structural damage to a steel-framed ISU facility",
            "Post-derecho assessment of multiple buildings along an Illinois corridor",
        ],
    },

    # ── Stream 7: Construction Materials Database ──
    {
        "name": "materials_database",
        "model": "gemma-4-31b-it",
        "description": "Construction materials properties, testing, and specifications",
        "output_file": "materials_database.jsonl",
        "schema_description": "Materials data card with properties and test methods",
        "system_prompt": (
            "You are a construction materials scientist and testing laboratory director. "
            "You generate precise materials data cards with ASTM testing standards, "
            "mechanical properties, durability characteristics, and field performance data "
            "relevant to Illinois construction conditions."
        ),
        "meta_prompt": (
            "Generate a construction materials data card. Output ONLY valid JSON:\n"
            '{{"material_card": {{"name": "...", "category": "...", '
            '"subcategory": "...", "astm_standards": ["..."], '
            '"properties": {{"strength": "...", "density": "...", '
            '"durability_class": "...", "fire_rating": "...", '
            '"thermal_conductivity": "...", "service_temp_range": "..."}}, '
            '"typical_applications": ["..."], '
            '"testing_methods": [{{"test": "...", "standard": "...", '
            '"frequency": "...", "acceptance_criteria": "..."}}], '
            '"illinois_considerations": "...", '
            '"common_defects": ["..."], '
            '"sustainability_data": {{"recycled_content": "...", "embodied_carbon": "...", '
            '"leed_contribution": "..."}}}}}}\n\n'
            "Material: {topic}\n"
            "Requirements:\n"
            "- Include specific numeric property values with units\n"
            "- Reference actual ASTM standard numbers\n"
            "- Note Illinois-specific climate considerations (freeze-thaw, deicing)\n"
            "- Include sustainability/LEED data where applicable"
        ),
        "topics": [
            "Normal-weight structural concrete 4000 psi for Chicago construction",
            "High-performance concrete 8000 psi with silica fume for high-rise columns",
            "Self-consolidating concrete (SCC) for congested reinforcement applications",
            "Grade 60 deformed reinforcing steel bars per ASTM A615",
            "Structural steel W-shapes ASTM A992 for Chicago building frames",
            "Portland cement Type I/II for general Illinois construction",
            "Fly ash Class C from Illinois coal plants for concrete admixture",
            "GFRP reinforcing bars for corrosion-resistant bridge deck applications",
            "Waterproofing membrane — hot-applied rubberized asphalt",
            "Concrete masonry units (CMU) — lightweight for Illinois construction",
            "Structural wood — Southern Pine for formwork and temporary structures",
            "Epoxy injection resin for structural crack repair per ACI 503R",
            "Carbon fiber reinforced polymer (CFRP) sheets for column strengthening",
            "Geosynthetic reinforcement for mechanically stabilized earth walls",
            "Spray-applied fireproofing — SFRM cementitious for steel protection",
            "Asphalt concrete — Superpave mix for Illinois state highway overlay",
            "Precast concrete — double-tee beams for parking structure construction",
            "Stainless steel rebar for bridge deck in high-chloride environment",
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Generation engine
# ─────────────────────────────────────────────────────────────────────────────

_write_lock = threading.Lock()
_global_hashes: set = set()
_global_stats = {
    "total_generated": 0,
    "total_failures": 0,
    "total_duplicates": 0,
    "per_stream": {},
}
_stats_lock = threading.Lock()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def load_existing_hashes() -> set:
    hashes = set()
    for jsonl in DATASETS_DIR.glob("**/*.jsonl"):
        try:
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    hashes.add(content_hash(line))
        except Exception:
            pass
    return hashes


def parse_json_response(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for start_pat in ['{"messages"', '{"image_description"', '{"drawing_type"',
                       '{"inspection_report"', '{"scene_id"', '{"code_qa"',
                       '{"assessment"', '{"material_card"']:
        idx = text.find(start_pat)
        if idx >= 0:
            depth = 0
            for i in range(idx, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[idx:i+1])
                        except json.JSONDecodeError:
                            break
    return None


def generate_one(client, model: str, system_prompt: str, user_prompt: str):
    from google.genai import types
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9,
                top_p=0.95,
                max_output_tokens=4096,
            ),
        )
        return resp.text or ""
    except Exception as e:
        log.warning(f"API error on {model}: {e}")
        return None


def run_stream(stream_cfg: dict, api_key: str, rpm: int, dry_run: bool = False):
    """Run a single generation stream (called in its own thread)."""
    global _global_hashes

    from google import genai

    name = stream_cfg["name"]
    model = stream_cfg["model"]
    out_path = SYNTH_DIR / stream_cfg["output_file"]
    interval = 60.0 / rpm
    topics = stream_cfg["topics"]

    variations = [
        "Make this a single-turn exchange.",
        "Make this a 2-turn conversation with a follow-up question.",
        "Frame it as an urgent field situation.",
        "Frame it from a student or junior engineer's perspective.",
        "Include comparisons with similar but different conditions.",
        "Emphasize the Illinois/Chicago regulatory context.",
        "Include specific numeric measurements and thresholds.",
        "Frame as a training scenario for new inspectors.",
    ]

    log.info(f"[{name}] Starting — model={model}, topics={len(topics)}, rpm={rpm}")

    if dry_run:
        prompt = stream_cfg["meta_prompt"].format(topic=topics[0])
        log.info(f"[{name}] DRY RUN sample prompt ({len(prompt)} chars):\n{prompt[:300]}...")
        return

    client = genai.Client(api_key=api_key)
    generated = 0
    failures = 0
    duplicates = 0

    while True:
        # Check free period
        if datetime.now(timezone.utc) >= FREE_CUTOFF_UTC:
            log.info(f"[{name}] Free period cutoff reached. Stopping.")
            break

        topic = random.choice(topics)
        variation = random.choice(variations)
        prompt = stream_cfg["meta_prompt"].format(topic=topic) + f"\n\nStyle: {variation}"

        text = generate_one(client, model, stream_cfg["system_prompt"], prompt)

        if text is None:
            failures += 1
            time.sleep(interval * 2)
            continue

        obj = parse_json_response(text)
        if obj is None:
            failures += 1
            log.debug(f"[{name}] Parse failure on response")
            time.sleep(interval)
            continue

        # Dedup
        h = content_hash(json.dumps(obj, sort_keys=True))
        with _write_lock:
            if h in _global_hashes:
                duplicates += 1
                time.sleep(interval)
                continue
            _global_hashes.add(h)

        # Add metadata
        obj["_meta"] = {
            "stream": name,
            "model": model,
            "topic": topic,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "iteration": generated + 1,
        }

        # Write
        line = json.dumps(obj, ensure_ascii=False)
        with _write_lock:
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

        generated += 1

        with _stats_lock:
            _global_stats["total_generated"] += 1
            _global_stats["per_stream"][name] = generated

        if generated % 5 == 0:
            log.info(
                f"[{name}] gen={generated} fail={failures} dup={duplicates} "
                f"| model={model}"
            )

        time.sleep(interval)


# ─────────────────────────────────────────────────────────────────────────────
# Stats monitor thread
# ─────────────────────────────────────────────────────────────────────────────

def stats_monitor(interval_seconds: int = 60):
    stats_file = SYNTH_DIR / "multistream_stats.jsonl"
    while True:
        time.sleep(interval_seconds)
        with _stats_lock:
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **_global_stats,
            }
        with _write_lock:
            with open(stats_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot) + "\n")
        total = snapshot["total_generated"]
        per = snapshot["per_stream"]
        breakdown = " | ".join(f"{k}={v}" for k, v in sorted(per.items()))
        log.info(f"[STATS] Total={total} | {breakdown}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Jemma Multi-Stream Synthetic Dataset Generator"
    )
    p.add_argument("--streams", type=int, default=len(STREAMS),
                    help=f"Number of streams to run (max {len(STREAMS)}, default: all)")
    p.add_argument("--rpm-per-stream", type=int, default=2,
                    help="Requests per minute per stream (default: 2)")
    p.add_argument("--dry-run", action="store_true",
                    help="Show sample prompts without calling API")
    args = p.parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        log.error("Set GOOGLE_API_KEY environment variable first")
        sys.exit(1)

    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing hashes for dedup
    global _global_hashes
    _global_hashes = load_existing_hashes()
    log.info(f"Loaded {len(_global_hashes)} existing hashes for dedup")

    active_streams = STREAMS[:args.streams]

    log.info("=" * 70)
    log.info("JEMMA MULTI-STREAM SYNTHETIC DATA GENERATOR")
    log.info(f"  Active streams: {len(active_streams)}")
    log.info(f"  RPM per stream: {args.rpm_per_stream}")
    log.info(f"  Total RPM across all streams: {len(active_streams) * args.rpm_per_stream}")
    log.info(f"  Free period cutoff: {FREE_CUTOFF_UTC.isoformat()}")
    log.info(f"  Output: {SYNTH_DIR}")
    for s in active_streams:
        log.info(f"    [{s['name']}] model={s['model']} topics={len(s['topics'])}")
    log.info("=" * 70)

    if args.dry_run:
        for s in active_streams:
            run_stream(s, api_key, args.rpm_per_stream, dry_run=True)
        return

    # Start stats monitor daemon
    stats_thread = threading.Thread(target=stats_monitor, args=(60,), daemon=True)
    stats_thread.start()

    # Launch all streams in parallel threads
    with ThreadPoolExecutor(max_workers=len(active_streams),
                            thread_name_prefix="stream") as pool:
        futures = {
            pool.submit(run_stream, s, api_key, args.rpm_per_stream): s["name"]
            for s in active_streams
        }
        try:
            for f in as_completed(futures):
                name = futures[f]
                try:
                    f.result()
                except Exception as e:
                    log.error(f"Stream {name} crashed: {e}")
        except KeyboardInterrupt:
            log.info("Ctrl+C received — shutting down all streams...")


if __name__ == "__main__":
    main()

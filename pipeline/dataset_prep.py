#!/usr/bin/env python3
"""
Jemma Dataset Preparation — Download, filter, and format Kaggle/HF datasets.

Downloads license-clean datasets and converts them to Gemma 4 chat-template
JSONL format for Unsloth SFT and DPO training.

Usage:
  python pipeline/dataset_prep.py --stage general   # UltraChat + OpenHermes
  python pipeline/dataset_prep.py --stage domain     # OSHA + FEMA + NOAA
  python pipeline/dataset_prep.py --stage toolcall   # Glaive Function Calling
  python pipeline/dataset_prep.py --stage dpo        # HelpSteer2 + UltraFeedback + Capybara
  python pipeline/dataset_prep.py --stage safety     # Real Toxicity → refusals
  python pipeline/dataset_prep.py --stage all        # Everything
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREPARED_DIR = ROOT / "datasets" / "prepared"
PREPARED_DIR.mkdir(parents=True, exist_ok=True)

log = logging.getLogger("dataset_prep")
log.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
log.addHandler(_sh)

# ---------------------------------------------------------------------------
# HuggingFace dataset loading helper
# ---------------------------------------------------------------------------

def load_hf_dataset(repo: str, *, split: str = "train", subset: str | None = None):
    """Load a HuggingFace dataset with lazy import."""
    from datasets import load_dataset
    kwargs: dict = {"split": split}
    if subset:
        kwargs["name"] = subset
    log.info(f"Loading {repo} (split={split}, subset={subset})...")
    ds = load_dataset(repo, **kwargs)
    log.info(f"  Loaded {len(ds)} rows")
    return ds


def save_jsonl(data: list[dict], path: Path, label: str):
    """Save a list of dicts as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    log.info(f"  Saved {len(data)} examples to {path.name} ({label})")


def sample_and_shuffle(data: list, n: int, seed: int = 42) -> list:
    """Deterministic sample and shuffle."""
    rng = random.Random(seed)
    if len(data) > n:
        data = rng.sample(data, n)
    rng.shuffle(data)
    return data


# ---------------------------------------------------------------------------
# Stage 1: General SFT — UltraChat + OpenHermes
# ---------------------------------------------------------------------------
GENERAL_TARGET = 35_000  # 20K UltraChat + 15K OpenHermes


def prep_general():
    """Download and format UltraChat 200K + OpenHermes 2.5."""
    out_path = PREPARED_DIR / "stage1_general_sft.jsonl"
    if out_path.exists():
        n = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info(f"Stage 1 already prepared: {n} examples in {out_path.name}")
        return out_path

    all_examples: list[dict] = []

    # ── UltraChat 200K (MIT) ───────────────────────────────────────────────
    log.info("=== UltraChat 200K (MIT license) ===")
    ds = load_hf_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft")
    count = 0
    for row in ds:
        messages = row.get("messages", [])
        if not messages or len(messages) < 2:
            continue
        # Filter: keep conversations with at least user + assistant
        formatted = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "").strip()
            if role in ("user", "assistant") and content:
                formatted.append({"role": role, "content": content})
        if len(formatted) >= 2 and formatted[0]["role"] == "user":
            all_examples.append({"messages": formatted, "_source": "ultrachat_200k"})
            count += 1
            if count >= 20_000:
                break
    log.info(f"  UltraChat: {count} examples")

    # ── OpenHermes 2.5 (Apache 2.0) ──────────────────────────────────────
    log.info("=== OpenHermes 2.5 (Apache 2.0 license) ===")
    ds = load_hf_dataset("teknium/OpenHermes-2.5", split="train")
    count = 0
    for row in ds:
        convos = row.get("conversations", [])
        if not convos or len(convos) < 2:
            continue
        formatted = []
        for m in convos:
            role_map = {"human": "user", "gpt": "assistant", "system": "system"}
            role = role_map.get(m.get("from", ""), "")
            content = m.get("value", "").strip()
            if role and content:
                formatted.append({"role": role, "content": content})
        if len(formatted) >= 2:
            all_examples.append({"messages": formatted, "_source": "openhermes_2.5"})
            count += 1
            if count >= 15_000:
                break
    log.info(f"  OpenHermes: {count} examples")

    all_examples = sample_and_shuffle(all_examples, GENERAL_TARGET)
    save_jsonl(all_examples, out_path, "Stage 1 General SFT")
    return out_path


# ---------------------------------------------------------------------------
# Stage 2: Domain SFT — OSHA + FEMA + NOAA + existing synth
# ---------------------------------------------------------------------------
DOMAIN_TARGET = 30_000


def prep_domain():
    """Prepare domain-specific datasets for construction safety focus."""
    out_path = PREPARED_DIR / "stage2_domain_sft.jsonl"
    if out_path.exists():
        n = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info(f"Stage 2 already prepared: {n} examples in {out_path.name}")
        return out_path

    all_examples: list[dict] = []

    # ── OSHA Accident Data (CC0) ──────────────────────────────────────────
    log.info("=== OSHA Accident Data (CC0 — Public Domain) ===")
    try:
        # Try Kaggle download via datasets library or local file
        osha_path = ROOT / "datasets" / "external" / "osha"
        osha_path.mkdir(parents=True, exist_ok=True)

        # Try HuggingFace version first
        try:
            ds = load_hf_dataset("ruqaiyaship/osha-accident-and-inspection-data", split="train")
            count = 0
            for row in ds:
                narrative = (row.get("Abstract", "") or row.get("abstract", "") or "").strip()
                if len(narrative) < 50:
                    continue
                event_type = row.get("EventType", row.get("event_type", "workplace accident"))
                sic = row.get("SIC", row.get("sic", ""))

                messages = [
                    {"role": "user", "content": f"Assess the following workplace safety incident: {narrative[:200]}..."},
                    {"role": "assistant", "content": (
                        f"**OSHA Incident Assessment**\n\n"
                        f"**Event Type**: {event_type}\n"
                        f"**Industry Code (SIC)**: {sic}\n\n"
                        f"**Narrative**: {narrative}\n\n"
                        f"**Safety Recommendations**: Based on this incident, employers should review "
                        f"relevant OSHA standards, conduct a job hazard analysis (JHA), and implement "
                        f"appropriate engineering controls, administrative controls, and PPE requirements."
                    )},
                ]
                all_examples.append({"messages": messages, "_source": "osha_accidents"})
                count += 1
                if count >= 10_000:
                    break
            log.info(f"  OSHA: {count} examples")
        except Exception as e:
            log.warning(f"  OSHA dataset not available: {e}")
            log.info("  Download manually: kaggle datasets download -d ruqaiyaship/osha-accident-and-inspection-data")
    except Exception as e:
        log.warning(f"  OSHA prep failed: {e}")

    # ── FEMA Public Assistance (CC0) ──────────────────────────────────────
    log.info("=== FEMA Public Assistance Projects (CC0) ===")
    try:
        try:
            ds = load_hf_dataset("fema/public-assistance-funded-projects-details", split="train")
        except Exception:
            # Try alternative name
            ds = None
            log.warning("  FEMA dataset not on HF. Trying local/Kaggle...")

        if ds:
            count = 0
            for row in ds:
                desc = (row.get("projectDescription", "") or row.get("title", "") or "").strip()
                disaster = (row.get("disasterNumber", "") or "")
                damage_cat = (row.get("damageCategory", "") or "")
                cost = row.get("federalShareObligated", 0)

                if len(desc) < 30:
                    continue

                messages = [
                    {"role": "user", "content": f"Describe the emergency response project: {desc[:150]}"},
                    {"role": "assistant", "content": (
                        f"**FEMA Project Assessment**\n\n"
                        f"**Disaster Number**: {disaster}\n"
                        f"**Damage Category**: {damage_cat}\n"
                        f"**Project**: {desc}\n"
                        f"**Federal Cost**: ${cost:,.2f}\n\n"
                        f"This project involves emergency response and recovery operations "
                        f"managed through FEMA Public Assistance programs."
                    )},
                ]
                all_examples.append({"messages": messages, "_source": "fema_pa"})
                count += 1
                if count >= 10_000:
                    break
            log.info(f"  FEMA: {count} examples")
    except Exception as e:
        log.warning(f"  FEMA prep failed: {e}")

    # ── Repurpose existing synth data (building_codes, construction_qa) ──
    log.info("=== Repurposing existing synth datasets ===")
    synth_dir = ROOT / "datasets" / "synth"
    for fname in ["building_codes.jsonl", "construction_qa.jsonl", "safety_inspections.jsonl",
                   "disaster_assessment.jsonl"]:
        fpath = synth_dir / fname
        if not fpath.exists():
            continue
        count = 0
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip stats entries
                if "total_generated" in obj or "_meta" not in obj:
                    continue

                # Extract messages from various formats
                messages = _extract_messages_from_synth(obj)
                if messages and len(messages) >= 2:
                    all_examples.append({"messages": messages, "_source": f"synth_{fname}"})
                    count += 1
        log.info(f"  {fname}: {count} examples repurposed")

    all_examples = sample_and_shuffle(all_examples, DOMAIN_TARGET)
    save_jsonl(all_examples, out_path, "Stage 2 Domain SFT")
    return out_path


def _extract_messages_from_synth(obj: dict) -> list[dict]:
    """Extract chat messages from various synth dataset formats."""
    # Format 1: messages array (construction_qa)
    if "messages" in obj:
        return [{"role": m["role"], "content": m["content"]}
                for m in obj["messages"] if m.get("role") in ("user", "assistant")]

    # Format 2: code_qa with conversation (building_codes)
    if "code_qa" in obj:
        qa = obj["code_qa"]
        convos = qa.get("conversation", [])
        if convos:
            return [{"role": m["role"], "content": m["content"]} for m in convos]

    # Format 3: Structured assessment (disaster_assessment, safety_inspections)
    meta = obj.get("_meta", {})
    stream = meta.get("stream", "")
    if stream == "disaster_assessment":
        loc = obj.get("location", {})
        return [
            {"role": "user", "content": f"Assess disaster damage at {loc.get('address', 'the site')}: {obj.get('event_type', 'unknown event')}"},
            {"role": "assistant", "content": json.dumps(obj, indent=2, ensure_ascii=False)[:2000]},
        ]
    if stream == "safety_inspections":
        site = obj.get("site_name", "construction site")
        return [
            {"role": "user", "content": f"Provide the safety inspection report for {site}"},
            {"role": "assistant", "content": json.dumps(obj, indent=2, ensure_ascii=False)[:2000]},
        ]

    return []


# ---------------------------------------------------------------------------
# Stage 3: Tool Calling SFT — Glaive Function Calling
# ---------------------------------------------------------------------------
TOOLCALL_TARGET = 15_000


def prep_toolcall():
    """Download and format Glaive Function Calling v2 (Apache 2.0)."""
    out_path = PREPARED_DIR / "stage3_toolcall_sft.jsonl"
    if out_path.exists():
        n = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info(f"Stage 3 already prepared: {n} examples in {out_path.name}")
        return out_path

    all_examples: list[dict] = []

    log.info("=== Glaive Function Calling v2 (Apache 2.0) ===")
    ds = load_hf_dataset("glaiveai/glaive-function-calling-v2", split="train")

    count = 0
    for row in ds:
        # Glaive format: system_prompt, chat (ShareGPT-style text)
        system = (row.get("system", "") or "").strip()
        chat_text = (row.get("chat", "") or "").strip()

        if not chat_text:
            continue

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Parse the chat text — Glaive uses "USER: ... ASSISTANT: ... FUNCTION RESPONSE: ..."
        parts = chat_text.split("\n")
        current_role = None
        current_content: list[str] = []

        for part in parts:
            stripped = part.strip()
            if stripped.startswith("USER:"):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                current_role = "user"
                current_content = [stripped[5:].strip()]
            elif stripped.startswith("ASSISTANT:"):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                current_role = "assistant"
                current_content = [stripped[10:].strip()]
            elif stripped.startswith("FUNCTION RESPONSE:"):
                if current_role and current_content:
                    messages.append({"role": current_role, "content": "\n".join(current_content).strip()})
                current_role = "tool"
                current_content = [stripped[18:].strip()]
            elif current_role:
                current_content.append(part)

        if current_role and current_content:
            messages.append({"role": current_role, "content": "\n".join(current_content).strip()})

        if len(messages) >= 2:
            all_examples.append({"messages": messages, "_source": "glaive_function_calling_v2"})
            count += 1
            if count >= TOOLCALL_TARGET:
                break

    log.info(f"  Glaive: {count} examples")
    all_examples = sample_and_shuffle(all_examples, TOOLCALL_TARGET)
    save_jsonl(all_examples, out_path, "Stage 3 Tool Calling SFT")
    return out_path


# ---------------------------------------------------------------------------
# Stage 4: DPO — HelpSteer2 + UltraFeedback + Capybara
# ---------------------------------------------------------------------------
DPO_TARGET = 40_000


def prep_dpo():
    """Download and format DPO preference datasets."""
    out_path = PREPARED_DIR / "stage4_dpo.jsonl"
    if out_path.exists():
        n = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info(f"Stage 4 already prepared: {n} examples in {out_path.name}")
        return out_path

    all_examples: list[dict] = []

    # ── UltraFeedback Binarized (MIT) ─────────────────────────────────────
    log.info("=== UltraFeedback Binarized (MIT license) ===")
    try:
        ds = load_hf_dataset("HuggingFaceH4/ultrafeedback_binarized", split="train_prefs")
        count = 0
        for row in ds:
            chosen = row.get("chosen", [])
            rejected = row.get("rejected", [])
            if not chosen or not rejected:
                continue

            all_examples.append({
                "chosen": chosen,
                "rejected": rejected,
                "_source": "ultrafeedback_binarized",
            })
            count += 1
            if count >= 15_000:
                break
        log.info(f"  UltraFeedback: {count} preference pairs")
    except Exception as e:
        log.warning(f"  UltraFeedback load failed: {e}")

    # ── Capybara DPO (Apache 2.0) ────────────────────────────────────────
    log.info("=== Distilabel Capybara DPO (Apache 2.0) ===")
    try:
        ds = load_hf_dataset("argilla/distilabel-capybara-dpo-7k-binarized", split="train")
        count = 0
        for row in ds:
            chosen = row.get("chosen", [])
            rejected = row.get("rejected", [])
            if not chosen or not rejected:
                continue

            all_examples.append({
                "chosen": chosen,
                "rejected": rejected,
                "_source": "capybara_dpo",
            })
            count += 1
        log.info(f"  Capybara DPO: {count} preference pairs")
    except Exception as e:
        log.warning(f"  Capybara load failed: {e}")

    # ── HelpSteer2 (CC-BY-4.0) ───────────────────────────────────────────
    log.info("=== HelpSteer2 (CC-BY-4.0) ===")
    try:
        ds = load_hf_dataset("nvidia/HelpSteer2", split="train")
        # HelpSteer2 has prompt + response + scores; convert to preference pairs
        # Group by prompt, pick best/worst response
        from collections import defaultdict
        prompt_groups: dict[str, list] = defaultdict(list)
        for row in ds:
            prompt = (row.get("prompt", "") or "").strip()
            response = (row.get("response", "") or "").strip()
            helpfulness = row.get("helpfulness", 0)
            correctness = row.get("correctness", 0)
            if prompt and response:
                overall = (helpfulness + correctness) / 2
                prompt_groups[prompt].append({"response": response, "score": overall})

        count = 0
        for prompt, responses in prompt_groups.items():
            if len(responses) < 2:
                continue
            responses.sort(key=lambda x: x["score"], reverse=True)
            best = responses[0]
            worst = responses[-1]
            if best["score"] - worst["score"] < 0.5:
                continue  # Skip ambiguous pairs

            all_examples.append({
                "chosen": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": best["response"]},
                ],
                "rejected": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": worst["response"]},
                ],
                "_source": "helpsteer2",
            })
            count += 1
        log.info(f"  HelpSteer2: {count} preference pairs")
    except Exception as e:
        log.warning(f"  HelpSteer2 load failed: {e}")

    all_examples = sample_and_shuffle(all_examples, DPO_TARGET)
    save_jsonl(all_examples, out_path, "Stage 4 DPO")
    return out_path


# ---------------------------------------------------------------------------
# Stage 5: Safety — Real Toxicity Prompts → refusal training
# ---------------------------------------------------------------------------
SAFETY_TARGET = 5_000


def prep_safety():
    """Download Real Toxicity Prompts and generate refusal training data."""
    out_path = PREPARED_DIR / "stage5_safety_sft.jsonl"
    if out_path.exists():
        n = sum(1 for _ in open(out_path, encoding="utf-8"))
        log.info(f"Stage 5 already prepared: {n} examples in {out_path.name}")
        return out_path

    all_examples: list[dict] = []

    log.info("=== Real Toxicity Prompts (Apache 2.0) ===")
    try:
        ds = load_hf_dataset("allenai/real-toxicity-prompts", split="train")
        count = 0
        for row in ds:
            prompt_data = row.get("prompt", {})
            if isinstance(prompt_data, dict):
                text = prompt_data.get("text", "").strip()
                toxicity = prompt_data.get("toxicity", 0) or 0
            else:
                continue

            if toxicity < 0.7 or len(text) < 20:
                continue

            # Create refusal response
            messages = [
                {"role": "user", "content": text},
                {"role": "assistant", "content": (
                    "I appreciate you reaching out, but I'm unable to engage with or "
                    "continue this type of content. It contains harmful, toxic, or "
                    "inappropriate material that I'm designed to avoid.\n\n"
                    "I'm Jemma SafeBrain, focused on construction safety, civic services, "
                    "and emergency response. I'd be happy to help you with:\n"
                    "- Building code questions\n"
                    "- Safety inspection guidance\n"
                    "- Emergency response procedures\n"
                    "- Civic service information\n\n"
                    "How can I assist you with something constructive?"
                )},
            ]
            all_examples.append({"messages": messages, "_source": "real_toxicity_refusal"})
            count += 1
            if count >= SAFETY_TARGET:
                break
        log.info(f"  Toxicity refusals: {count} examples")
    except Exception as e:
        log.warning(f"  Real Toxicity Prompts load failed: {e}")

    # Also include existing safety refusals from synth
    refusal_path = ROOT / "datasets" / "synth" / "safety_refusals.jsonl"
    if refusal_path.exists():
        count = 0
        with open(refusal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "messages" in obj:
                        all_examples.append({"messages": obj["messages"], "_source": "synth_safety_refusals"})
                        count += 1
                except json.JSONDecodeError:
                    continue
        log.info(f"  Existing synth refusals: {count} examples")

    all_examples = sample_and_shuffle(all_examples, SAFETY_TARGET)
    save_jsonl(all_examples, out_path, "Stage 5 Safety SFT")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
STAGE_MAP = {
    "general": prep_general,
    "domain": prep_domain,
    "toolcall": prep_toolcall,
    "dpo": prep_dpo,
    "safety": prep_safety,
}


def main():
    parser = argparse.ArgumentParser(description="Jemma Dataset Preparation")
    parser.add_argument("--stage", type=str, default="all",
                        help="Stage to prepare: general|domain|toolcall|dpo|safety|all")
    parser.add_argument("--force", action="store_true", help="Re-download even if files exist")
    args = parser.parse_args()

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║     Jemma Dataset Preparation Pipeline       ║")
    log.info("╚══════════════════════════════════════════════╝")

    if args.force:
        log.info("Force mode: will re-download all datasets")
        for f in PREPARED_DIR.glob("*.jsonl"):
            f.unlink()

    stages = list(STAGE_MAP.keys()) if args.stage == "all" else [args.stage]

    for stage in stages:
        if stage not in STAGE_MAP:
            log.error(f"Unknown stage: {stage}. Options: {list(STAGE_MAP.keys())}")
            continue
        log.info(f"\n▶▶▶ Preparing: {stage}")
        t0 = time.time()
        try:
            result_path = STAGE_MAP[stage]()
            elapsed = time.time() - t0
            log.info(f"  ✓ {stage} done in {elapsed:.0f}s → {result_path}")
        except Exception as e:
            log.error(f"  ✗ {stage} failed: {e}")
            import traceback
            traceback.print_exc()

    log.info("\n═══ Dataset preparation complete ═══")
    # Show summary
    for f in sorted(PREPARED_DIR.glob("*.jsonl")):
        n = sum(1 for _ in open(f, encoding="utf-8"))
        size_mb = f.stat().st_size / (1024 * 1024)
        log.info(f"  {f.name}: {n:,} examples ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()

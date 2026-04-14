"""
Jemma Embed — Training Data Pipeline

Downloads, preprocesses, and converts public datasets into the
unified training format for contrastive embedding learning.

Datasets:
  Phase 1 (text): MS MARCO triplets, AllNLI pairs, civic domain pairs
  Phase 2 (multimodal): COCO Captions (image-text), AudioCaps (audio-text)

All outputs are JSONL files in datasets/embedding/.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sqlite3
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("jemma.embed.data")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EMBED_DATA_DIR = BASE_DIR / "datasets" / "embedding"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_dir() -> Path:
    EMBED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return EMBED_DATA_DIR


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _write_jsonl(path: Path, records: list[dict]) -> int:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


# ---------------------------------------------------------------------------
# Phase 1: Text datasets
# ---------------------------------------------------------------------------
def prepare_msmarco_triplets(max_samples: int = 500_000) -> Path:
    """
    Download and convert MS MARCO passage ranking triplets.
    Format: {query, positive, negative}
    """
    out_path = _ensure_dir() / "msmarco_triplets.jsonl"
    if out_path.exists() and _count_lines(out_path) >= max_samples * 0.9:
        log.info(f"MS MARCO already prepared: {_count_lines(out_path)} samples")
        return out_path

    log.info("Preparing MS MARCO triplets from HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "sentence-transformers/msmarco-bm25",
            split="train",
            streaming=True,
        )

        records = []
        for i, row in enumerate(ds):
            if i >= max_samples:
                break
            # Extract query, positive passage, negative passage
            query = row.get("query", row.get("anchor", ""))
            positive = row.get("positive", row.get("pos", [""]))[0] if isinstance(
                row.get("positive", row.get("pos", "")), list
            ) else row.get("positive", row.get("pos", ""))
            negatives = row.get("negative", row.get("neg", []))
            negative = negatives[0] if isinstance(negatives, list) and negatives else ""

            if query and positive:
                records.append({
                    "type": "triplet",
                    "query": query,
                    "positive": positive,
                    "negative": negative,
                })

            if len(records) % 50000 == 0 and len(records) > 0:
                log.info(f"  MS MARCO: {len(records):,} samples processed...")

        count = _write_jsonl(out_path, records)
        log.info(f"MS MARCO prepared: {count:,} triplets → {out_path}")
        return out_path

    except Exception as e:
        log.error(f"Failed to prepare MS MARCO: {e}")
        # Create a minimal placeholder so training can proceed
        _write_jsonl(out_path, [])
        return out_path


def prepare_allnli_pairs(max_samples: int = 275_000) -> Path:
    """
    Download and convert AllNLI (SNLI + MultiNLI) entailment pairs.
    Format: {anchor, positive} — entailment pairs only.
    """
    out_path = _ensure_dir() / "allnli_pairs.jsonl"
    if out_path.exists() and _count_lines(out_path) >= max_samples * 0.9:
        log.info(f"AllNLI already prepared: {_count_lines(out_path)} samples")
        return out_path

    log.info("Preparing AllNLI pairs from HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "sentence-transformers/all-nli",
            "pair-class",
            split="train",
            streaming=True,
        )

        records = []
        for i, row in enumerate(ds):
            if len(records) >= max_samples:
                break
            # Only keep entailment pairs (label=0 in most NLI datasets)
            label = row.get("label", -1)
            if label == 0:  # entailment
                premise = row.get("premise", row.get("anchor", ""))
                hypothesis = row.get("hypothesis", row.get("positive", ""))
                if premise and hypothesis:
                    records.append({
                        "type": "pair",
                        "anchor": premise,
                        "positive": hypothesis,
                    })

            if i % 100000 == 0 and i > 0:
                log.info(f"  AllNLI: scanned {i:,}, kept {len(records):,} entailment pairs")

        count = _write_jsonl(out_path, records)
        log.info(f"AllNLI prepared: {count:,} pairs → {out_path}")
        return out_path

    except Exception as e:
        log.error(f"Failed to prepare AllNLI: {e}")
        _write_jsonl(out_path, [])
        return out_path


def prepare_civic_pairs(
    db_path: Optional[Path] = None,
    max_samples: int = 50_000,
) -> Path:
    """
    Generate embedding training pairs from Jemma's civic RAG database.
    Uses page titles + content, dataset descriptions, contact info.
    Format: {anchor, positive}
    """
    out_path = _ensure_dir() / "civic_pairs.jsonl"
    if db_path is None:
        db_path = BASE_DIR / "datasets" / "civic_data.db"

    if not db_path.exists():
        log.warning(f"Civic DB not found at {db_path}, skipping")
        _write_jsonl(out_path, [])
        return out_path

    log.info("Generating civic embedding pairs from RAG database...")
    conn = sqlite3.connect(str(db_path))
    records = []

    # Page title → content chunk pairs
    try:
        pages = conn.execute(
            "SELECT title, content FROM pages WHERE content IS NOT NULL AND title IS NOT NULL"
        ).fetchall()
        for title, content in pages:
            if not content or not title:
                continue
            # Split content into chunks, pair each with the title
            chunks = _chunk_text(content, 512)
            for chunk in chunks[:5]:  # max 5 chunks per page
                records.append({
                    "type": "pair",
                    "anchor": title.strip(),
                    "positive": chunk.strip(),
                })
    except sqlite3.OperationalError:
        pass

    # Dataset name → description pairs
    try:
        datasets = conn.execute(
            "SELECT name, description FROM datasets WHERE description IS NOT NULL"
        ).fetchall()
        for name, desc in datasets:
            if name and desc:
                records.append({
                    "type": "pair",
                    "anchor": f"What is the {name} dataset?",
                    "positive": desc.strip(),
                })
    except sqlite3.OperationalError:
        pass

    # Contact query → contact info pairs
    try:
        contacts = conn.execute(
            "SELECT name, department, email, phone FROM contacts"
        ).fetchall()
        for name, dept, email, phone in contacts:
            info_parts = [p for p in [name, dept, email, phone] if p]
            if len(info_parts) >= 2:
                query = f"Contact information for {name or dept}"
                answer = ", ".join(info_parts)
                records.append({
                    "type": "pair",
                    "anchor": query,
                    "positive": answer,
                })
    except sqlite3.OperationalError:
        pass

    conn.close()

    random.shuffle(records)
    records = records[:max_samples]
    count = _write_jsonl(out_path, records)
    log.info(f"Civic pairs prepared: {count:,} pairs → {out_path}")
    return out_path


def _chunk_text(text: str, max_chars: int = 512) -> list[str]:
    """Simple character-level chunking with sentence boundary awareness."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end < len(text):
            # Try to break at sentence boundary
            for sep in [". ", ".\n", "\n\n", "\n", " "]:
                pos = text.rfind(sep, start, end)
                if pos > start + max_chars // 2:
                    end = pos + len(sep)
                    break
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Phase 2: Multimodal datasets
# ---------------------------------------------------------------------------
def prepare_coco_captions(max_samples: int = 118_000) -> Path:
    """
    Prepare COCO Captions dataset metadata for image-text contrastive training.
    Stores references (image URLs/paths + captions). Actual images loaded at train time.
    Format: {image_url, caption, image_id}
    """
    out_path = _ensure_dir() / "coco_captions.jsonl"
    if out_path.exists() and _count_lines(out_path) >= max_samples * 0.9:
        log.info(f"COCO Captions already prepared: {_count_lines(out_path)} samples")
        return out_path

    log.info("Preparing COCO Captions from HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "nlphuji/flickr30k",
            split="test",
            streaming=True,
        )

        records = []
        for i, row in enumerate(ds):
            if len(records) >= max_samples:
                break
            captions = row.get("caption", [])
            image = row.get("image")  # PIL Image in HF datasets
            if captions and image:
                # Store the first caption; actual image is loaded from HF cache
                records.append({
                    "type": "image_text_pair",
                    "dataset": "flickr30k",
                    "index": i,
                    "caption": captions[0] if isinstance(captions, list) else captions,
                    "all_captions": captions if isinstance(captions, list) else [captions],
                })

        # Also try COCO from HF
        try:
            ds_coco = load_dataset(
                "HuggingFaceM4/COCO",
                split="train",
                streaming=True,
            )
            for i, row in enumerate(ds_coco):
                if len(records) >= max_samples:
                    break
                sentences = row.get("sentences", {}).get("raw", [])
                if sentences:
                    records.append({
                        "type": "image_text_pair",
                        "dataset": "coco",
                        "index": i,
                        "caption": sentences[0],
                        "all_captions": sentences[:5],
                    })
        except Exception:
            log.info("COCO dataset not available, using Flickr30k only")

        count = _write_jsonl(out_path, records)
        log.info(f"Image-text pairs prepared: {count:,} → {out_path}")
        return out_path

    except Exception as e:
        log.error(f"Failed to prepare image-text data: {e}")
        _write_jsonl(out_path, [])
        return out_path


def prepare_audiocaps(max_samples: int = 46_000) -> Path:
    """
    Prepare AudioCaps metadata for audio-text contrastive training.
    Format: {audio_url, caption, audiocap_id}
    """
    out_path = _ensure_dir() / "audiocaps.jsonl"
    if out_path.exists() and _count_lines(out_path) >= max_samples * 0.9:
        log.info(f"AudioCaps already prepared: {_count_lines(out_path)} samples")
        return out_path

    log.info("Preparing AudioCaps from HuggingFace...")
    try:
        from datasets import load_dataset
        ds = load_dataset(
            "d0rj/audiocaps",
            split="train",
            streaming=True,
        )

        records = []
        for i, row in enumerate(ds):
            if len(records) >= max_samples:
                break
            caption = row.get("caption", "")
            if caption:
                records.append({
                    "type": "audio_text_pair",
                    "dataset": "audiocaps",
                    "index": i,
                    "caption": caption,
                    "youtube_id": row.get("youtube_id", ""),
                    "start_time": row.get("start_time", 0),
                })

        count = _write_jsonl(out_path, records)
        log.info(f"Audio-text pairs prepared: {count:,} → {out_path}")
        return out_path

    except Exception as e:
        log.error(f"Failed to prepare AudioCaps: {e}")
        _write_jsonl(out_path, [])
        return out_path


# ---------------------------------------------------------------------------
# PyTorch Datasets
# ---------------------------------------------------------------------------
class TextTripletDataset:
    """PyTorch-compatible dataset for text triplet contrastive learning."""

    def __init__(self, paths: list[Path], max_samples: Optional[int] = None):
        self.records = []
        for path in paths:
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    self.records.append(rec)
        if max_samples and len(self.records) > max_samples:
            random.shuffle(self.records)
            self.records = self.records[:max_samples]
        log.info(f"TextTripletDataset: {len(self.records):,} samples from {len(paths)} files")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict:
        rec = self.records[idx]
        if rec.get("type") == "triplet":
            return {
                "query": rec["query"],
                "positive": rec["positive"],
                "negative": rec.get("negative", ""),
            }
        else:
            return {
                "query": rec.get("anchor", rec.get("query", "")),
                "positive": rec.get("positive", ""),
                "negative": "",
            }


class MultimodalPairDataset:
    """
    Dataset for cross-modal contrastive learning.
    Returns (modality_a_input, modality_b_input) pairs.
    Actual loading of images/audio happens here.
    """

    def __init__(
        self,
        metadata_path: Path,
        modality: str = "image_text",
        max_samples: Optional[int] = None,
    ):
        self.modality = modality
        self.records = []
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                for line in f:
                    self.records.append(json.loads(line))
        if max_samples and len(self.records) > max_samples:
            random.shuffle(self.records)
            self.records = self.records[:max_samples]
        log.info(
            f"MultimodalPairDataset ({modality}): {len(self.records):,} pairs"
        )

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict:
        rec = self.records[idx]
        return {
            "caption": rec.get("caption", ""),
            "dataset": rec.get("dataset", ""),
            "index": rec.get("index", idx),
            "modality": self.modality,
        }


# ---------------------------------------------------------------------------
# Master data preparation
# ---------------------------------------------------------------------------
def prepare_all_datasets(
    phases: list[str] | None = None,
    max_text_samples: int = 800_000,
    max_image_samples: int = 118_000,
    max_audio_samples: int = 46_000,
) -> dict[str, Path]:
    """
    Prepare all training datasets. Returns dict of dataset name → path.

    phases: list of ["text", "multimodal"] or None for all.
    """
    _ensure_dir()
    results = {}

    if phases is None:
        phases = ["text", "multimodal"]

    if "text" in phases:
        log.info("\n=== Preparing Text Datasets ===")
        results["msmarco"] = prepare_msmarco_triplets(
            max_samples=min(500_000, max_text_samples)
        )
        results["allnli"] = prepare_allnli_pairs(
            max_samples=min(275_000, max_text_samples)
        )
        results["civic"] = prepare_civic_pairs(max_samples=50_000)

    if "multimodal" in phases:
        log.info("\n=== Preparing Multimodal Datasets ===")
        results["coco_captions"] = prepare_coco_captions(max_samples=max_image_samples)
        results["audiocaps"] = prepare_audiocaps(max_samples=max_audio_samples)

    log.info(f"\nAll datasets prepared: {list(results.keys())}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    import argparse
    parser = argparse.ArgumentParser(description="Prepare embedding training data")
    parser.add_argument("--phases", nargs="+", default=None,
                        choices=["text", "multimodal"])
    parser.add_argument("--max-text", type=int, default=800_000)
    parser.add_argument("--max-image", type=int, default=118_000)
    parser.add_argument("--max-audio", type=int, default=46_000)
    args = parser.parse_args()

    results = prepare_all_datasets(
        phases=args.phases,
        max_text_samples=args.max_text,
        max_image_samples=args.max_image,
        max_audio_samples=args.max_audio,
    )
    for name, path in results.items():
        count = _count_lines(path)
        print(f"  {name}: {count:,} samples → {path}")

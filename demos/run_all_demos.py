"""
Jemma Unified Demo Runner — All 5 Modalities on Gemma 4 E4B.

Runs all demo suites sequentially with a single model load:
  1. Text + Thinking
  2. Image Understanding
  3. Audio Understanding
  4. Video Understanding
  5. Function Calling

Usage:
    .\.venv_multimodal\Scripts\python.exe demos\run_all_demos.py [--modality text|image|audio|video|tools|all]

Hardware: RTX 5090 (32 GB), bf16, SDPA, TF32
Model: google/gemma-4-E4B-it (4.5B effective, 8B total with PLE)
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from e4b_loader import load_model_and_processor, print_vram_stats

import torch


def run_text_demos(model, processor):
    """Run text + thinking demos."""
    from demo_text import demo_basic_text, demo_thinking, demo_system_prompt, demo_multiturn
    results = {}
    for name, fn in [
        ("text/basic", demo_basic_text),
        ("text/thinking", demo_thinking),
        ("text/system_prompt", demo_system_prompt),
        ("text/multiturn", demo_multiturn),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results[name] = False
    return results


def run_image_demos(model, processor):
    """Run image understanding demos."""
    # Bump token budget for images
    processor.image_processor.max_soft_tokens = 560
    from demo_image import demo_image_caption, demo_ocr, demo_bbox, demo_local_image
    results = {}
    for name, fn in [
        ("image/caption", demo_image_caption),
        ("image/ocr", demo_ocr),
        ("image/bbox", demo_bbox),
        ("image/local", demo_local_image),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results[name] = False
    return results


def run_audio_demos(model, processor):
    """Run audio understanding demos."""
    from demo_audio import demo_audio_classification, demo_asr_synthetic, demo_audio_with_thinking
    results = {}
    for name, fn in [
        ("audio/classify", demo_audio_classification),
        ("audio/asr", demo_asr_synthetic),
        ("audio/thinking", demo_audio_with_thinking),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results[name] = False
    return results


def run_video_demos(model, processor):
    """Run video understanding demos."""
    # Lower token budget for video frames
    processor.image_processor.max_soft_tokens = 70
    from demo_video import demo_video_description, demo_video_thinking, demo_video_frame_counting
    results = {}
    for name, fn in [
        ("video/description", demo_video_description),
        ("video/thinking", demo_video_thinking),
        ("video/frames", demo_video_frame_counting),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results[name] = False
    return results


def run_tool_demos(model, processor):
    """Run function calling demos."""
    from demo_function_calling import demo_single_tool_call, demo_multiturn_tool
    results = {}
    for name, fn in [
        ("tools/single_call", demo_single_tool_call),
        ("tools/multiturn", demo_multiturn_tool),
    ]:
        try:
            results[name] = fn(model, processor)
        except Exception as e:
            print(f"  FAILED {name}: {e}")
            results[name] = False
    return results


SUITES = {
    "text": run_text_demos,
    "image": run_image_demos,
    "audio": run_audio_demos,
    "video": run_video_demos,
    "tools": run_tool_demos,
}


def main():
    parser = argparse.ArgumentParser(description="Jemma E4B Multimodal Demo Runner")
    parser.add_argument("--modality", choices=["text", "image", "audio", "video", "tools", "all"], default="all")
    args = parser.parse_args()

    print("=" * 70)
    print("  JEMMA MULTIMODAL DEMO SUITE — Gemma 4 E4B on RTX 5090")
    print("=" * 70)
    print()

    # Load model once
    t0 = time.time()
    model, processor = load_model_and_processor(max_soft_tokens=280)
    load_time = time.time() - t0
    print_vram_stats()
    print()

    # Run selected suites
    all_results = {}
    suites_to_run = SUITES if args.modality == "all" else {args.modality: SUITES[args.modality]}

    for suite_name, suite_fn in suites_to_run.items():
        print(f"\n{'#' * 70}")
        print(f"  SUITE: {suite_name.upper()}")
        print(f"{'#' * 70}")

        t1 = time.time()
        results = suite_fn(model, processor)
        suite_time = time.time() - t1

        all_results.update(results)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        print(f"\n  {suite_name}: {passed}/{total} passed ({suite_time:.1f}s)")

    # Final report
    total_time = time.time() - t0
    passed = sum(1 for v in all_results.values() if v)
    total = len(all_results)

    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)
    print(f"  Model: google/gemma-4-E4B-it (bf16)")
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  Load time: {load_time:.1f}s")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Results: {passed}/{total} passed")
    print()

    for name, passed_flag in sorted(all_results.items()):
        status = "PASS" if passed_flag else "FAIL"
        print(f"  [{status}] {name}")

    print()
    print_vram_stats()
    print("=" * 70)

    return 0 if all(all_results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

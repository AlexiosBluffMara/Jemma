"""
Publish Jemma SafeBrain model to HuggingFace Hub.

Naming follows Google's External Gemma Model Variant Guidelines:
  - Model name ("jemma-safebrain") comes FIRST
  - Gemma reference ("gemma-4-e4b-it") comes AFTER for discoverability
  - "Gemma is a trademark of Google LLC." attribution included
  - base_model metadata links back to google/gemma-4-E4B-it

Repo: soumitty/jemma-safebrain-gemma-4-e4b-it
License: Apache 2.0 (same as Gemma 4)
"""

import argparse
import os
import sys
import shutil
from pathlib import Path

# --- Configuration ---
REPO_ID = "soumitty/jemma-safebrain-gemma-4-e4b-it"
BASE_MODEL = "google/gemma-4-E4B-it"
MODEL_CARD_PATH = Path(__file__).parent / "hf_model_card.md"


def create_repo(api, repo_id: str, private: bool = False):
    """Create the HF repo if it doesn't exist."""
    try:
        url = api.create_repo(
            repo_id=repo_id,
            private=private,
            exist_ok=True,
            repo_type="model",
        )
        print(f"Repo ready: {url}")
        return url
    except Exception as e:
        print(f"Error creating repo: {e}")
        sys.exit(1)


def upload_model_card(api, repo_id: str, card_path: Path):
    """Upload the model card (README.md) to the repo."""
    if not card_path.exists():
        print(f"Model card not found: {card_path}")
        sys.exit(1)

    api.upload_file(
        path_or_fileobj=str(card_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
        commit_message="Add model card",
    )
    print(f"Uploaded model card from {card_path}")


def upload_notice_file(api, repo_id: str):
    """Upload Apache 2.0 NOTICE file with attribution."""
    notice_content = """Jemma SafeBrain
Copyright 2026 Soumit Lahiri

This product is based on Gemma 4, developed by Google DeepMind.
Original model: google/gemma-4-E4B-it
License: Apache 2.0

Gemma is a trademark of Google LLC.
"""
    api.upload_file(
        path_or_fileobj=notice_content.encode("utf-8"),
        path_in_repo="NOTICE",
        repo_id=repo_id,
        repo_type="model",
        commit_message="Add NOTICE file (Apache 2.0 attribution)",
    )
    print("Uploaded NOTICE file")


def upload_config_and_demos(api, repo_id: str, project_root: Path):
    """Upload demo scripts and hardware config for reproducibility."""
    files_to_upload = [
        ("demos/e4b_loader.py", "demos/e4b_loader.py"),
        ("demos/hw_config.py", "demos/hw_config.py"),
        ("demos/demo_text.py", "demos/demo_text.py"),
        ("demos/demo_image.py", "demos/demo_image.py"),
        ("demos/demo_audio.py", "demos/demo_audio.py"),
        ("demos/demo_video.py", "demos/demo_video.py"),
        ("demos/demo_function_calling.py", "demos/demo_function_calling.py"),
        ("demos/run_all_demos.py", "demos/run_all_demos.py"),
        ("demos/verify_gpu.py", "demos/verify_gpu.py"),
    ]

    for local_path, repo_path in files_to_upload:
        full_path = project_root / local_path
        if full_path.exists():
            api.upload_file(
                path_or_fileobj=str(full_path),
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type="model",
                commit_message=f"Add {repo_path}",
            )
            print(f"  Uploaded {repo_path}")
        else:
            print(f"  Skipped {local_path} (not found)")


def upload_model_weights(api, repo_id: str, model_path: str):
    """Upload fine-tuned model weights (adapter or full).

    For initial release, we upload the base model config + link.
    For fine-tuned releases, this uploads the actual weights.
    """
    model_dir = Path(model_path)
    if not model_dir.exists():
        print(f"Model path not found: {model_path}")
        print("Skipping weight upload — use --model-path to specify weights directory")
        return

    api.upload_folder(
        folder_path=str(model_dir),
        repo_id=repo_id,
        repo_type="model",
        commit_message="Upload model weights",
        ignore_patterns=["*.py", "*.md", "__pycache__", ".git"],
    )
    print(f"Uploaded model weights from {model_dir}")


def validate_token():
    """Validate HF token is set and has write access."""
    from huggingface_hub import HfApi
    api = HfApi()
    try:
        info = api.whoami()
        print(f"Authenticated as: {info['name']} ({info.get('fullname', 'N/A')})")
        return api
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Run: huggingface-cli login")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Publish Jemma SafeBrain to HuggingFace Hub"
    )
    parser.add_argument(
        "--repo-id", default=REPO_ID,
        help=f"HuggingFace repo ID (default: {REPO_ID})"
    )
    parser.add_argument(
        "--private", action="store_true",
        help="Create as private repo (use for testing)"
    )
    parser.add_argument(
        "--model-path", default=None,
        help="Path to fine-tuned model weights to upload"
    )
    parser.add_argument(
        "--card-only", action="store_true",
        help="Only upload the model card (README.md)"
    )
    parser.add_argument(
        "--demos", action="store_true",
        help="Also upload demo scripts"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate everything without uploading"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Jemma SafeBrain — HuggingFace Publisher")
    print("=" * 60)
    print(f"Repo: {args.repo_id}")
    print(f"Base model: {BASE_MODEL}")
    print(f"License: Apache 2.0")
    print(f"Naming: Per Google External Gemma Model Variant Guidelines")
    print()

    # Validate auth
    api = validate_token()

    if args.dry_run:
        print("\n[DRY RUN] Validation passed. No uploads performed.")
        print(f"  Would create repo: {args.repo_id}")
        print(f"  Would upload model card from: {MODEL_CARD_PATH}")
        if args.model_path:
            print(f"  Would upload weights from: {args.model_path}")
        if args.demos:
            print(f"  Would upload demo scripts")
        return

    # Create repo
    create_repo(api, args.repo_id, private=args.private)

    # Upload model card
    upload_model_card(api, args.repo_id, MODEL_CARD_PATH)

    if args.card_only:
        print("\nDone (card-only mode).")
        return

    # Upload NOTICE
    upload_notice_file(api, args.repo_id)

    # Upload demos if requested
    if args.demos:
        project_root = Path(__file__).parent.parent
        upload_config_and_demos(api, args.repo_id, project_root)

    # Upload model weights if provided
    if args.model_path:
        upload_model_weights(api, args.repo_id, args.model_path)

    print("\n" + "=" * 60)
    print("PUBLISH COMPLETE")
    print("=" * 60)
    print(f"View at: https://huggingface.co/{args.repo_id}")
    print()
    print("Next steps:")
    if not args.model_path:
        print("  1. Fine-tune the model (Unsloth QLoRA)")
        print("  2. Re-run with --model-path <weights_dir> to upload weights")
    print("  3. Run benchmarks and update the model card")
    print("  4. Add to Kaggle writeup submission")


if __name__ == "__main__":
    main()

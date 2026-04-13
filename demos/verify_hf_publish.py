"""Verify the published HuggingFace model repo."""
from huggingface_hub import HfApi

api = HfApi()
info = api.model_info("soumitty/jemma-safebrain-gemma-4-e4b-it")

print(f"Model: {info.id}")
print(f"Private: {info.private}")
print(f"Tags: {info.tags}")
print(f"Pipeline: {info.pipeline_tag}")

if info.card_data:
    print(f"License: {info.card_data.get('license', 'N/A')}")
    print(f"Base model: {info.card_data.get('base_model', 'N/A')}")
    print(f"Base model relation: {info.card_data.get('base_model_relation', 'N/A')}")
else:
    print("No card data parsed")

print(f"\nFiles in repo:")
for s in info.siblings:
    size = f" ({s.size:,} bytes)" if s.size else ""
    print(f"  {s.rfilename}{size}")

print(f"\nCreated: {info.created_at}")
print(f"Last modified: {info.last_modified}")
print(f"\nURL: https://huggingface.co/{info.id}")
print("\nVALIDATION PASSED" if not info.private else "\nWARNING: Repo is private!")

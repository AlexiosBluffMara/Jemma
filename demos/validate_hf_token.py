"""Validate HuggingFace token: auth, permissions, existing repos."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from huggingface_hub import HfApi
import requests

api = HfApi()
info = api.whoami()
print(f"Authenticated as: {info['name']}")
print(f"Full name: {info.get('fullname', 'N/A')}")
print(f"Email: {info.get('email', 'N/A')}")
print(f"Orgs: {[o['name'] for o in info.get('orgs', [])]}")

# List existing repos
repos = list(api.list_models(author=info['name']))
print(f"\nExisting models: {len(repos)}")
for r in repos[:20]:
    print(f"  - {r.id} (likes: {r.likes}, downloads: {r.downloads})")

# List datasets
datasets = list(api.list_datasets(author=info['name']))
print(f"\nExisting datasets: {len(datasets)}")
for d in datasets[:20]:
    print(f"  - {d.id} (likes: {d.likes}, downloads: {d.downloads})")

# Check token permissions via API
r = requests.get(
    'https://huggingface.co/api/whoami-v2',
    headers={'Authorization': f'Bearer {api.token}'}
)
data = r.json()
access = data.get('auth', {}).get('accessToken', {})
print(f"\nToken name: {access.get('displayName', 'unknown')}")
print(f"Token role: {access.get('role', 'unknown')}")
fgp = access.get('fineGrainedPermissions', [])
if fgp:
    print(f"Fine-grained permissions: {fgp}")

# Check if we can access gated models (Gemma)
print("\n--- Gated Model Access ---")
try:
    model_info = api.model_info("google/gemma-4-e4b-it")
    print(f"google/gemma-4-e4b-it: gated={model_info.gated}")
    print(f"  tags: {model_info.tags[:10] if model_info.tags else 'none'}")
    print(f"  license: {model_info.card_data.get('license', 'unknown') if model_info.card_data else 'unknown'}")
except Exception as e:
    print(f"google/gemma-4-e4b-it: ERROR - {e}")

try:
    model_info = api.model_info("google/gemma-4-e2b-it")
    print(f"google/gemma-4-e2b-it: gated={model_info.gated}")
except Exception as e:
    print(f"google/gemma-4-e2b-it: ERROR - {e}")

# Test write access by creating + deleting a test repo
print("\n--- Write Access Test ---")
test_repo = f"{info['name']}/jemma-test-delete-me"
try:
    url = api.create_repo(repo_id=test_repo, private=True, exist_ok=True)
    print(f"Created test repo: {url} (WRITE ACCESS CONFIRMED)")
    api.delete_repo(repo_id=test_repo)
    print(f"Deleted test repo: {test_repo}")
    print("WRITE + DELETE permissions: CONFIRMED")
except Exception as e:
    print(f"Write test failed: {e}")
    print("Token may be READ-ONLY")

print("\nValidation complete!")

---
description: "Publish the trained model and artifacts to HuggingFace Hub"
agent: "agent"
tools: [execute, read, search]
---
Publish the Jemma model and artifacts to HuggingFace Hub.

1. Validate HF token: `python -u -W ignore demos/validate_hf_token.py`
2. Ensure model card is up to date: `toolbox/hf_model_card.md`
3. Run publisher: `python -u -W ignore toolbox/publish_to_hf.py --demos`
4. Verify the published repo at `https://huggingface.co/soumitty/jemma-safebrain-gemma-4-e4b-it`
5. Check: model card renders correctly, NOTICE file present, demos included
6. Confirm: base_model metadata links to `google/gemma-4-E4B-it`, license is Apache-2.0

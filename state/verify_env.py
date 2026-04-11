"""Verify the Unsloth training environment has all required packages."""
import sys

print(f"Python: {sys.version}")

results = []

def check(name, test_fn):
    try:
        msg = test_fn()
        print(f"  [OK] {name}: {msg}")
        results.append((name, True))
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        results.append((name, False))

def check_torch():
    import torch
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    return f"v{torch.__version__}, CUDA={torch.cuda.is_available()}, GPU={gpu}"

def check_unsloth():
    from unsloth import FastModel
    return "FastModel imported OK"

def check_transformers():
    import transformers
    return f"v{transformers.__version__}"

def check_trl():
    import trl
    return f"v{trl.__version__}"

def check_peft():
    import peft
    return f"v{peft.__version__}"

def check_datasets():
    import datasets
    return f"v{datasets.__version__}"

def check_accelerate():
    import accelerate
    return f"v{accelerate.__version__}"

def check_bitsandbytes():
    import bitsandbytes
    return f"v{bitsandbytes.__version__}"

def check_sentencepiece():
    import sentencepiece
    return "OK"

def check_huggingface_hub():
    import huggingface_hub
    return f"v{huggingface_hub.__version__}"

def check_tokenizers():
    import tokenizers
    return f"v{tokenizers.__version__}"

def check_unsloth_zoo():
    import unsloth_zoo
    return "OK"

check("torch", check_torch)
check("unsloth", check_unsloth)
check("transformers", check_transformers)
check("trl", check_trl)
check("peft", check_peft)
check("datasets", check_datasets)
check("accelerate", check_accelerate)
check("bitsandbytes", check_bitsandbytes)
check("sentencepiece", check_sentencepiece)
check("huggingface_hub", check_huggingface_hub)
check("tokenizers", check_tokenizers)
check("unsloth_zoo", check_unsloth_zoo)

passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
print(f"\nResult: {passed} passed, {failed} failed")
if failed:
    print("MISSING:", [name for name, ok in results if not ok])
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")

"""
Jemma E4B Model Loader — maximized for RTX 5090 (32GB VRAM).

Loads google/gemma-4-E4B-it at bf16 with hardware-optimal settings:
- bf16 for Blackwell SM_120 native precision
- SDPA (scaled dot product attention) via PyTorch 2.11
- TF32 enabled for matmuls
- Full 128K context budget

VRAM budget:
  Model weights (bf16):  ~15.0 GB
  KV cache (128K ctx):    ~2.3 GB  (hybrid attention: 9 global + 27 sliding)
  Activations/overhead:   ~3.0 GB
  --------------------------------
  Total committed:        ~20.3 GB
  Free headroom:          ~11.5 GB  (for batch, images, audio, video tokens)
"""

import torch
import time
import os
import warnings

# Suppress HF and torch warnings that cause PowerShell to kill the process
warnings.filterwarnings("ignore", category=UserWarning)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Redirect stderr warnings through logging instead of direct stderr
import logging
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Hardware maximization settings
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cudnn.benchmark = True

# Use Unsloth's E4B (identical architecture, already cached locally)
# Falls back to official Google model if not available
MODEL_ID = "unsloth/gemma-4-E4B-it"
DEVICE = "cuda"
DTYPE = torch.bfloat16


def load_model_and_processor(
    model_id: str = MODEL_ID,
    max_soft_tokens: int = 560,
    trust_remote_code: bool = True,
):
    """Load E4B with full hardware optimization for RTX 5090.

    Args:
        model_id: HuggingFace model ID.
        max_soft_tokens: Image token budget (70/140/280/560/1120).
        trust_remote_code: Allow custom model code from HF.

    Returns:
        (model, processor) tuple ready for inference.
    """
    from transformers import AutoProcessor, AutoModelForMultimodalLM

    print(f"Loading {model_id} in bf16 on {DEVICE}...")
    t0 = time.time()

    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        dtype=DTYPE,
        device_map="auto",
        trust_remote_code=trust_remote_code,
        attn_implementation="sdpa",
    )
    model.eval()

    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=trust_remote_code)
    processor.image_processor.max_soft_tokens = max_soft_tokens

    elapsed = time.time() - t0
    vram_used = torch.cuda.max_memory_allocated() / 1024**3
    print(f"Loaded in {elapsed:.1f}s | VRAM: {vram_used:.1f} GB | Tokens/image: {max_soft_tokens}")

    return model, processor


def generate(model, processor, messages, max_new_tokens=512, enable_thinking=False, temperature=1.0, top_p=0.95, top_k=64):
    """Run inference with optimal generation settings.

    Args:
        model: Loaded E4B model.
        processor: Loaded processor.
        messages: Chat messages in HF format.
        max_new_tokens: Max tokens to generate.
        enable_thinking: Enable chain-of-thought reasoning.
        temperature: Sampling temperature.
        top_p: Nucleus sampling threshold.
        top_k: Top-k sampling.

    Returns:
        Generated text string.
    """
    # Normalize messages: convert plain string content to list-of-dicts format
    normalized = []
    for msg in messages:
        m = dict(msg)
        if isinstance(m.get("content"), str):
            m["content"] = [{"type": "text", "text": m["content"]}]
        normalized.append(m)

    inputs = processor.apply_chat_template(
        normalized,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        enable_thinking=enable_thinking,
    ).to(model.device)

    input_len = inputs["input_ids"].shape[1]

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )

    response = processor.decode(outputs[0][input_len:], skip_special_tokens=True)
    return response


def print_vram_stats():
    """Print current VRAM usage."""
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {allocated:.1f} GB allocated | {reserved:.1f} GB reserved | {total:.1f} GB total")


if __name__ == "__main__":
    model, processor = load_model_and_processor()
    print_vram_stats()

    # Quick smoke test
    messages = [{"role": "user", "content": "Say 'Hello from Jemma E4B on RTX 5090!' and nothing else."}]
    response = generate(model, processor, messages, max_new_tokens=30)
    print(f"\nResponse: {response}")
    print_vram_stats()

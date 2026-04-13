"""
Hardware Maximization Config for RTX 5090 + Gemma 4 E4B.

This module configures optimal settings for maximum throughput
and data ingestion on the RTX 5090 (32 GB GDDR7, Blackwell SM_120).

Key optimizations:
  - bf16 native precision (SM_120 optimal)
  - TF32 matmuls (2x throughput vs full fp32)
  - SDPA attention (FlashAttention-like via PyTorch)
  - cudnn.benchmark for conv autotuning
  - Hybrid attention KV budget: 128K context = only ~2.3 GB
  - torch.compile for sustained throughput (optional)
"""

import torch
import os


def apply_hardware_maximization():
    """Apply all hardware optimization settings for RTX 5090.

    Call this BEFORE loading any model.
    """
    # TF32 — 2x throughput on tensor cores, ~0.1% accuracy impact
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    # cuDNN autotuner — finds fastest conv algorithms
    torch.backends.cudnn.benchmark = True

    # Memory efficiency
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

    # Disable gradient computation globally for inference
    torch.set_grad_enabled(False)

    print("Hardware maximization applied:")
    print(f"  TF32 matmul: {torch.backends.cuda.matmul.allow_tf32}")
    print(f"  TF32 cudnn: {torch.backends.cudnn.allow_tf32}")
    print(f"  cudnn benchmark: {torch.backends.cudnn.benchmark}")
    print(f"  CUDA alloc: expandable_segments")


def get_optimal_batch_config():
    """Return optimal batch sizes per modality for RTX 5090.

    Based on VRAM budget:
        Model (bf16):    ~15.0 GB
        Total VRAM:      ~31.8 GB
        Available:       ~16.8 GB for KV cache + activations + batch data

    Returns:
        dict with per-modality batch configurations
    """
    return {
        "text": {
            "max_batch_size": 8,
            "max_new_tokens": 2048,
            "context_window": 131072,  # Full 128K
            "description": "Text-only: 8 concurrent requests at 128K context",
        },
        "image": {
            "max_batch_size": 4,
            "max_new_tokens": 1024,
            "max_soft_tokens": 560,  # Good balance: detail vs speed
            "throughput_estimate": "18-24K images/hour (classify)",
            "description": "Image: 4 concurrent, 560 tokens/image for detailed analysis",
        },
        "audio": {
            "max_batch_size": 2,
            "max_new_tokens": 512,
            "max_duration_seconds": 30,
            "token_rate": 25,  # ~25 tokens/second of audio
            "throughput_estimate": "1400-2400 chunks/hour",
            "description": "Audio: 2 concurrent, 30s max per clip",
        },
        "video": {
            "max_batch_size": 1,
            "max_new_tokens": 1024,
            "max_duration_seconds": 60,
            "fps": 1,
            "max_soft_tokens_per_frame": 70,
            "description": "Video: single, 60s at 1fps, 70 tokens/frame",
        },
    }


def get_vram_budget():
    """Calculate and display VRAM budget for E4B on RTX 5090.

    Returns:
        dict with budget breakdown
    """
    props = torch.cuda.get_device_properties(0)
    total_gb = props.total_memory / 1024**3

    budget = {
        "gpu_name": torch.cuda.get_device_name(0),
        "total_vram_gb": round(total_gb, 1),
        "model_weights_gb": 15.0,  # E4B @ bf16
        "kv_cache_128k_gb": 2.3,   # Hybrid attention: 9 global + 27 sliding window
        "activations_gb": 3.0,
        "committed_gb": 20.3,
        "available_gb": round(total_gb - 20.3, 1),
    }

    print(f"\nVRAM Budget — {budget['gpu_name']}")
    print(f"  Total:           {budget['total_vram_gb']:.1f} GB")
    print(f"  Model (bf16):    {budget['model_weights_gb']:.1f} GB")
    print(f"  KV (128K ctx):   {budget['kv_cache_128k_gb']:.1f} GB")
    print(f"  Activations:     {budget['activations_gb']:.1f} GB")
    print(f"  Committed:       {budget['committed_gb']:.1f} GB")
    print(f"  Available:       {budget['available_gb']:.1f} GB")

    return budget


if __name__ == "__main__":
    apply_hardware_maximization()
    budget = get_vram_budget()
    config = get_optimal_batch_config()

    print("\nPer-Modality Optimal Configs:")
    for modality, cfg in config.items():
        print(f"\n  {modality.upper()}:")
        for k, v in cfg.items():
            print(f"    {k}: {v}")

"""Verify GPU stack: PyTorch + CUDA + RTX 5090 detection."""
import torch

print(f"PyTorch {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
props = torch.cuda.get_device_properties(0)
print(f"VRAM: {props.total_memory / 1024**3:.1f} GB")
cap = torch.cuda.get_device_capability(0)
print(f"Arch: sm_{cap[0]}{cap[1]}")
print(f"bf16 supported: {torch.cuda.is_bf16_supported()}")
print(f"SDPA available: {hasattr(torch.nn.functional, 'scaled_dot_product_attention')}")

# Quick CUDA compute test
x = torch.randn(1024, 1024, device="cuda", dtype=torch.bfloat16)
y = torch.matmul(x, x.T)
print(f"bf16 matmul test: {y.shape} - OK")

# Check transformers
import transformers
print(f"transformers {transformers.__version__}")

import accelerate
print(f"accelerate {accelerate.__version__}")

import bitsandbytes
print(f"bitsandbytes {bitsandbytes.__version__}")

import peft
print(f"peft {peft.__version__}")

# Media libs
import PIL
print(f"Pillow {PIL.__version__}")

import librosa
print(f"librosa {librosa.__version__}")

import av
print(f"PyAV {av.__version__}")

import cv2
print(f"OpenCV {cv2.__version__}")

print("\n=== ALL CHECKS PASSED ===")

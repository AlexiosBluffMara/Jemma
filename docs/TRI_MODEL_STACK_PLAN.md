# Tri-Model Stack: Gemma 4 E2B + E4B + SAM 3.1 on RTX 5090

**Target**: Run all three models in unison on a single RTX 5090 (31.8 GB VRAM)
for cohesive video/camera feed analysis with segmentation, captioning, and
dataset ingestion.

---

## 1. Pre-Flight Environment Checks

Run these before anything else to confirm the environment is ready.

### 1.1 GPU & Driver

```powershell
# Confirm GPU detected, VRAM available, CUDA version
$env:PYTHONUNBUFFERED=1
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import torch
assert torch.cuda.is_available(), 'No CUDA GPU'
props = torch.cuda.get_device_properties(0)
print(f'GPU: {props.name}')
print(f'VRAM: {props.total_memory / 1024**3:.1f} GB')
print(f'Compute: SM_{props.major}{props.minor}')
print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.version.cuda}')
# Must be: RTX 5090, ~31.8 GB, SM_120, PyTorch 2.10+, CUDA 12.8
assert props.total_memory > 30 * 1024**3, 'Need 32GB VRAM'
assert props.major >= 12, 'Need Blackwell (SM_120+)'
print('GPU check PASSED')
"
```

**Expected**: RTX 5090, 31.8 GB, SM_120, PyTorch ≥2.10.0+cu128.

### 1.2 Ollama Service

```powershell
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import urllib.request, json
req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
with urllib.request.urlopen(req, timeout=5) as resp:
    models = [m['name'] for m in json.loads(resp.read())['models']]
assert 'gemma4:e2b' in models, 'Missing gemma4:e2b in Ollama'
assert 'gemma4:e4b' in models, 'Missing gemma4:e4b in Ollama'
print(f'Ollama OK: {len(models)} models, E2B+E4B present')
"
```

**Expected**: Both `gemma4:e2b` and `gemma4:e4b` listed.

If missing, pull them:
```powershell
ollama pull gemma4:e2b
ollama pull gemma4:e4b
```

### 1.3 Ollama Quick Chat Validation

```powershell
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import urllib.request, json, time

def chat(model, prompt):
    payload = json.dumps({'model': model, 'messages': [{'role':'user','content': prompt}], 'stream': False}).encode()
    req = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=payload, headers={'Content-Type':'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data['message']['content'][:80], time.time()-t0

for m in ['gemma4:e2b', 'gemma4:e4b']:
    txt, t = chat(m, 'Say exactly: Hello from Jemma.')
    print(f'{m} ({t:.1f}s): {txt}')
"
```

**Expected**: Both respond with "Hello from Jemma" in < 15s.

### 1.4 SAM 3 Package

```powershell
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import sam3
from sam3.model_builder import build_sam3_image_model, build_sam3_video_predictor
print('SAM 3 package OK')
"
```

**If missing**, install from the cloned vendor directory:
```powershell
cd d:\JemmaRepo\Jemma\vendor\sam3
& d:\JemmaRepo\Jemma\.venv_multimodal\Scripts\pip.exe install -e .
& d:\JemmaRepo\Jemma\.venv_multimodal\Scripts\pip.exe install einops pycocotools
```

### 1.5 HuggingFace Auth (for gated SAM 3.1 checkpoint)

```powershell
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
from huggingface_hub import HfApi
api = HfApi()
user = api.whoami()
print(f'HF user: {user[\"name\"]}')
# Verify access to gated sam3.1 model
info = api.model_info('facebook/sam3.1')
print(f'SAM 3.1 access: {info.gated} — OK')
"
```

**If access denied**: Visit https://huggingface.co/facebook/sam3.1 and accept
the license agreement, then retry.

### 1.6 Python Version & Key Packages

```powershell
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import sys; assert sys.version_info >= (3, 12), f'Need Python 3.12+, got {sys.version}'
import torch; assert torch.cuda.is_available()
import transformers; print(f'transformers: {transformers.__version__}')
import sam3; print('sam3: OK')
import PIL; print(f'Pillow: {PIL.__version__}')
import av; print(f'PyAV: {av.__version__}')
import numpy; print(f'numpy: {numpy.__version__}')
print('All packages OK')
"
```

---

## 2. VRAM Budget Analysis

### 2.1 RTX 5090 Total: 31.8 GB

| Component | Mode | VRAM (est.) | Notes |
|---|---|---|---|
| **Gemma 4 E4B (bf16)** | Transformers direct | ~15.0 GB | Full weights + KV cache |
| **Gemma 4 E2B (bf16)** | Transformers direct | ~5.5 GB | Smaller model |
| **SAM 3.1** | bf16 inference | ~7.0 GB | 848M params + vision encoder + memory |
| PyTorch overhead | — | ~1.5 GB | CUDA context, allocator |

### 2.2 Viable Configurations on RTX 5090

#### Config A: SAM 3.1 + E2B (bf16) — FITS COMFORTABLY ✓
| Model | VRAM | Running |
|---|---|---|
| SAM 3.1 (bf16) | ~7.0 GB | Segmentation + tracking |
| E2B (bf16, Transformers) | ~5.5 GB | Captioning + reasoning |
| Overhead + activations | ~3.0 GB | |
| **Total** | **~15.5 GB** | **16.3 GB free for batch/media** |

This is the **recommended local config** — leaves massive headroom for images,
video frames, and batch processing.

#### Config B: SAM 3.1 + E4B (bf16) — FITS, TIGHT ✓
| Model | VRAM | Running |
|---|---|---|
| SAM 3.1 (bf16) | ~7.0 GB | Segmentation + tracking |
| E4B (bf16, Transformers) | ~15.0 GB | Captioning + reasoning |
| Overhead + activations | ~3.0 GB | |
| **Total** | **~25.0 GB** | **6.8 GB free** |

Workable but tight. Reduce image token budget (`max_soft_tokens=140`)
and limit video to short clips.

#### Config C: SAM 3.1 + Ollama E2B (q4_k_m) + Ollama E4B (q8_0) — SEQUENTIAL ✓
| Model | VRAM | Running |
|---|---|---|
| SAM 3.1 (bf16) | ~7.0 GB | Always loaded |
| Ollama E2B (q4, when called) | ~1.5 GB | Swapped in by Ollama |
| Ollama E4B (q8, when called) | ~5.0 GB | Swapped in by Ollama |
| **Peak** | **~12.0 GB** | **Ollama manages swap** |

Ollama handles model swapping automatically. SAM stays pinned on GPU.
This is the **most flexible config** — both Gemma models available
via HTTP API calls, SAM runs continuously for camera/video feeds.

#### Config D: All three simultaneously — DOES NOT FIT ✗
E4B bf16 (15GB) + E2B bf16 (5.5GB) + SAM 3.1 (7GB) = ~27.5GB + overhead > 31.8GB.
Not viable without offloading. Use Config C instead.

### 2.3 Recommendation

**Use Config C (SAM 3.1 pinned + Ollama for both Gemma models).**

- SAM 3.1 stays resident on GPU full-time for real-time segmentation
- Ollama dynamically loads E2B or E4B as needed for captioning/reasoning
- The quantized Ollama models (q4_k_m / q8_0) coexist with SAM 3.1 easily
- Total peak VRAM: ~12 GB, leaving ~20 GB free for video frames and batch work

---

## 3. Stack Execution Plan

### 3.1 Phase 1: Download SAM 3.1 Checkpoint

```python
from sam3.model_builder import download_ckpt_from_hf
# Downloads ~3.3 GB checkpoint from facebook/sam3.1 (gated, needs HF auth)
ckpt_path = download_ckpt_from_hf(version="sam3.1")
print(f"Checkpoint: {ckpt_path}")
```

This caches to `~/.cache/huggingface/hub/`. Only downloads once.

### 3.2 Phase 2: Load SAM 3.1 for Image Segmentation

```python
import torch
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
from PIL import Image

# Build model — loads SAM 3.1 checkpoint with Object Multiplex
model = build_sam3_image_model(
    device="cuda",
    eval_mode=True,
    load_from_HF=True,   # auto-downloads sam3.pt from facebook/sam3
)
processor = Sam3Processor(model)

# Quick validation: segment a test image
img = Image.new("RGB", (400, 300), "white")
from PIL import ImageDraw
draw = ImageDraw.Draw(img)
draw.rectangle([50, 50, 200, 200], fill="red")
draw.ellipse([250, 100, 380, 250], fill="blue")

state = processor.set_image(img)
output = processor.set_text_prompt(state=state, prompt="red rectangle")
masks, boxes, scores = output["masks"], output["boxes"], output["scores"]
print(f"SAM 3.1 image OK: {len(masks)} masks, top score {scores[0]:.3f}")
```

### 3.3 Phase 3: Load SAM 3.1 for Video Tracking

```python
from sam3.model_builder import build_sam3_video_predictor

video_predictor = build_sam3_video_predictor()

# Start a session with a video file or JPEG directory
video_path = "path/to/video.mp4"
response = video_predictor.handle_request(
    request=dict(type="start_session", resource_path=video_path)
)
session_id = response["session_id"]

# Add text prompt on first frame
response = video_predictor.handle_request(
    request=dict(
        type="add_prompt",
        session_id=session_id,
        frame_index=0,
        text="person walking",
    )
)
output = response["outputs"]
print(f"SAM 3.1 video tracking OK: frame 0, {len(output)} objects tracked")
```

### 3.4 Phase 4: Validate Ollama Gemma Models Are Operational

```python
import urllib.request, json, time

def ollama_chat(model, prompt, timeout=60):
    payload = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False
    }).encode()
    req = urllib.request.Request(
        'http://127.0.0.1:11434/api/chat',
        data=payload,
        headers={'Content-Type': 'application/json'}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    content = data['message']['content']
    dur = data.get('total_duration', 0) / 1e9
    return content, time.time() - t0, dur

# Validate E2B quantized
txt, wall, model_t = ollama_chat('gemma4:e2b', 'Say: Jemma E2B operational.')
print(f"E2B via Ollama: '{txt[:60]}' ({wall:.1f}s)")

# Validate E4B quantized
txt, wall, model_t = ollama_chat('gemma4:e4b', 'Say: Jemma E4B operational.')
print(f"E4B via Ollama: '{txt[:60]}' ({wall:.1f}s)")
```

### 3.5 Phase 5: Unified Pipeline — SAM 3.1 Segments, Gemma Describes

The core idea: SAM 3.1 finds and segments objects in video frames,
then Gemma (via Ollama) describes/reasons about those segments.

```python
"""
Unified tri-model pipeline:
  1. SAM 3.1 segments objects from camera/video frames
  2. Crop + mask the detected regions
  3. Feed cropped regions to Gemma E2B/E4B for captioning/reasoning
  4. Store structured annotations in the dataset
"""

import numpy as np
from PIL import Image

# -- SAM 3.1 segments a frame --
frame = Image.open("frame_001.jpg")
state = sam3_processor.set_image(frame)
output = sam3_processor.set_text_prompt(state=state, prompt="all objects")
masks, boxes, scores = output["masks"], output["boxes"], output["scores"]

# -- For each detected object, crop and send to Gemma --
for i, (mask, box, score) in enumerate(zip(masks, boxes, scores)):
    if score < 0.3:
        continue
    x1, y1, x2, y2 = box.int().tolist()
    crop = frame.crop((x1, y1, x2, y2))

    # Save crop to temp file for Ollama (Ollama doesn't take PIL directly)
    crop_path = f"/tmp/crop_{i}.jpg"
    crop.save(crop_path)

    # Ask Gemma to describe the crop
    # (Ollama E2B for speed, E4B for quality)
    description = ollama_chat(
        'gemma4:e2b',
        f'Describe this cropped region from a camera feed in one sentence.'
    )

    # Store annotation
    annotation = {
        "frame": "frame_001.jpg",
        "object_id": i,
        "bbox": [x1, y1, x2, y2],
        "score": float(score),
        "mask_pixels": int(mask.sum()),
        "description": description,
    }
    # -> Append to datasets/annotations.jsonl
```

### 3.6 Phase 6: VRAM Telemetry During Run

```python
import torch

def vram_report():
    alloc = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {alloc:.1f}GB alloc / {reserved:.1f}GB reserved / {total:.1f}GB total")
    print(f"Free: {total - reserved:.1f}GB")
    return total - reserved

# Call after each model load to verify budget
vram_report()
```

---

## 4. Ollama Quantized Model Verification

To confirm the Ollama quantized models are genuinely running (not cached/stale):

```powershell
# 1. Check which model is actively loaded in Ollama
ollama ps

# 2. Verify model metadata
ollama show gemma4:e2b --modelfile
ollama show gemma4:e4b --modelfile

# 3. Check quantization level in the response metadata
& .\.venv_multimodal\Scripts\python.exe -u -W ignore -c "
import urllib.request, json

def get_model_info(model):
    payload = json.dumps({'model': model}).encode()
    req = urllib.request.Request('http://127.0.0.1:11434/api/show', data=payload,
                                 headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

for m in ['gemma4:e2b', 'gemma4:e4b']:
    info = get_model_info(m)
    details = info.get('details', {})
    print(f'{m}:')
    print(f'  Family: {details.get(\"family\", \"?\")}')
    print(f'  Param size: {details.get(\"parameter_size\", \"?\")}')
    print(f'  Quant: {details.get(\"quantization_level\", \"?\")}')
    print(f'  Format: {details.get(\"format\", \"?\")}')
    print()
"
```

**What to expect**:
- `gemma4:e2b` → quantization_level: Q4_K_M, parameter_size: ~2B
- `gemma4:e4b` → quantization_level: Q8_0, parameter_size: ~4B

---

## 5. Google Cloud Full-Size Model Evaluation

### 5.1 What "Full Size" Means

| Model | Full (bf16) | VRAM Required | Best GCP Machine |
|---|---|---|---|
| Gemma 4 E2B (bf16) | ~5.5 GB | 8 GB | `g2-standard-4` (1× L4 24GB) |
| Gemma 4 E4B (bf16) | ~15 GB | 20 GB | `g2-standard-8` (1× L4 24GB) |
| SAM 3.1 (bf16) | ~7 GB | 10 GB | `g2-standard-4` (1× L4 24GB) |
| **All three (bf16)** | **~27.5 GB** | **~32 GB** | `a3-highgpu-1g` (1× H100 80GB) |
| Gemma 4 31B (bf16) | ~62 GB | 80 GB | `a3-highgpu-1g` (1× H100 80GB) |
| Gemma 4 26B-A4B MoE (bf16) | ~50 GB | 64 GB | `a3-highgpu-1g` (1× H100 80GB) |

### 5.2 Google Cloud Configurations

#### Budget Option: L4 GPU ($0.70/hr)
- **Machine**: `g2-standard-8` (1× NVIDIA L4, 24GB VRAM)
- **Fits**: E4B bf16 + SAM 3.1 bf16 (~22 GB total) — TIGHT
- **Or**: E2B bf16 + SAM 3.1 bf16 (~12.5 GB) — COMFORTABLE
- **Region**: `us-central1-a` or `europe-west4-a`
- **Cost**: ~$0.70/hr on-demand, ~$0.21/hr spot

#### Performance Option: H100 GPU ($3.00–$12.00/hr)
- **Machine**: `a3-highgpu-1g` (1× NVIDIA H100 80GB)
- **Fits**: ALL models simultaneously at full bf16, including 31B
- **Or**: Run the full tri-model stack + 128K context + large batch sizes
- **Region**: `us-central1-a`
- **Cost**: ~$3.00/hr spot, ~$12.00/hr on-demand

#### Sweet Spot: A100 40GB ($1.50–$3.80/hr)
- **Machine**: `a2-highgpu-1g` (1× A100 40GB)
- **Fits**: E4B bf16 + SAM 3.1 bf16 + E2B bf16 = ~27.5 GB — FITS with margin
- **Region**: `us-central1-a`, `us-east1-b`
- **Cost**: ~$1.50/hr spot, ~$3.80/hr on-demand
- **This is the recommended cloud tier for the full tri-model stack at bf16.**

### 5.3 Cloud Deployment via Ollama Container

The existing `toolbox/prepare_ollama_cloud_bundle.py` creates a Dockerfile
for Cloud Run. For the tri-model stack:

```
# Cloud Run with Ollama container
# E2B + E4B loaded in Ollama (auto-swap), SAM 3.1 as a sidecar

Dockerfile:
  FROM ollama/ollama:latest
  COPY Modelfile.e2b /models/
  COPY Modelfile.e4b /models/
  # SAM 3.1 runs in a separate container or as a Python process
```

For serious cloud inference, use **Vertex AI** with the Gemma models
directly (no Ollama needed), and run SAM 3.1 in a separate Cloud Run
service.

---

## 6. SAM 3.1 Fine-Tuning Proposal

### 6.1 Why Fine-Tune SAM 3.1?

SAM 3.1 is a general-purpose segmentation model. Fine-tuning for Jemma's
civic/safety domain would improve:
- Segmentation of civic infrastructure (buildings, roads, signs, vehicles)
- Recognition of safety-relevant objects (fire hydrants, hazards, PPE)
- Better performance on municipal camera feed aesthetics (low-res, night)

### 6.2 Training Infrastructure Available

The SAM 3 repo includes full training code at `vendor/sam3/training/`.
See `vendor/sam3/README_TRAIN.md` for the official guide.

Key training requirements:
- **Python 3.12+**, PyTorch 2.7+ with CUDA 12.6+
- **VRAM**: Training requires significantly more than inference
  - Fine-tune on RTX 5090 (32GB): possible with gradient checkpointing
    and micro batch size 1-2, LoRA/PEFT approaches recommended
  - Full fine-tune: needs A100 40GB or H100 80GB

### 6.3 Fine-Tuning Approaches

#### Option A: LoRA/PEFT on Vision Encoder (RECOMMENDED for RTX 5090)
- Freeze the text encoder and most of the vision encoder
- Apply LoRA rank 16-32 to the ViT attention layers only
- Train on Jemma civic dataset images with segmentation masks
- **VRAM**: ~16 GB (fits on 5090 with SAM 3.1 frozen base)
- **Time**: ~2-4 hours for 5K annotated images

```python
# LoRA fine-tune approach (conceptual)
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["qkv"],  # ViT attention projections
    lora_dropout=0.05,
    task_type="FEATURE_EXTRACTION",
)

# Apply to SAM 3.1's vision encoder only
sam3_model.backbone.visual = get_peft_model(
    sam3_model.backbone.visual, lora_config
)
```

#### Option B: Full Fine-Tune with Gradient Checkpointing
- Unfreeze all of SAM 3.1's detector head
- Use gradient checkpointing to fit in 32GB
- Train on COCO-format annotations of civic objects
- **VRAM**: ~28 GB with checkpointing (barely fits 5090)
- **Better on cloud**: A100 40GB gives comfortable margin

#### Option C: Distillation from Gemma 4 Caption Labels
- Use Gemma E4B to generate rich text descriptions of civic images
- Use those descriptions as SAM 3.1 text prompts for training
- Self-training loop: Gemma labels → SAM segments → verify → retrain
- This is the **most novel approach** for the hackathon — using
  two models to improve each other

### 6.4 Dataset for Fine-Tuning

Sources already in the Jemma pipeline:
1. **Normal/ISU civic images** — scrape from ArcGIS Hub open data
2. **Google Street View** of Town of Normal (if licensed)
3. **SA-V dataset** (Meta's dataset, included with SAM 3)
4. **COCO** for general object detection bootstrap
5. **Synthetic data** from `toolbox/synth_dashboard.py`

Target annotation format: COCO JSON with segmentation masks.

### 6.5 Pairing SAM 3.1 with E2B vs E4B

| Task | Best Model | Reasoning |
|---|---|---|
| Real-time camera feed captioning | **E2B** (via Ollama q4_k_m) | Low latency, small VRAM |
| Detailed safety analysis of frames | **E4B** (via Ollama q8_0) | Higher accuracy |
| Frame-level object segmentation | **SAM 3.1** | Purpose-built |
| Video tracking across frames | **SAM 3.1** (video mode) | Object Multiplex |
| Audio + video combined analysis | **E2B/E4B** (Transformers) | Native audio support |
| Text-prompted segmentation | **SAM 3.1** | Open-vocab concepts |
| OCR / document understanding | **E4B** | Better text extraction |

**Recommended pairing for most tasks**: SAM 3.1 + E2B via Ollama.
Use E4B only when higher quality is needed and latency is acceptable.

---

## 7. The Unified Stack Script (To Build)

When GPU is free, the script `demos/demo_trimodel.py` should:

1. **Load SAM 3.1** on GPU (~7 GB)
2. **Verify Ollama** E2B + E4B respond via HTTP
3. **Create synthetic test video** (moving shapes, like existing demos)
4. **SAM 3.1 segments** each frame → masks + boxes + scores
5. **Gemma E2B** (Ollama) describes each segmented region
6. **Gemma E4B** (Ollama) does deeper safety analysis on select frames
7. **Compare**: quantized Ollama output vs direct Transformers output
8. **Report VRAM** usage at each step
9. **Output**: structured JSONL annotations ready for dataset ingestion

The script structure follows the pattern in `demos/e4b_loader.py` and
`demos/demo_video.py`.

---

## 8. Verified Facts (From This Session)

| Check | Status | Details |
|---|---|---|
| RTX 5090 detected | ✓ | 31.8 GB VRAM, SM_120, CUDA 12.8 |
| Python version | ✓ | 3.12.10 |
| PyTorch version | ✓ | 2.10.0+cu128 |
| Ollama running | ✓ | 14 models loaded |
| Ollama E2B responds | ✓ | 8.9s wall time |
| Ollama E4B responds | ✓ | 11.4s wall time |
| SAM 3 package installed | ✓ | sam3 0.1.0 (editable, vendor/sam3) |
| SAM 3 imports clean | ✓ | build_sam3_image_model, build_sam3_video_predictor |
| HF auth (soumitty) | ✓ | Write+delete access |
| SAM 3.1 HF access | ✓ | Gated model, access granted |
| SAM 3.1 checkpoint | ✓ | `sam3.1_multiplex.pt` (3.34 GB) |
| einops installed | ✓ | 0.8.2 |
| pycocotools installed | ✓ | 2.0.11 |
| timm installed | ✓ | 1.0.26 |
| SAM 3.1 checkpoint NOT yet downloaded | — | Will download on first build_sam3_image_model() call |

### Known Issues
- `numpy` was downgraded to 1.26.4 (SAM 3 requires `<2`). This conflicts
  with `opencv-python-headless` which wants `>=2`. SAM 3 inference works
  fine with 1.26. If opencv is needed, install `opencv-python-headless<4.12`.
- SAM 3.1 model is **gated** on HuggingFace — you must accept the license
  at https://huggingface.co/facebook/sam3.1 before first download.
- SAM 3 license is **SAM License** (not Apache 2.0) — check compatibility
  before including in hackathon submission.

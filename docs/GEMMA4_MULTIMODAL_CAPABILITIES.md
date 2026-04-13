# Gemma 4 Multimodal Capabilities Reference

> **Source**: Official Google AI documentation as of April 2026
> **License**: Apache 2.0

## Model Family Overview

Gemma 4 is a family of multimodal models handling text + image input (with audio/video on smaller models) and generating text output. All models share a hybrid attention mechanism (sliding window local + full global, final layer always global).

## Capability Matrix

| Capability | E2B (2.3B eff) | E4B (4.5B eff) | 31B (dense) | 26B-A4B (MoE) |
|---|:---:|:---:|:---:|:---:|
| **Text** | ✅ | ✅ | ✅ | ✅ |
| **Image** | ✅ | ✅ | ✅ | ✅ |
| **Audio** | ✅ | ✅ | ❌ | ❌ |
| **Video (native)** | ✅ | ✅ | frames only | frames only |
| **Function Calling** | ✅ | ✅ | ✅ | ✅ |
| **Thinking** | ✅ | ✅ | ✅ | ✅ |
| **System Prompts** | ✅ | ✅ | ✅ | ✅ |
| **Context Window** | 128K | 128K | 256K | 256K |
| **Sliding Window** | 512 | 512 | 1024 | 1024 |
| **Vocabulary** | 262K | 262K | 262K | 262K |

## Architecture Details

| Spec | E2B | E4B | 31B | 26B-A4B |
|---|---|---|---|---|
| Total Parameters | 5.1B (with PLE) | 8B (with PLE) | 30.7B | 25.2B |
| Effective Parameters | 2.3B | 4.5B | 30.7B | 3.8B active |
| Layers | 35 | 42 | 60 | 30 |
| Vision Encoder | ~150M | ~150M | ~550M | ~550M |
| Audio Encoder | ~300M | ~300M | None | None |
| Expert Config | — | — | — | 8 active / 128 total + 1 shared |

- **PLE** (Per-Layer Embeddings): Each decoder layer has its own small embedding table per token. Tables are large but only used for lookups, so effective parameter count is much smaller than total.
- **MoE**: 26B-A4B loads all 25.2B params but activates only 3.8B per token → runs nearly as fast as a 4B model.

## VRAM Requirements

| Model | BF16 | INT8 | INT4 (QLoRA) |
|---|---|---|---|
| E2B | 9.6 GB | 4.6 GB | **3.2 GB** |
| E4B | 15 GB | 7.5 GB | **5 GB** |
| 31B | 58.3 GB | 30.4 GB | **17.4 GB** |
| 26B-A4B | 48 GB | 25 GB | **15.6 GB** |

## Image Understanding (All Models)

### Capabilities
- Visual QA, scene description, image captioning
- OCR (multilingual — demonstrated with Japanese)
- Object detection with bounding boxes (normalized 1000x1000 grid)
- Document/PDF parsing, screen/UI understanding
- Chart comprehension, handwriting recognition, pointing
- Interleaved multimodal: freely mix text and images in any order

### Variable Resolution (Token Budget)
Controls how many visual tokens represent an image. Higher budget = more detail, more compute.

| Budget | Tokens | Best For |
|---|---|---|
| 70 | ~64 | Classification, captioning, video frames |
| 140 | ~121 | General understanding |
| 280 | ~256 | Standard object detection |
| 560 | ~529 | Detailed detection, OCR |
| 1120 | ~1024+ | Fine-grained OCR, document parsing, small text |

Set via: `processor.image_processor.max_soft_tokens = 560`

### Code Pattern
```python
from transformers import AutoProcessor, AutoModelForMultimodalLM

model = AutoModelForMultimodalLM.from_pretrained(MODEL_ID, dtype="auto", device_map="auto")
processor = AutoProcessor.from_pretrained(MODEL_ID)

messages = [
    {"role": "user", "content": [
        {"type": "image", "url": "https://example.com/photo.jpg"},
        {"type": "text", "text": "Describe this image."}
    ]}
]

inputs = processor.apply_chat_template(messages, tokenize=True, return_dict=True, return_tensors="pt", add_generation_prompt=True).to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512)
response = processor.decode(outputs[0], skip_special_tokens=False)
```

### Local Image Loading
```python
from PIL import Image
messages = [
    {"role": "user", "content": [
        {"type": "image", "image": Image.open("local_file.jpg").convert("RGB")},
        {"type": "text", "text": "What is in this image?"}
    ]}
]
```

## Audio Understanding (E2B and E4B ONLY)

### Specs
- Max duration: **30 seconds**
- Sample rate: **16 kHz mono**
- Format: 32-bit float [-1, 1]
- Token rate: ~25 tokens/second
- Encoder: ~300M parameters

### Capabilities
- **ASR** (Automatic Speech Recognition): Transcribe speech to text
- **AST** (Automatic Speech Translation): Transcribe + translate across languages

### Recommended Prompts

**ASR:**
```
Transcribe the following speech segment in {LANGUAGE} into {LANGUAGE} text.

Follow these specific instructions for formatting the answer:
*   Only output the transcription, with no newlines.
*   When transcribing numbers, write the digits, i.e. write 1.7 and not one point seven, and write 3 instead of three.
```

**AST:**
```
Transcribe the following speech segment in {SOURCE_LANGUAGE}, then translate it into {TARGET_LANGUAGE}.
When formatting the answer, first output the transcription in {SOURCE_LANGUAGE}, then one newline, then output the string '{TARGET_LANGUAGE}: ', then the translation in {TARGET_LANGUAGE}.
```

### Code Pattern
```python
messages = [
    {"role": "user", "content": [
        {"type": "audio", "audio": "path/to/audio.wav"},
        {"type": "text", "text": "Transcribe the following speech segment in English into English text."}
    ]}
]

inputs = processor.apply_chat_template(messages, tokenize=True, return_dict=True, return_tensors="pt", add_generation_prompt=True).to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512)
```

## Video Understanding (Native on E2B/E4B; frame-based on 31B/26B-A4B)

### Specs
- Max duration: **60 seconds** (at 1 fps)
- Processes videos as sequences of frames
- Lower token budgets recommended per frame

### Code Pattern
```python
messages = [
    {"role": "user", "content": [
        {"type": "video", "video": "https://example.com/video.mp4"},
        {"type": "text", "text": "Describe this video."}
    ]}
]

inputs = processor.apply_chat_template(messages, tokenize=True, return_dict=True, return_tensors="pt", add_generation_prompt=True).to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512)
```

## Function Calling (All Models)

### Native Tool Use
Gemma 4 has built-in function calling via special tokens. Supports JSON schema or raw Python functions.

### Code Pattern
```python
def get_current_weather(location: str, unit: str = "celsius"):
    """Gets the current weather in a given location.
    Args:
        location: The city and state, e.g. "San Francisco, CA"
        unit: The unit for temperature. (choices: ["celsius", "fahrenheit"])
    Returns:
        temperature: The current temperature
        weather: The current weather condition
    """
    return {"temperature": 15, "weather": "sunny"}

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather in Tokyo?"},
]

text = processor.apply_chat_template(messages, tools=[get_current_weather], tokenize=False, add_generation_prompt=True)
```

### Tool Call Parsing
```python
import re

def extract_tool_calls(text):
    def cast(v):
        try: return int(v)
        except:
            try: return float(v)
            except: return {'true': True, 'false': False}.get(v.lower(), v.strip("'\""))

    return [{
        "name": name,
        "arguments": {
            k: cast((v1 or v2).strip())
            for k, v1, v2 in re.findall(r'(\w+):(?:<\|"\|>(.*?)<\|"\|>|([^,}]*))', args)
        }
    } for name, args in re.findall(r"<\|tool_call>call:(\w+)\{(.*?)\}<tool_call\|>", text, re.DOTALL)]
```

### Multi-Turn Tool Response Format
```python
message.append({
    "role": "assistant",
    "tool_calls": [{"function": call} for call in calls],
    "tool_responses": [
        {"name": function_name, "response": function_response}
    ]
})
```

## Thinking Mode (All Models)

- Enable: `enable_thinking=True` in `apply_chat_template()` or `<|think|>` token in system prompt
- Output structure: `<|channel>thought\n[reasoning]<channel|>[answer]`
- Parse with: `processor.parse_response(response)`
- Works with function calling for improved tool-use accuracy
- E2B/E4B: if thinking disabled, model still generates tags with empty thought block

## Best Practices

1. **Sampling**: `temperature=1.0`, `top_p=0.95`, `top_k=64`
2. **Modality order**: Place image/audio content BEFORE text in prompts
3. **Multi-turn**: Historical model output should only include final response (strip thoughts)
4. **Variable resolution**: Use lower budgets for video/classification, higher for OCR/documents

## Fine-Tuning Reference

### Vision QLoRA (Official Google Recipe)

**Stack**: `transformers` + `trl` + `peft` + `bitsandbytes`

**Dataset format** (multimodal conversation):
```json
{"messages": [
  {"role": "system", "content": "You are..."},
  {"role": "user", "content": [
    {"type": "text", "text": "..."},
    {"type": "image"}
  ]},
  {"role": "assistant", "content": [{"type": "text", "text": "..."}]}
]}
```

**Model loading**:
```python
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig

model_kwargs = dict(dtype=torch.bfloat16, device_map="auto")
model_kwargs["quantization_config"] = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_storage=torch.bfloat16,
)

model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
processor = AutoProcessor.from_pretrained("google/gemma-4-E2B-it")
```

**LoRA config**:
```python
from peft import LoraConfig

peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.05,
    r=16,
    bias="none",
    target_modules="all-linear",
    task_type="CAUSAL_LM",
    modules_to_save=["lm_head", "embed_tokens"],  # CRITICAL for special tokens
    ensure_weight_tying=True,
)
```

**Training config**:
```python
from trl import SFTConfig

args = SFTConfig(
    output_dir="gemma-product-description",
    num_train_epochs=3,
    per_device_train_batch_size=1,
    optim="adamw_torch_fused",
    logging_steps=5,
    save_strategy="epoch",
    eval_strategy="epoch",
    learning_rate=2e-4,
    bf16=True,
    max_grad_norm=0.3,
    lr_scheduler_type="constant",
    push_to_hub=True,
    report_to="tensorboard",
    dataset_text_field="",                        # dummy for collator
    dataset_kwargs={"skip_prepare_dataset": True}, # important
    remove_unused_columns=False,                   # important
)
```

**Custom collator** (critical — handles image processing):
```python
def collate_fn(examples):
    texts, images = [], []
    for example in examples:
        image_inputs = process_vision_info(example["messages"])
        text = processor.apply_chat_template(
            example["messages"], add_generation_prompt=False, tokenize=False
        )
        texts.append(text.strip())
        images.append(image_inputs)

    batch = processor(text=texts, images=images, return_tensors="pt", padding=True)

    # Mask non-text tokens in loss
    labels = batch["input_ids"].clone()
    labels[labels == processor.tokenizer.pad_token_id] = -100
    labels[labels == processor.tokenizer.boi_token_id] = -100
    labels[labels == processor.tokenizer.image_token_id] = -100
    labels[labels == processor.tokenizer.eoi_token_id] = -100
    batch["labels"] = labels
    return batch
```

**Trainer**:
```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    args=args,
    train_dataset=dataset_train,
    eval_dataset=dataset_test,
    peft_config=peft_config,
    processing_class=processor,
    data_collator=collate_fn,
)
trainer.train()
```

### Available Fine-Tuning Tutorials
| Tutorial | URL |
|---|---|
| Text QLoRA | `ai.google.dev/gemma/docs/core/huggingface_text_finetune_qlora` |
| Vision QLoRA | `ai.google.dev/gemma/docs/core/huggingface_vision_finetune_qlora` |
| Full model fine-tune | `ai.google.dev/gemma/docs/core/huggingface_text_full_finetune` |
| LoRA with Keras | `ai.google.dev/gemma/docs/core/lora_tuning` |
| Distributed tuning | `ai.google.dev/gemma/docs/core/distributed_tuning` |
| Spoken language tasks | `ai.google.dev/gemma/docs/spoken-language/task-specific-tuning` |

### HuggingFace Model IDs
| Model | Base | Instruct |
|---|---|---|
| E2B | `google/gemma-4-E2B` | `google/gemma-4-E2B-it` |
| E4B | `google/gemma-4-E4B` | `google/gemma-4-E4B-it` |
| 31B | `google/gemma-4-31B` | `google/gemma-4-31B-it` |
| 26B-A4B | `google/gemma-4-26B-A4B` | `google/gemma-4-26B-A4B-it` |

### Unsloth Checkpoints
| Model | HuggingFace ID |
|---|---|
| E2B | `unsloth/gemma-4-E2B-it` |
| E4B | `unsloth/gemma-4-E4B-it` |

> **Note**: Unsloth currently optimizes text-only QLoRA. For multimodal (vision/audio) fine-tuning, use raw `transformers` + `trl` + `peft` as shown above.

## Benchmark Highlights

| Benchmark | 31B | 26B-A4B | E4B | E2B |
|---|---|---|---|---|
| MMLU Pro | 85.2% | 82.6% | 69.4% | 60.0% |
| AIME 2026 (no tools) | 89.2% | 88.3% | 42.5% | 37.5% |
| LiveCodeBench v6 | 80.0% | 77.1% | 52.0% | 44.0% |
| GPQA Diamond | 84.3% | 82.3% | 58.6% | 43.4% |
| MMMU Pro (vision) | 76.9% | 73.8% | 52.6% | 44.2% |
| OmniDocBench (lower=better) | 0.131 | 0.149 | 0.181 | 0.290 |
| MATH-Vision | 85.6% | 82.4% | 59.5% | 52.4% |
| CoVoST (audio) | — | — | 35.54 | 33.47 |
| FLEURS (audio, lower=better) | — | — | 0.08 | 0.09 |
| MRCR v2 128k (long context) | 66.4% | 44.1% | 25.4% | 19.1% |

---

## Jemma Architecture Mapping

### Hybrid Deployment Strategy

| Target | Model | Modalities | Role |
|---|---|---|---|
| **Pixel phone** | E2B (q4_k_m) | Text+Image+Audio+Video | On-device civic data collection: photos, meeting audio, traffic video |
| **RTX 5090 workstation** | E4B (q8_0) | Text+Image+Audio+Video | Primary multimodal processor: all modalities at higher quality |
| **RTX 5090 workstation** | 31B (q4_k_m) | Text+Image | Heavy reasoning: document analysis, policy synthesis, safety evaluation |
| **Cloud API** | Any | All | Fallback and batch processing |

### Town of Normal Data Pipeline

| Data Source | Modality | Best Model | Notes |
|---|---|---|---|
| Town meeting recordings | Audio → Text | E4B (ASR) | 30s chunks, 16kHz mono |
| Budget PDFs | Image (rendered pages) | 31B or E4B | High token budget for OCR |
| GIS maps | Image | E4B or 31B | Variable resolution, object detection |
| Building permits | Image + Text | E4B or 31B | Document parsing |
| ArcGIS portal data | Text (JSON/CSV) | 31B | Structured data analysis |
| Infrastructure inspection photos | Image | E4B | Object detection, condition assessment |
| Traffic camera footage | Video | E4B | Native video, 60s max at 1fps |
| Municipal code text | Text | 31B | 256K context for full documents |
| Council agenda/minutes | Text + Image (scans) | 31B | Long-form analysis |

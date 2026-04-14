---
description: "Run multimodal demos showing Gemma 4 capabilities across text, image, audio, and video"
agent: "agent"
argument-hint: "Which demos to run: all, text, image, audio, video, function-calling"
tools: [execute, read, search]
---
Run the Gemma 4 multimodal demo suite to verify capabilities.

Environment setup: `.\.venv_multimodal\Scripts\Activate.ps1`

Available demos in `demos/`:
- `demo_text.py` — Basic text chat completions
- `demo_image.py` — Image understanding (vision)
- `demo_audio.py` — Audio processing (E2B/E4B only, 30s max)
- `demo_video.py` — Video analysis (E2B/E4B only, 60s@1fps)
- `demo_function_calling.py` — Native function calling
- `run_all_demos.py` — All demos in sequence

Run with: `$env:PYTHONUNBUFFERED=1; & .\.venv_multimodal\Scripts\python.exe -u -W ignore demos/<script>.py`

Report results: which modalities succeeded, inference speed, any errors.

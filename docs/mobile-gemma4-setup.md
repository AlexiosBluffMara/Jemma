# Mobile Gemma 4 setup

## Primary architecture
The primary mobile architecture is remote-first:

- run Gemma 4 on the RTX 5090 workstation through Ollama,
- expose the Jemma FastAPI control plane on the workstation and use the phone as a client over the local network,
- keep an on-device E2B fallback only for offline use.

This is the only practical way to preserve long context and stable quality on both phones.

The repository now includes a native Android client in `android-app/` that targets this path first:

- Android app talks to `http://<workstation-ip>:8000/api`,
- Jemma backend talks to local Ollama at `http://127.0.0.1:11434`,
- `gemma4-e4b-it:q8_0` remains the main remote model,
- `gemma4-e2b-it:q4_k_m` stays a later offline/mobile fallback only.

## Pixel Fold 9 priority path
Use the Pixel as the first mobile target.

### Same-LAN path
1. Keep Ollama and the Jemma backend on the workstation.
2. Put the Pixel on the same trusted network.
3. Run `python -m jemma.cli serve-api --host 0.0.0.0 --port 8000` on the workstation only when you are on a trusted LAN.
4. Point the Android client at `http://<workstation-ip>:8000/`.
5. Let the backend keep using `gemma4-e4b-it:q8_0` as the main remote model.

### USB path
If you want a cable-only connection, use `adb reverse`:

```bash
./toolbox/pixel_fold_adb_reverse.sh
```

This exposes the workstation's port `11434` as `127.0.0.1:11434` on the Pixel.
For the Android app, also reverse the API port:

```bash
adb reverse tcp:8000 tcp:8000
```

Then use `http://127.0.0.1:8000/` inside the Android client.

## iPhone 16 Pro Max path
Treat the iPhone as a same-LAN client first.

- Use the workstation-hosted Jemma API endpoint.
- Avoid trying to build a USB-only path on Linux for the first pass.
- Keep offline deployment as a later optimization.

## On-device fallback
If you need offline usage on the phone, export a quantized E2B variant.

Recommended target:
- E2B quantized for GGUF-compatible mobile runtimes

Do not treat E4B or 31B as the first offline phone target.

## Context guidance
- Remote workstation path: use the full 128K-class context where needed.
- Phone-local fallback: expect much smaller practical contexts.
- Keep long documents, large retrieval payloads, and agentic workflows on the workstation.
- Do not claim unvalidated on-device multimodal parity or tool-calling parity on mobile; the current app is chat and control-plane oriented.

## Security guidance
- Keep both the Jemma API and Ollama endpoints on a trusted network only.
- Do not expose either endpoint publicly.
- Prefer a firewall rule, VPN, or private LAN over wide-open binding.

## Recommended mobile split
- Workstation quality path: `gemma4-e4b-it:q8_0`
- Mobile and offline fallback: `gemma4-e2b-it:q4_k_m`

## Android app surfaces
The Android module implements these remote-first surfaces with Material 3 cards and adaptive foldable layouts:

- Home benchmark tiles
- Chat
- Prompt Lab
- Skills
- Benchmarks
- Models
- System

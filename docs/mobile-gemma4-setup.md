# Mobile Gemma 4 setup

## Primary architecture
The primary mobile architecture is remote-first:

- run Gemma 4 on the RTX 5090 workstation through Ollama,
- use the phone as a client over the local network,
- keep an on-device E2B fallback only for offline use.

This is the only practical way to preserve long context and stable quality on both phones.

## Pixel Fold 9 priority path
Use the Pixel as the first mobile target.

### Same-LAN path
1. Keep Ollama on the workstation.
2. Put the Pixel on the same trusted network.
3. Point the mobile client at `http://<workstation-ip>:11434` or the OpenAI-compatible `http://<workstation-ip>:11434/v1` endpoint.
4. Use `gemma4-e4b-it:q8_0` as the main remote model.

### USB path
If you want a cable-only connection, use `adb reverse`:

```bash
./toolbox/pixel_fold_adb_reverse.sh
```

This exposes the workstation's port `11434` as `127.0.0.1:11434` on the Pixel.

## iPhone 16 Pro Max path
Treat the iPhone as a same-LAN client first.

- Use the workstation-hosted Ollama endpoint.
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

## Security guidance
- Keep the Ollama endpoint on a trusted network only.
- Do not expose the endpoint publicly.
- Prefer a firewall rule, VPN, or private LAN over wide-open binding.

## Recommended mobile split
- Workstation quality path: `gemma4-e4b-it:q8_0`
- Mobile and offline fallback: `gemma4-e2b-it:q4_k_m`

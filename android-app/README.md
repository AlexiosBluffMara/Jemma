# Jemma Android app

Native Android client for the remote-first Jemma control plane.

## Highlights
- Kotlin + Jetpack Compose Material 3
- Foldable-aware adaptive navigation
- Remote-first chat against the workstation-hosted FastAPI backend
- Public-demo-safe surfaces: Home, Chat, Prompt Lab, Skills, Benchmarks, Models, System

## Expected connection model
- Android app -> `http://<workstation-ip>:8000/`
- Jemma backend -> local Ollama on `http://127.0.0.1:11434`

Start the backend with a network-visible bind on a trusted LAN:

```bash
python -m jemma.cli serve-api --host 0.0.0.0 --port 8000
```

## Open in Android Studio
Open the `android-app/` directory as a standalone Gradle project.

If you are using a USB-connected Pixel test device, you can also bridge the backend with:

```bash
adb reverse tcp:8000 tcp:8000
```

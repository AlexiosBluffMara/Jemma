# Google Cloud + Ollama deployment from notebook exports

This is the canonical path for taking the local 5090 Unsloth workflow and turning it into a hosted Ollama deployment on Google Cloud.

## Recommended artifact order
1. Run `gemma4-31b-unsloth-local-5090.ipynb` locally on the 5090.
2. Save the LoRA adapter first.
3. Re-run with `JEMMA_SAVE_GGUF=1` when you are ready to deploy through Ollama.
4. Use the generated deployment manifest to build a Cloud Run bundle.

## 1. Run the notebook and keep the deployment manifest
The notebook executor now writes a deployment manifest next to the export directory:

```powershell
set JEMMA_NOTEBOOK_PYTHON=D:\unsloth\studio\.venv\Scripts\python.exe
set JEMMA_SAVE_GGUF=1
python FINAL_NOTEBOOK_RUNNER.py
```

After a successful run, look for a file like:

```text
D:\JemmaData\exports\gemma4-e4b-second-brain-deployment-manifest.json
```

That manifest captures the artifact slug, model choice, dataset source, and the exported GGUF path.

## 2. Build the Ollama + Google Cloud bundle

```powershell
python toolbox\prepare_ollama_cloud_bundle.py D:\JemmaData\exports\gemma4-e4b-second-brain-deployment-manifest.json
```

This creates a self-contained bundle with:

- `Dockerfile`
- `Modelfile`
- `entrypoint.sh`
- `deploy-cloud-run.ps1`
- `bundle-manifest.json`

## 3. Deploy to Google Cloud Run
Open the generated bundle directory and run:

```powershell
.\deploy-cloud-run.ps1 -ProjectId YOUR_GCP_PROJECT -Region us-central1 -ServiceName jemma-gemma4-e4b
```

Safe default: use Cloud Run for public demos, low-volume hosted testing, or stakeholder review links. If you need tighter GPU control, longer-lived model residency, or more predictable latency, use the same bundle as the base for GCE or GKE instead of treating Cloud Run as the only target.

## 4. Verify the hosted Ollama endpoint
Once deployed, the service exposes the Ollama HTTP API. Point your client or Jemma config at the resulting base URL.

Example:

```powershell
curl https://YOUR-SERVICE-URL/api/tags
```

## Notes
- The simplest Ollama path is GGUF, so the bundle generator requires a GGUF export.
- Keep the local Ollama workflow in `docs/local-gemma4-ollama-setup.md` as the source-of-truth workstation setup.
- Keep 31B for late-stage comparisons; E4B and E2B remain the default deployment ladder.

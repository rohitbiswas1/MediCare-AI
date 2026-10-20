# Isolated research inference

Run from the repository root with the ML environment:

```bash
uv run --frozen --project ml uvicorn services.inference.main:app --port 8001
```

Set `INFERENCE_SERVICE_KEY` securely. Keep this service on a private network; public ingress is not intended. `ALLOW_RESEARCH_INFERENCE=false` is the default. `/ecg` accepts an NPZ containing `waveform` (12 × 1000 float samples), scalar `sampling_rate=100`, and named `leads`. Paper photographs are rejected. `/xray` accepts a PNG/JPEG and a verified `view=AP|PA` field. View is not guessed from pixels.

An opted-in research run additionally needs artifacts under `MODEL_ARTIFACT_ROOT/ecg` or `/xray`. The loader checks both weights and evaluation SHA-256, label metadata, and experimental status, and uses PyTorch `weights_only=True`. Output probabilities are research estimates, not medical confidence. Production mode rejects all such artifacts. The patient-facing application never sends a record to this research service. `services/api/app/inference.py` defines the validated integration contract for a future reviewed release.

No weights, region visualizations, clinical classifications, or approvals are bundled. New clinical functionality requires a separate assessed deployment and cannot be enabled by changing an artifact's status string.

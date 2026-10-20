# Medical ML research

These pipelines are executable research infrastructure, not validated medical products. No dataset, pretrained medical weight, calibration claim, diagnostic accuracy figure, or patient training record is bundled.

## Environment and resources

From the repository root:

```bash
uv sync --frozen --project ml
uv run --frozen --project ml python -m pytest tests/test_ml.py -q
```

The lock uses CPU PyTorch for repeatable development checks. A one-epoch synthetic smoke run verifies serialization, calibration, and gates; its metrics have no medical meaning. Full ECG training benefits from a GPU with roughly 8–12 GiB VRAM. DenseNet chest X-ray experiments commonly need 12–24 GiB depending on batch size/resolution. Benchmark your actual dataset and model. For GPU work, create a separate reviewed environment with a CUDA-compatible PyTorch build, driver/runtime, version lock, and deterministic settings. Do not silently change the application environment's lock.

## Datasets and isolation

Obtain PTB-XL from PhysioNet under its license, and CheXpert or MIMIC-CXR through their official access/license processes. This repository does not automate acceptance, credentialed download, or redistribution. Store approved research data outside patient uploads. Specify the exact dataset release and label definitions. Never export uploaded app records into these directories.

```bash
uv run --project ml python -m ml.datasets.prepare_ptbxl \
  --source /authorized/ptb-xl --output ml/data/ptbxl \
  --dataset-version YOUR_RELEASE --license-acknowledged

uv run --project ml python -m ml.datasets.prepare_chexpert \
  --csv /authorized/chexpert/train.csv --output ml/data/chexpert \
  --dataset-version YOUR_RELEASE --license-acknowledged
```

PTB-XL uses official folds 1–8 for training, 9 for validation, and 10 for testing, and validates patient isolation. The provided baseline predicts five diagnostic superclasses, not a clinically validated rhythm diagnosis. Rhythm-label experiments need a separately versioned label specification and validation. ECG arrays retain named leads, 100 Hz sampling rate, and a 10-second duration; flat/nonfinite/wrong-format signals fail quality checks. No photograph is converted into a waveform.

CheXpert preparation retains frontal studies and acquisition view metadata, masks missing/uncertain labels as -1, and splits by patient. `--data-root` must be the parent directory under which manifest paths resolve. The five baseline labels are Cardiomegaly, Edema, Consolidation, Atelectasis, and Pleural Effusion. There is no bundled MIMIC-CXR adapter or access approval; create a reviewed manifest using matching definitions after obtaining access.

## Training

```bash
uv run --project ml python -m ml.ecg.train \
  --manifest ml/data/ptbxl/manifest.csv --dataset-metadata ml/data/ptbxl/dataset.json \
  --data-root ml/data/ptbxl --output ml/artifacts/ecg --version ecg-research-v1 \
  --epochs 20 --batch-size 16 --seed 42 --threads 2 --device cpu

# Add --architecture transformer to explore the Hugging Face PatchTST backbone.
uv run --project ml python -m ml.xray.train \
  --manifest ml/data/chexpert/manifest.csv --dataset-metadata ml/data/chexpert/dataset.json \
  --data-root /authorized --output ml/artifacts/xray --version xray-research-v1 \
  --epochs 20 --batch-size 8 --seed 42 --threads 2 --device cpu
```

The ECG CNN and PatchTST architectures and MONAI DenseNet121 return multilabel logits. Training uses masked BCE, AdamW, gradient clipping, fixed seeds, deterministic PyTorch operations, patient-level manifests, and validation-loss checkpoint selection. Normalization and input sizes are shared with inference. The validation split alone fits scalar temperature scaling and operating thresholds. Insufficient positive/negative validation classes stop threshold fitting. The test split never tunes hyperparameters or thresholds.

Outputs: `weights.pt`, `model.json`, `evaluation.json`, and append-only `experiments.jsonl`. The model record includes dataset/version, ordered labels, manifest/weights/evaluation checksums, seed, patient counts, temperature, thresholds, limitations, and `status=experimental`. Use a new output directory per experiment; do not overwrite reviewed releases.

## Evaluation and governance

Metrics include sensitivity, specificity, AUROC, Brier score, and expected calibration error. Missing-class/fully masked cases return null instead of fabricated scores. Subgroup metrics are produced when `sex`/`age_group` columns exist. Small or unrepresentative subgroups need further evidence, not a fairness claim.

```bash
uv run --project ml python -m ml.evaluation.external \
  --artifact ml/artifacts/ecg --manifest /authorized/external/manifest.csv \
  --dataset-metadata /authorized/external/dataset.json \
  --training-manifest ml/data/ptbxl/manifest.csv --data-root /authorized/external \
  --output ml/artifacts/ecg/external-evaluation.json
```

External rows must use `split=external`; label definitions/order must match, the dataset identity must differ, and the original training manifest/weights must match their hashes. Establish real patient linkage across sources; dataset-scoped pseudonyms alone do not prove absence of overlapping people. External evaluation never automatically promotes an artifact to clinical status.

Complete [MODEL_CARD.md](MODEL_CARD.md), clinician review, suitable statistical uncertainty analysis, external/site/device validation, bias assessment, monitoring, privacy, and regulatory review before proposing clinical deployment. The supplied inference service remains experimental and rejects production mode. It has no automatic diagnostic release or saliency-map feature.

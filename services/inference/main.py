import io
import os
import secrets
import zipfile

import numpy as np
import torch
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from ml.ecg.model import signal_quality
from ml.xray.model import image_quality

from .registry import Registry

app = FastAPI(
    title="MediCare research inference",
    version="0.1.0",
    description="Private research service. No clinically approved predictions.",
)
Image.MAX_IMAGE_PIXELS = 25_000_000


def authorize(x_service_key: str = Header("")):
    expected = os.environ.get("INFERENCE_SERVICE_KEY", "")
    if not expected:
        raise HTTPException(503, "Inference service authentication is not configured.")
    if not secrets.compare_digest(expected, x_service_key):
        raise HTTPException(401, "Service authentication required.")


class Prediction(BaseModel):
    label: str
    probability: float
    threshold: float
    identified: bool


class ResearchResult(BaseModel):
    status: str = "experimental"
    clinical_use: bool = False
    model_version: str
    predictions: list[Prediction]
    quality: dict
    uncertainty: str = (
        "Probabilities use validation-set temperature scaling. They are not validated clinical confidence."
    )
    summary: str


def predict(modality, values, quality):
    if not quality["supported"]:
        raise HTTPException(422, {"message": "Unsupported acquisition quality.", "quality": quality})
    try:
        model, card = Registry().load(modality)
    except (OSError, ValueError, KeyError, RuntimeError):
        raise HTTPException(
            503, "No eligible verified research artifact is available. Clinical inference is disabled."
        )
    with torch.no_grad():
        probabilities = torch.sigmoid(model(torch.from_numpy(values.copy())[None]) / card["temperature"])[
            0
        ].numpy()
    if not np.isfinite(probabilities).all():
        raise HTTPException(503, "Model output failed validation.")
    predictions = [
        Prediction(
            label=name,
            probability=float(prob),
            threshold=float(threshold),
            identified=bool(prob >= threshold),
        )
        for name, prob, threshold in zip(card["labels"], probabilities, card["thresholds"])
    ]
    summary = "Experimental model output requires professional review; it is not a diagnosis."
    if not any(p.identified for p in predictions):
        summary = (
            "No supported finding identified by this model. This does not establish that the study is normal."
        )
    return ResearchResult(
        model_version=card["version"], predictions=predictions, quality=quality, summary=summary
    )


@app.get("/health")
def health():
    return {"status": "ok", "clinical_use": False}


@app.get("/capabilities", dependencies=[Depends(authorize)])
def capabilities():
    states = {}
    for modality in ["ecg", "xray"]:
        try:
            _, card = Registry().load(modality)
            states[modality] = {"status": "experimental", "version": card["version"]}
        except (OSError, ValueError, KeyError, RuntimeError):
            states[modality] = {"status": "unavailable"}
    return {"models": states, "clinical_use": False}


@app.post("/ecg", response_model=ResearchResult, dependencies=[Depends(authorize)])
async def ecg(file: UploadFile = File(...)):
    data = await file.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024 or not (file.filename or "").endswith(".npz"):
        raise HTTPException(
            422, "Provide a supported raw ECG NPZ archive up to 8 MB, not a paper photograph."
        )
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if sum(f.file_size for f in archive.infolist()) > 32 * 1024 * 1024:
                raise ValueError("Archive is too large")
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            values = archive["waveform"].astype(np.float32)
            quality = signal_quality(values, int(archive["sampling_rate"]), archive["leads"].tolist())
    except Exception:
        raise HTTPException(422, "ECG archive is invalid. Required arrays: waveform, sampling_rate, leads.")
    if quality["supported"]:
        values = (values - values.mean(axis=1, keepdims=True)) / np.maximum(
            values.std(axis=1, keepdims=True), 1e-6
        )
    return predict("ecg", values, quality)


@app.post("/xray", response_model=ResearchResult, dependencies=[Depends(authorize)])
async def xray(file: UploadFile = File(...), view: str = Form(...)):
    data = await file.read(15 * 1024 * 1024 + 1)
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Image is too large.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise ValueError("Unsupported image container")
            image = image.convert("L")
            quality = image_quality(image, view)
            values = np.asarray(image.resize((224, 224)), dtype=np.float32)[None] / 255
    except Exception:
        raise HTTPException(
            422, "Provide a supported chest radiograph PNG/JPEG with verified AP/PA view metadata."
        )
    return predict("xray", values, quality)

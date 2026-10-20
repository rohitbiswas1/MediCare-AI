"""Fail-closed research artifact loader. Not a clinical deployment approval system."""

import json
import os
from pathlib import Path

import torch

from ml.datasets.manifest import sha256
from ml.train import model_for


class Registry:
    def __init__(self, root=None):
        self.root = Path(root or os.environ.get("MODEL_ARTIFACT_ROOT", "/models"))

    def load(self, modality):
        if os.environ.get("APP_MODE", "development") == "production":
            raise ValueError("Clinical inference is not enabled in this release.")
        if os.environ.get("ALLOW_RESEARCH_INFERENCE") != "true":
            raise ValueError("Research inference is disabled.")
        directory = self.root / modality
        card = json.loads((directory / "model.json").read_text())
        if card.get("status") != "experimental" or card.get("modality") != modality:
            raise ValueError("Unsupported model release status or modality.")
        if card.get("clinical_use") is not False:
            raise ValueError("This service only accepts explicitly nonclinical research artifacts.")
        if sha256(directory / "weights.pt") != card["weights_sha256"]:
            raise ValueError("Weights checksum mismatch.")
        if sha256(directory / "evaluation.json") != card["evaluation_sha256"]:
            raise ValueError("Evaluation checksum mismatch.")
        if not 0.05 <= card["temperature"] <= 20 or len(card["thresholds"]) != len(card["labels"]):
            raise ValueError("Invalid calibration metadata.")
        model = model_for(modality, len(card["labels"]), card["architecture"])
        model.load_state_dict(torch.load(directory / "weights.pt", weights_only=True, map_location="cpu"))
        model.eval()
        return model, card

"""Reproducible research trainer. Clinical release is a separate, external governance process."""

import argparse
import importlib.metadata
import json
import os
import platform
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset

from ml.datasets.manifest import data_path, sha256, validate_manifest
from ml.ecg.model import ECGCNN, ECGTransformer, signal_quality
from ml.evaluation.metrics import evaluate, subgroup_metrics, validation_thresholds
from ml.xray.model import create_model, image_quality


def seed_all(seed):
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False


class MedicalDataset(Dataset):
    def __init__(self, frame, labels, root, modality):
        self.frame, self.labels, self.root, self.modality = (
            frame.reset_index(drop=True),
            labels,
            root,
            modality,
        )

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        row = self.frame.iloc[index]
        path = data_path(self.root, row.file)
        if self.modality == "ecg":
            with np.load(path, allow_pickle=False) as archive:
                values = archive["waveform"].astype(np.float32)
                quality = signal_quality(values, int(archive["sampling_rate"]), archive["leads"].tolist())
            if not quality["supported"]:
                raise ValueError("; ".join(quality["reasons"]))
            values = (values - values.mean(axis=1, keepdims=True)) / np.maximum(
                values.std(axis=1, keepdims=True), 1e-6
            )
        else:
            with Image.open(path) as image:
                image = image.convert("L")
                quality = image_quality(image, row.get("view"))
                if not quality["supported"]:
                    raise ValueError("; ".join(quality["reasons"]))
                values = np.asarray(image.resize((224, 224)), dtype=np.float32)[None] / 255
        return torch.from_numpy(values.copy()), torch.tensor(self.labels[index])


def model_for(modality, labels, architecture="cnn"):
    return (
        create_model(labels)
        if modality == "xray"
        else ECGTransformer(labels)
        if architecture == "transformer"
        else ECGCNN(labels)
    )


def masked_loss(logits, labels):
    mask = labels >= 0
    if not mask.any():
        raise ValueError("Batch contains no observed labels.")
    return nn.functional.binary_cross_entropy_with_logits(logits[mask], labels[mask])


def collect(model, loader, device):
    model.eval()
    truth, logits = [], []
    with torch.no_grad():
        for features, labels in loader:
            logits.append(model(features.to(device)).cpu())
            truth.append(labels)
    if not truth:
        raise ValueError("Selected split is empty.")
    return torch.cat(truth), torch.cat(logits)


def calibrate(labels, logits):
    log_temperature = torch.zeros(1, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=50)

    def closure():
        optimizer.zero_grad()
        loss = masked_loss(logits / log_temperature.exp().clamp(0.05, 20), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(log_temperature.exp().clamp(0.05, 20).detach())


def train(args):
    seed_all(args.seed)
    torch.set_num_threads(args.threads)
    metadata = json.loads(args.dataset_metadata.read_text())
    if not metadata.get("version") or not metadata.get("labels"):
        raise ValueError("Dataset version and label ordering must be recorded.")
    frame, labels = validate_manifest(args.manifest, len(metadata["labels"]))
    if not {"train", "validation", "test"}.issubset(frame.split.unique()):
        raise ValueError("Training requires distinct patient-level train, validation, and test splits.")
    loaders = {}
    for split in ["train", "validation", "test"]:
        mask = (frame.split == split).to_numpy()
        ds = MedicalDataset(frame[mask], labels[mask], args.data_root, args.modality)
        loaders[split] = DataLoader(ds, batch_size=args.batch_size, shuffle=split == "train", num_workers=0)
    device = torch.device(args.device)
    model = model_for(args.modality, labels.shape[1], args.architecture).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    args.output.mkdir(parents=True, exist_ok=True)
    best = float("inf")
    for epoch in range(args.epochs):
        model.train()
        losses = []
        for features, target in loaders["train"]:
            optimizer.zero_grad()
            loss = masked_loss(model(features.to(device)), target.to(device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(float(loss.detach()))
        truth, logits = collect(model, loaders["validation"], device)
        validation_loss = float(masked_loss(logits, truth))
        record = {
            "epoch": epoch + 1,
            "training_loss": float(np.mean(losses)),
            "validation_loss": validation_loss,
        }
        with (args.output / "experiments.jsonl").open("a") as log:
            log.write(json.dumps(record) + "\n")
        if validation_loss < best:
            best = validation_loss
            torch.save(model.state_dict(), args.output / "weights.pt")
    model.load_state_dict(torch.load(args.output / "weights.pt", map_location=device, weights_only=True))
    val_truth, val_logits = collect(model, loaders["validation"], device)
    temperature = calibrate(val_truth, val_logits)
    thresholds = validation_thresholds(val_truth.numpy(), torch.sigmoid(val_logits / temperature).numpy())
    test_truth, test_logits = collect(model, loaders["test"], device)
    probability = torch.sigmoid(test_logits / temperature).numpy()
    test_frame = frame[frame.split == "test"]
    evaluation = {
        "split": "test",
        "metrics": evaluate(test_truth.numpy(), probability, thresholds),
        "subgroups": {
            column: subgroup_metrics(test_frame, test_truth.numpy(), probability, thresholds, column)
            for column in ["sex", "age_group"]
        },
        "clinical_validation": False,
    }
    (args.output / "evaluation.json").write_text(json.dumps(evaluation, indent=2))
    card = {
        "version": args.version,
        "modality": args.modality,
        "architecture": args.architecture,
        "status": "experimental",
        "clinical_use": False,
        "external_validation": False,
        "labels": metadata["labels"],
        "dataset": metadata,
        "manifest_sha256": sha256(args.manifest),
        "weights_sha256": sha256(args.output / "weights.pt"),
        "evaluation_sha256": sha256(args.output / "evaluation.json"),
        "temperature": temperature,
        "thresholds": thresholds,
        "seed": args.seed,
        "training_config": {
            name: getattr(args, name)
            for name in ["epochs", "batch_size", "learning_rate", "seed", "threads", "device"]
        },
        "software_versions": {
            "python": platform.python_version(),
            **{
                name: importlib.metadata.version(name)
                for name in ["torch", "monai", "transformers", "numpy", "scikit-learn"]
            },
        },
        "environment_lock_sha256": sha256(Path(__file__).parent / "uv.lock"),
        "source_sha256": {
            name: sha256(Path(__file__).parent / name)
            for name in [
                "train.py",
                "ecg/model.py",
                "xray/model.py",
                "datasets/manifest.py",
                "evaluation/metrics.py",
            ]
        },
        "patients": {
            s: int(frame[frame.split == s].patient_id.nunique()) for s in ["train", "validation", "test"]
        },
        "limitations": [
            "Research only.",
            "External validation and clinical/regulatory review are required.",
            "Absence of a finding does not establish normality.",
        ],
    }
    (args.output / "model.json").write_text(json.dumps(card, indent=2))
    return card


def arguments(modality=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--modality", choices=["ecg", "xray"], default=modality, required=modality is None)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-metadata", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--architecture", choices=["cnn", "transformer"], default="cnn")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


if __name__ == "__main__":
    train(arguments())

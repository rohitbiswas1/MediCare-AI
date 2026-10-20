"""Synthetic engineering checks only. Passing does not validate medical performance."""

import json
from argparse import Namespace

import numpy as np
import pandas as pd
import pytest
import torch

from ml.datasets.manifest import assign_splits, validate_manifest
from ml.ecg.model import ECGCNN, ECGTransformer, signal_quality
from ml.evaluation.metrics import evaluate
from ml.train import train
from ml.xray.model import create_model
from services.inference.registry import Registry

LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]


def test_patient_split_and_leakage_rejection(tmp_path):
    frame = pd.DataFrame(
        [{"patient_id": str(i // 2), "file": f"{i}.npz", "labels": "[0, 1]"} for i in range(40)]
    )
    split = assign_splits(frame)
    assert split.groupby("patient_id").split.nunique().max() == 1
    path = tmp_path / "manifest.csv"
    split.to_csv(path, index=False)
    validate_manifest(path, 2)
    split.loc[0, "split"] = "external"
    split.to_csv(path, index=False)
    with pytest.raises(ValueError, match="leakage"):
        validate_manifest(path, 2)


def test_metrics_and_masked_labels():
    result = evaluate(
        np.array([[0, -1], [1, 1], [0, 0], [1, 1]]),
        np.array([[0.1, 0.8], [0.9, 0.9], [0.2, 0.1], [0.8, 0.9]]),
    )
    assert result[0]["sensitivity"] == 1 and result[0]["specificity"] == 1
    assert result[0]["auroc"] == 1 and result[1]["n"] == 3
    assert result[0]["ece"] > 0
    with pytest.raises(ValueError):
        evaluate(np.ones((2, 1)), np.array([[float("nan")], [0.4]]))


def test_signal_quality_does_not_accept_paper_or_flat_signal():
    assert not signal_quality(np.zeros((12, 1000)), 100, LEADS)["supported"]
    signal = np.random.default_rng(42).normal(size=(12, 1000))
    assert signal_quality(signal, 100, LEADS)["supported"]
    assert not signal_quality(signal, 500, LEADS)["supported"]


def test_research_architecture_shapes():
    torch.set_num_threads(2)
    with torch.no_grad():
        assert ECGCNN(5).eval()(torch.zeros(2, 12, 1000)).shape == (2, 5)
        assert ECGTransformer(5).eval()(torch.zeros(2, 12, 1000)).shape == (2, 5)
        assert create_model(5).eval()(torch.zeros(1, 1, 224, 224)).shape == (1, 5)


def test_training_artifact_and_integrity_gate(tmp_path, monkeypatch):
    rng = np.random.default_rng(123)
    rows = []
    for i in range(24):
        file = f"{i}.npz"
        np.savez(
            tmp_path / file,
            waveform=rng.normal(size=(12, 1000)).astype("float32"),
            sampling_rate=100,
            leads=LEADS,
        )
        rows.append(
            {
                "patient_id": str(i),
                "file": file,
                "labels": json.dumps([i % 2, (i // 2) % 2]),
                "split": "train" if i < 16 else "validation" if i < 20 else "test",
            }
        )
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    metadata = tmp_path / "dataset.json"
    metadata.write_text(
        json.dumps(
            {"name": "synthetic-engineering-only", "version": "1", "labels": ["synthetic_a", "synthetic_b"]}
        )
    )
    output = tmp_path / "artifacts" / "ecg"
    args = Namespace(
        seed=42,
        threads=2,
        dataset_metadata=metadata,
        manifest=manifest,
        modality="ecg",
        data_root=tmp_path,
        batch_size=4,
        device="cpu",
        architecture="cnn",
        learning_rate=0.001,
        output=output,
        epochs=1,
        version="engineering-test-only",
    )
    card = train(args)
    assert card["clinical_use"] is False and card["status"] == "experimental"
    assert card["external_validation"] is False
    monkeypatch.setenv("ALLOW_RESEARCH_INFERENCE", "true")
    monkeypatch.setenv("APP_MODE", "development")
    Registry(tmp_path / "artifacts").load("ecg")
    (output / "weights.pt").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        Registry(tmp_path / "artifacts").load("ecg")
    monkeypatch.setenv("APP_MODE", "production")
    with pytest.raises(ValueError, match="Clinical inference"):
        Registry(tmp_path / "artifacts").load("ecg")

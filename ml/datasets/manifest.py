"""Validate patient isolation before training; retain patient IDs only inside secured research data."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


def assign_splits(frame, seed=42):
    if frame.patient_id.nunique() < 10:
        raise ValueError("At least 10 unique patients are needed for a three-way split.")
    frame = frame.copy()
    train, remainder = next(
        GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(frame, groups=frame.patient_id)
    )
    remainder_frame = frame.iloc[remainder]
    val, test = next(
        GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=seed).split(
            remainder_frame, groups=remainder_frame.patient_id
        )
    )
    frame["split"] = "train"
    frame.loc[frame.index[remainder[val]], "split"] = "validation"
    frame.loc[frame.index[remainder[test]], "split"] = "test"
    return frame


def validate_manifest(path, label_count=None):
    frame = pd.read_csv(path, dtype={"patient_id": str, "file": str})
    required = {"patient_id", "file", "labels", "split"}
    if not required.issubset(frame.columns) or frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Manifest requires nonempty patient_id, file, labels, and split columns.")
    if not set(frame.split).issubset({"train", "validation", "test", "external"}):
        raise ValueError("Unsupported split name.")
    if frame.groupby("patient_id").split.nunique().max() > 1:
        raise ValueError("Patient leakage across splits detected.")
    if frame.file.duplicated().any():
        raise ValueError("Duplicate recording/image paths detected.")
    labels = np.array([json.loads(x) for x in frame.labels], dtype=np.float32)
    if labels.ndim != 2 or (label_count and labels.shape[1] != label_count):
        raise ValueError("Label dimensions do not match.")
    if not np.isin(labels, [-1, 0, 1]).all():
        raise ValueError("Labels must be 0, 1, or -1 (uncertain/masked).")
    return frame, labels


def data_path(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Dataset file is missing or escapes its authorized root.")
    return path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

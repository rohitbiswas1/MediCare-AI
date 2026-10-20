"""Evaluate a fixed artifact on a distinct, authorized external dataset; never tune thresholds here."""

import argparse
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from ml.datasets.manifest import sha256, validate_manifest
from ml.evaluation.metrics import evaluate, subgroup_metrics
from ml.train import MedicalDataset, collect, model_for


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-metadata", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    card = json.loads((args.artifact / "model.json").read_text())
    metadata = json.loads(args.dataset_metadata.read_text())
    if metadata["labels"] != card["labels"]:
        raise ValueError("External dataset label definitions/order must match the artifact.")
    if metadata["name"] == card["dataset"]["name"]:
        raise ValueError("External validation needs a distinct dataset, not another internal split.")
    if sha256(args.artifact / "weights.pt") != card["weights_sha256"]:
        raise ValueError("Artifact integrity verification failed.")
    if sha256(args.training_manifest) != card["manifest_sha256"]:
        raise ValueError("Original training manifest does not match.")
    frame, labels = validate_manifest(args.manifest, len(card["labels"]))
    original, _ = validate_manifest(args.training_manifest, len(card["labels"]))
    if set(frame.patient_id) & set(original.patient_id):
        raise ValueError("Patient overlap detected. Use stable dataset-scoped IDs and verify linkage.")
    if set(frame.split) != {"external"}:
        raise ValueError("All external rows must use split=external.")
    model = model_for(card["modality"], len(card["labels"]), card["architecture"])
    model.load_state_dict(torch.load(args.artifact / "weights.pt", weights_only=True, map_location="cpu"))
    loader = DataLoader(MedicalDataset(frame, labels, args.data_root, card["modality"]), batch_size=16)
    truth, logits = collect(model, loader, torch.device("cpu"))
    probs = torch.sigmoid(logits / card["temperature"]).numpy()
    report = {
        "dataset": metadata,
        "manifest_sha256": sha256(args.manifest),
        "weights_sha256": card["weights_sha256"],
        "metrics": evaluate(truth.numpy(), probs, card["thresholds"]),
        "subgroups": {
            key: subgroup_metrics(frame, truth.numpy(), probs, card["thresholds"], key)
            for key in ["sex", "age_group"]
        },
        "clinical_approval": False,
        "warning": "An external evaluation does not itself establish clinical or regulatory approval.",
    }
    args.output.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

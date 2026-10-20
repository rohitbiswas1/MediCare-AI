"""Convert a licensed CheXpert CSV into a patient-isolated research manifest."""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from .manifest import assign_splits

LABELS = ["Cardiomegaly", "Edema", "Consolidation", "Atelectasis", "Pleural Effusion"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--license-acknowledged", action="store_true", required=True)
    args = parser.parse_args()
    source = pd.read_csv(args.csv)
    source = source[source["Frontal/Lateral"] == "Frontal"]
    rows = []
    for _, row in source.iterrows():
        match = re.search(r"patient(\d+)", row["Path"])
        if not match:
            raise ValueError("Cannot establish patient identity for splitting.")
        # Missing and uncertain labels are masked, not converted to negatives.
        labels = [int(row[label]) if pd.notna(row[label]) else -1 for label in LABELS]
        rows.append(
            {
                "patient_id": match[1],
                "file": row["Path"],
                "labels": json.dumps(labels),
                "view": row.get("AP/PA", ""),
                "sex": row.get("Sex", ""),
                "age": row.get("Age", ""),
            }
        )
    frame = assign_splits(pd.DataFrame(rows), seed=42)
    args.output.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output / "manifest.csv", index=False)
    (args.output / "dataset.json").write_text(
        json.dumps(
            {
                "name": "CheXpert",
                "version": args.dataset_version,
                "labels": LABELS,
                "clinical_use": False,
                "uncertain_labels": "masked",
                "source": "https://stanfordmlgroup.github.io/competitions/chexpert/",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

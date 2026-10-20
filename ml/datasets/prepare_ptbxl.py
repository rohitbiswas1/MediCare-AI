"""Prepare a locally obtained, licensed PTB-XL release. No automatic dataset download."""

import argparse
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

from .manifest import data_path

LABELS = ["NORM", "MI", "STTC", "CD", "HYP"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--license-acknowledged", action="store_true", required=True)
    args = parser.parse_args()
    metadata = pd.read_csv(args.source / "ptbxl_database.csv")
    statements = pd.read_csv(args.source / "scp_statements.csv", index_col=0)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for row in metadata.itertuples():
        header = data_path(args.source, row.filename_lr + ".hea")
        waveform, meta = wfdb.rdsamp(str(header.with_suffix("")))
        codes = ast.literal_eval(row.scp_codes)
        classes = {
            statements.loc[code, "diagnostic_class"]
            for code in codes
            if code in statements.index and statements.loc[code, "diagnostic"] == 1
        }
        labels = [int(name in classes) for name in LABELS]
        target = f"{row.ecg_id}.npz"
        np.savez_compressed(
            args.output / target,
            waveform=waveform.T.astype(np.float32),
            sampling_rate=meta["fs"],
            leads=np.asarray(meta["sig_name"]),
        )
        records.append(
            {
                "patient_id": str(row.patient_id),
                "file": target,
                "labels": json.dumps(labels),
                "split": "train" if row.strat_fold <= 8 else "validation" if row.strat_fold == 9 else "test",
                "sex": str(row.sex),
                "age": row.age,
            }
        )
    pd.DataFrame(records).to_csv(args.output / "manifest.csv", index=False)
    (args.output / "dataset.json").write_text(
        json.dumps(
            {
                "name": "PTB-XL",
                "version": args.dataset_version,
                "labels": LABELS,
                "sampling_rate": 100,
                "samples": 1000,
                "split": "official patient-level folds",
                "source": "https://physionet.org/content/ptb-xl/",
                "clinical_use": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

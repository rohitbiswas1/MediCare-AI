import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def evaluate(y_true, probabilities, thresholds=None, bins=10):
    y_true, probabilities = np.asarray(y_true), np.asarray(probabilities)
    if y_true.shape != probabilities.shape or y_true.ndim != 2 or not len(y_true):
        raise ValueError("Expected matching nonempty [samples, labels] arrays.")
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("Probabilities must be finite values between zero and one.")
    thresholds = np.full(y_true.shape[1], 0.5) if thresholds is None else np.asarray(thresholds)
    result = []
    for column in range(y_true.shape[1]):
        mask = y_true[:, column] >= 0
        truth, score = y_true[mask, column], probabilities[mask, column]
        if len(truth) == 0:
            result.append(
                {"n": 0, "auroc": None, "sensitivity": None, "specificity": None, "ece": None, "brier": None}
            )
            continue
        pred = score >= thresholds[column]
        positives, negatives = (truth == 1).sum(), (truth == 0).sum()
        ece = 0.0
        for lower, upper in zip(np.linspace(0, 1, bins + 1)[:-1], np.linspace(0, 1, bins + 1)[1:]):
            selected = (score >= lower) & ((score < upper) if upper < 1 else (score <= upper))
            if selected.any():
                ece += selected.mean() * abs(score[selected].mean() - truth[selected].mean())
        result.append(
            {
                "n": len(truth),
                "auroc": float(roc_auc_score(truth, score)) if positives and negatives else None,
                "sensitivity": float(pred[truth == 1].mean()) if positives else None,
                "specificity": float((~pred[truth == 0]).mean()) if negatives else None,
                "ece": float(ece),
                "brier": float(np.mean((score - truth) ** 2)),
            }
        )
    return result


def validation_thresholds(y_true, probabilities):
    values = []
    for i in range(y_true.shape[1]):
        mask = y_true[:, i] >= 0
        truth, score = y_true[mask, i], probabilities[mask, i]
        if len(np.unique(truth)) < 2:
            raise ValueError("Validation needs both classes for every label; do not invent a threshold.")
        fpr, tpr, thresholds = roc_curve(truth, score)
        finite = np.isfinite(thresholds)
        values.append(float(thresholds[finite][np.argmax((tpr - fpr)[finite])]))
    return values


def subgroup_metrics(frame, truth, probabilities, thresholds, column):
    if column not in frame:
        return {}
    return {
        str(group): evaluate(truth[indices], probabilities[indices], thresholds)
        for group, indices in frame.reset_index(drop=True).groupby(column).indices.items()
    }

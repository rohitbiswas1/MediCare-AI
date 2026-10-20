"""Research architectures; untrained networks must never serve patient predictions."""

from torch import nn


class ECGCNN(nn.Module):
    def __init__(self, labels=5, leads=12):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(leads, 32, 15, stride=2, padding=7),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, 64, 9, stride=2, padding=4),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Conv1d(64, 128, 7, stride=2, padding=3),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(128, labels),
        )

    def forward(self, waveform):
        return self.layers(waveform)


class ECGTransformer(nn.Module):
    """Hugging Face PatchTST backbone with a multi-label research head."""

    def __init__(self, labels=5, leads=12, samples=1000):
        super().__init__()
        from transformers import PatchTSTConfig, PatchTSTModel

        config = PatchTSTConfig(
            num_input_channels=leads,
            context_length=samples,
            patch_length=50,
            patch_stride=50,
            d_model=64,
            num_attention_heads=4,
            num_hidden_layers=2,
            do_mask_input=False,
        )
        self.backbone = PatchTSTModel(config)
        self.head = nn.Linear(64, labels)

    def forward(self, waveform):
        hidden = self.backbone(past_values=waveform.transpose(1, 2)).last_hidden_state
        return self.head(hidden.mean(dim=(1, 2)))


def signal_quality(signal, sampling_rate, leads):
    import numpy as np

    expected = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
    reasons = []
    if signal.ndim != 2 or signal.shape[0] != 12:
        reasons.append("Expected 12 leads in channel-first format.")
    if sampling_rate != 100:
        reasons.append("This research adapter requires 100 Hz data; no automatic resampling is assumed.")
    if list(leads) != expected:
        reasons.append("Lead names/order do not match the supported format.")
    if not np.isfinite(signal).all():
        reasons.append("Signal contains non-finite values.")
    if signal.ndim == 2 and signal.shape[1] != 1000:
        reasons.append("Expected a 10-second, 100 Hz recording.")
    if signal.ndim == 2 and np.any(np.std(signal, axis=1) < 1e-6):
        reasons.append("At least one lead appears flat.")
    return {
        "supported": not reasons,
        "reasons": reasons,
        "sampling_rate": int(sampling_rate),
        "leads": list(leads),
        "duration_seconds": signal.shape[-1] / sampling_rate if sampling_rate > 0 else None,
        "limitation": "Basic acquisition checks do not establish clinical signal quality.",
    }

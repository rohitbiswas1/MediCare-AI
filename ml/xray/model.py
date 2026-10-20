from monai.networks.nets import DenseNet121


def create_model(labels=5):
    # No pretrained weights are silently downloaded or presented as clinically validated.
    return DenseNet121(spatial_dims=2, in_channels=1, out_channels=labels)


def image_quality(image, view=None):
    import numpy as np

    pixels = np.asarray(image)
    reasons = []
    if min(image.size) < 224:
        reasons.append("Image resolution is below the supported research input size.")
    if pixels.std() < 5:
        reasons.append("Very low contrast image.")
    if view not in {"PA", "AP"}:
        reasons.append("View must be verified from acquisition metadata. It is not inferred from pixels.")
    return {
        "supported": not reasons,
        "reasons": reasons,
        "view": view,
        "limitation": "Image checks do not establish diagnostic image quality.",
    }

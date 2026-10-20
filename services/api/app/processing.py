"""Evidence extraction only. No diagnosis or medication advice is generated."""

import io
import re
import httpx
import pymupdf as fitz
import cv2
import numpy as np
import pytesseract
from PIL import Image
from .config import settings
from .schemas import AnalysisOut, Measurement

DISCLAIMER = "This AI explanation is informational and does not replace evaluation by a qualified medical professional."
EMERGENCY = "If you have severe chest pain, severe trouble breathing, fainting, or signs of a stroke, seek emergency care now. In India, call 112."
EXPLANATIONS = {
    "above_reported_range": "This value is above the reference range printed on this report. A clinician can explain what it means in your context.",
    "below_reported_range": "This value is below the reference range printed on this report. A clinician can explain what it means in your context.",
    "within_reported_range": "This value is within the reference range printed on this report. This alone does not establish that you are healthy.",
    "no_reference": "A value was extracted, but no supported reference range was found on the same line. Confirm it against your original report.",
}
# Units and reference intervals must be literally present. Never infer a missing unit.
PATTERNS = [
    (
        "Heart rate",
        r"(?:heart\s*rate|ventricular\s*rate|HR)\s*[:=]?\s*(\d{2,3}(?:\.\d+)?)\s*(bpm|beats/min)",
        "bpm",
    ),
    ("Haemoglobin", r"(?:ha?emoglobin|HGB|Hb)\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)\s*(g/d[lL])", "g/dL"),
    ("Glucose", r"(?:glucose|blood\s*sugar)\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)\s*(mg/d[lL]|mmol/[lL])", None),
    (
        "Total cholesterol",
        r"(?:total\s*cholesterol)\s*[:=]?\s*(\d{1,3}(?:\.\d+)?)\s*(mg/d[lL]|mmol/[lL])",
        None,
    ),
    ("HbA1c", r"(?:HbA1c)\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)\s*(%)", "%"),
    ("Creatinine", r"(?:creatinine)\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)\s*(mg/d[lL]|µmol/[lL])", None),
]


def extract_measurements(text):
    measurements = []
    for line in text.splitlines():
        for name, pattern, normalized_unit in PATTERNS:
            match = re.search(pattern, line, re.I)
            if not match:
                continue
            value = float(match[1])
            tail = line[match.end() :]
            reference = re.search(
                r"(?:reference|ref|range)\s*[:(]?\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", tail, re.I
            )
            low = float(reference[1]) if reference else None
            high = float(reference[2]) if reference else None
            comparison = "no_reference"
            if low is not None and high is not None and low < high:
                comparison = (
                    "below_reported_range"
                    if value < low
                    else "above_reported_range"
                    if value > high
                    else "within_reported_range"
                )
            else:
                low = high = None
            explanation = EXPLANATIONS[comparison]
            if name == "Heart rate" and comparison == "no_reference" and value > 100:
                explanation += " If this is an adult resting reading, it is faster than the typical adult resting range. Activity, stress, and illness can affect it; discuss persistent readings or symptoms with a clinician."
            measurements.append(
                Measurement(
                    name=name,
                    value=value,
                    unit=normalized_unit or match[2],
                    source_quote=line.strip()[:500],
                    reference_low=low,
                    reference_high=high,
                    comparison=comparison,
                    explanation=explanation,
                ).model_dump()
            )
    return measurements[:100]


def classify(text, requested):
    if requested in {"ecg", "xray", "prescription", "heart_rate"}:
        return requested
    if re.search(r"\b(ECG|electrocardiogram|ventricular rate)\b", text, re.I):
        return "ecg"
    if re.search(r"\b(ha?emoglobin|HbA1c|glucose|creatinine)\b", text, re.I):
        return "blood_test"
    return "document"


def image_text(image):
    image = image.convert("RGB")
    grey = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    quality = {
        "width": image.width,
        "height": image.height,
        "blur_score": round(float(cv2.Laplacian(grey, cv2.CV_64F).var()), 2),
    }
    # This threshold flags acquisition quality only; it is not medical model confidence.
    quality["needs_review"] = min(image.size) < 500 or quality["blur_score"] < 25
    return pytesseract.image_to_string(image, lang="eng", timeout=30), quality


def extract(data, mime):
    if mime == "application/dicom":
        return (
            "",
            {
                "needs_review": True,
                "reason": "DICOM is stored securely. Pixel inference requires validated model support.",
            },
            "dicom-container-only",
        )
    if mime == "application/pdf":
        texts, flags = [], []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                text = page.get_text("text", sort=True)
                if len(text.strip()) < 20:
                    scale = min(2, 2500 / max(page.rect.width, page.rect.height, 1))
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    text, quality = image_text(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
                    flags.append(quality["needs_review"])
                texts.append(text)
        text = "\n".join(texts)[:100_000]
        return (
            text,
            {"pages": len(texts), "needs_review": any(flags) or len(text.strip()) < 20},
            "pymupdf+tesseract-5",
        )
    with Image.open(io.BytesIO(data)) as image:
        text, quality = image_text(image)
    quality["needs_review"] |= len(text.strip()) < 20
    return text[:100_000], quality, "tesseract-5"


def controlled_gemini(measurements):
    """Ask for template keys, never accept provider-generated clinical prose or new facts."""
    cfg = settings()
    if not cfg.gemini_api_key or not measurements:
        return "deterministic-evidence-templates"
    expected = [{"index": i, "template": item["comparison"]} for i, item in enumerate(measurements)]
    # Only precomputed comparison categories leave the machine, without names, IDs, files, or text.
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.gemini_model}:generateContent",
            headers={"x-goog-api-key": cfg.gemini_api_key},
            timeout=15,
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Return exactly this JSON array of approved explanation template keys: "
                                + __import__("json").dumps(expected)
                            }
                        ]
                    }
                ],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
            },
        )
        response.raise_for_status()
        import json

        actual = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        if actual == expected:
            return "gemini-validated-template-selection"
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        pass
    return "deterministic-evidence-templates"


def analyze(text, quality, requested, third_party_ai=False):
    report_type = classify(text, requested)
    measurements = extract_measurements(text)
    limitations = [
        "OCR may misread text or numbers. Compare every extracted value with the original.",
        "Reference ranges vary by laboratory, age, clinical context, and measurement method.",
        "No diagnosis, treatment decision, or medication change is provided.",
    ]
    status = "needs_review" if quality.get("needs_review") or not measurements else "informational"
    summary = f"{len(measurements)} reported measurement(s) extracted. Review the source text before using this explanation."
    model = {"name": "evidence-extractor", "version": "1.0.0", "validation": "informational-only"}
    if report_type in {"ecg", "xray"}:
        limitations.append(
            "No clinically validated imaging or waveform model is deployed. Extracted text is not a rhythm or radiology interpretation."
        )
        if report_type == "ecg":
            limitations.append("A photograph of ECG paper is not raw waveform data.")
        model = {"name": f"{report_type}-classifier", "version": None, "validation": "unavailable"}
        status = "unavailable"
        summary = "Specialized medical inference is unavailable. Any values below were extracted from report text only."
    elif not measurements:
        summary = "No supported measurements could be reliably extracted. Review the original with a clinician or upload a clearer report."
    return AnalysisOut(
        report_type=report_type,
        status=status,
        measurements=measurements,
        summary=summary,
        limitations=limitations,
        quality=quality,
        model=model,
        emergency_guidance=EMERGENCY,
        disclaimer=DISCLAIMER,
        explanation_engine=controlled_gemini(measurements)
        if third_party_ai
        else "deterministic-evidence-templates",
    ).model_dump()


def prescription_candidates(text, medicines):
    """Match only known catalog names. Every returned field is a literal OCR substring."""
    candidates = []
    names = sorted(
        {name for med in medicines for name in [med.generic_name, med.brand_name] if name},
        key=len,
        reverse=True,
    )
    for line in text.splitlines():
        for name in names:
            match = re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", line, re.I)
            if not match:
                continue
            remainder = line[match.end() :]
            strength = re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|IU)\b", remainder, re.I)
            form = re.search(r"\b(?:tablet|capsule|syrup|cream|drops|injection|tab|cap)\b", remainder, re.I)
            candidates.append(
                {
                    "name": match[0],
                    "strength": strength[0] if strength else "",
                    "dosage_form": form[0] if form else "",
                    "instructions": remainder[form.end() :].strip(" :-") if form else "",
                    "source_quote": line.strip(),
                    "verification": "unconfirmed",
                }
            )
            break
    return candidates[:30]

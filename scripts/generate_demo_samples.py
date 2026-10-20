"""Create clearly labeled synthetic documents for the public demo. No patient data."""
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

destination = Path(sys.argv[1])
destination.mkdir(parents=True, exist_ok=True)
with pymupdf.open() as pdf:
    page = pdf.new_page()
    for y, line in [
        (55, "SYNTHETIC DEMO REPORT - NOT A PATIENT"),
        (90, "For testing document extraction only."),
        (135, "Heart rate: 88 bpm Reference: 60-100"),
        (165, "Haemoglobin: 13.5 g/dL Reference: 12-16"),
        (220, "These example values are not medical advice."),
    ]:
        page.insert_text((40, y), line, fontsize=13)
    pdf.save(destination / "sample-report.pdf")
image = Image.new("RGB", (1500, 650), "white")
draw = ImageDraw.Draw(image)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
for y, line in [
    (60, "SYNTHETIC PRESCRIPTION - NOT A PATIENT"),
    (150, "OCR workflow demonstration only."),
    (240, "Confirm unclear text with a pharmacist."),
    (330, "No medicine, dose, or treatment is prescribed."),
]:
    draw.text((40, y), line, font=font, fill="black")
image.save(destination / "sample-prescription.png")

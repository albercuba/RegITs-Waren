from pathlib import Path

from PIL import Image, ImageOps
from pyzbar.pyzbar import decode
import pytesseract

from app.services.parser import parse_label_data


def scan_image(path: Path) -> dict:
    raw_text = ""
    barcodes: list[str] = []
    ocr_error = ""

    try:
        image = ImageOps.exif_transpose(Image.open(path))
        grayscale = ImageOps.grayscale(image)
        raw_text = pytesseract.image_to_string(grayscale)
        barcodes = [item.data.decode("utf-8", errors="ignore") for item in decode(image)]
    except Exception as exc:  # OCR tooling can fail if binaries are missing.
        ocr_error = str(exc)

    fields = parse_label_data(raw_text, barcodes)
    detected = any(fields.values())
    return {
        "status": "fields_detected" if detected else "manual_input_required",
        "fields": fields,
        "raw_text": raw_text,
        "barcodes": barcodes,
        "ocr_error": ocr_error,
    }

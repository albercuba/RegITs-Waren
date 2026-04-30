from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from pyzbar.pyzbar import decode
import pytesseract

from app.services.parser import parse_label_data


def _merge_text(parts: list[str]) -> str:
    lines = []
    seen = set()
    for part in parts:
        for line in part.splitlines():
            clean = line.strip()
            if clean and clean not in seen:
                lines.append(clean)
                seen.add(clean)
    return "\n".join(lines)


def _ocr_text(image: Image.Image) -> str:
    grayscale = ImageOps.grayscale(image)
    enhanced = ImageEnhance.Contrast(ImageOps.autocontrast(grayscale)).enhance(1.8)
    fast_text = pytesseract.image_to_string(enhanced, config="--psm 6")
    if len(fast_text.strip()) >= 20:
        return fast_text

    upscaled = enhanced.resize((enhanced.width * 2, enhanced.height * 2))
    fallback_text = pytesseract.image_to_string(upscaled, config="--psm 11")
    return _merge_text([fast_text, fallback_text])


def scan_image(path: Path) -> dict:
    raw_text = ""
    barcodes: list[str] = []
    ocr_error = ""

    try:
        image = ImageOps.exif_transpose(Image.open(path))
        raw_text = _ocr_text(image)
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

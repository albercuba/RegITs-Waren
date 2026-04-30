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


def _enhanced_image(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    return ImageEnhance.Contrast(ImageOps.autocontrast(grayscale)).enhance(1.8)


def _ocr_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(image)
    return pytesseract.image_to_string(enhanced, config="--psm 6")


def _ocr_fallback_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(image)
    upscaled = enhanced.resize((enhanced.width * 2, enhanced.height * 2))
    return pytesseract.image_to_string(upscaled, config="--psm 11")


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
    if not fields.get("serial_number") and raw_text and not ocr_error:
        try:
            fallback_text = _ocr_fallback_text(image)
            raw_text = _merge_text([raw_text, fallback_text])
            fields = parse_label_data(raw_text, barcodes)
        except Exception as exc:  # Keep the fast OCR result if fallback fails.
            ocr_error = str(exc)

    detected = any(fields.values())
    return {
        "status": "fields_detected" if detected else "manual_input_required",
        "fields": fields,
        "raw_text": raw_text,
        "barcodes": barcodes,
        "ocr_error": ocr_error,
    }

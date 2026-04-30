from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyzbar.pyzbar import decode
import pytesseract

from app.services.parser import parse_label_data_with_debug


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
    contrasted = ImageEnhance.Contrast(ImageOps.autocontrast(grayscale)).enhance(1.8)
    return contrasted.filter(ImageFilter.SHARPEN)


def _threshold_image(image: Image.Image) -> Image.Image:
    enhanced = _enhanced_image(image)
    return enhanced.point(lambda pixel: 255 if pixel > 165 else 0)


def _ocr_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(image)
    return pytesseract.image_to_string(enhanced, config="--oem 3 --psm 6")


def _ocr_fallback_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(image)
    upscaled = enhanced.resize((enhanced.width * 2, enhanced.height * 2))
    thresholded = _threshold_image(image).resize((image.width * 2, image.height * 2))
    return _merge_text(
        [
            pytesseract.image_to_string(upscaled, config="--oem 3 --psm 11"),
            pytesseract.image_to_string(thresholded, config="--oem 3 --psm 6"),
        ]
    )


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

    fields, serial_debug = parse_label_data_with_debug(raw_text, barcodes)
    if serial_debug.get("needs_confirmation") and raw_text and not ocr_error:
        try:
            fallback_text = _ocr_fallback_text(image)
            raw_text = _merge_text([raw_text, fallback_text])
            fields, serial_debug = parse_label_data_with_debug(raw_text, barcodes)
        except Exception as exc:  # Keep the fast OCR result if fallback fails.
            ocr_error = str(exc)

    detected = any(fields.values())
    return {
        "status": "fields_detected" if detected else "manual_input_required",
        "fields": fields,
        "raw_text": raw_text,
        "raw_ocr_text": raw_text,
        "barcodes": barcodes,
        "serial_debug": serial_debug,
        "best_guess_serial": serial_debug.get("best_guess_serial", ""),
        "confidence_score": serial_debug.get("confidence_score", 0),
        "confidence": serial_debug.get("confidence", 0),
        "serial_candidates": serial_debug.get("candidates", []),
        "candidates": serial_debug.get("candidates", []),
        "warnings": serial_debug.get("warnings", []),
        "ocr_error": ocr_error,
    }

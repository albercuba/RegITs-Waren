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


def _decode_barcodes(images: list[Image.Image]) -> list[str]:
    values = []
    seen = set()
    for image in images:
        try:
            decoded = decode(image)
        except Exception:
            decoded = []
        for item in decoded:
            value = item.data.decode("utf-8", errors="ignore").strip()
            if value and value not in seen:
                values.append(value)
                seen.add(value)
    return values


def _enhanced_image(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageEnhance.Contrast(ImageOps.autocontrast(grayscale)).enhance(1.8)
    return contrasted.filter(ImageFilter.SHARPEN)


def _threshold_image(image: Image.Image) -> Image.Image:
    enhanced = _enhanced_image(image)
    return enhanced.point(lambda pixel: 255 if pixel > 165 else 0)


def _upscale(image: Image.Image, factor: int = 2) -> Image.Image:
    return image.resize((image.width * factor, image.height * factor), Image.Resampling.LANCZOS)


def _rotations(image: Image.Image) -> list[Image.Image]:
    return [image, image.rotate(90, expand=True), image.rotate(180, expand=True), image.rotate(270, expand=True)]


def _ocr_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(image)
    return pytesseract.image_to_string(enhanced, config="--oem 3 --psm 6 -c preserve_interword_spaces=1")


def _ocr_fallback_text(image: Image.Image) -> str:
    images = [
        _upscale(_enhanced_image(image)),
        _upscale(_threshold_image(image)),
        _upscale(ImageOps.invert(_threshold_image(image))),
    ]
    rotated_images = [_upscale(_enhanced_image(rotated)) for rotated in _rotations(image)[1:]]
    configs = [
        "--oem 3 --psm 6 -c preserve_interword_spaces=1",
        "--oem 3 --psm 11",
        "--oem 3 --psm 12",
    ]
    texts = []
    for candidate in [*images, *rotated_images]:
        for config in configs:
            texts.append(pytesseract.image_to_string(candidate, config=config))
    return _merge_text(
        texts
    )


def scan_image(path: Path) -> dict:
    raw_text = ""
    barcodes: list[str] = []
    ocr_error = ""

    try:
        image = ImageOps.exif_transpose(Image.open(path))
        raw_text = _ocr_text(image)
        barcodes = _decode_barcodes([image, _enhanced_image(image), _threshold_image(image), *_rotations(image)[1:]])
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

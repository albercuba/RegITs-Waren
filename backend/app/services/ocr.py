from functools import lru_cache
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.config import get_settings
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
    try:
        from pyzbar.pyzbar import decode
    except Exception:
        return values

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


def _fit_for_ocr(image: Image.Image) -> Image.Image:
    max_dimension = get_settings().ocr_max_dimension
    if max(image.size) <= max_dimension:
        return image
    fitted = image.copy()
    fitted.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return fitted


def _rotations(image: Image.Image) -> list[Image.Image]:
    return [image, image.rotate(90, expand=True), image.rotate(180, expand=True), image.rotate(270, expand=True)]


@lru_cache(maxsize=1)
def get_ocr_engine() -> Any:
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        raise RuntimeError("PaddleOCR is not installed or could not be imported") from exc

    settings = get_settings()
    # Keep the engine cached; loading PaddleOCR models for every scan would be very slow.
    return PaddleOCR(
        lang=settings.paddleocr_lang,
        use_angle_cls=settings.paddleocr_use_angle_cls,
        show_log=False,
        use_gpu=False,
        drop_score=settings.paddleocr_min_confidence,
    )


def _paddleocr_result_pages(result: Any) -> list:
    if not result:
        return []
    if isinstance(result, list) and result and _looks_like_ocr_line(result[0]):
        return [result]
    return result if isinstance(result, list) else []


def _looks_like_ocr_line(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and isinstance(value[1], (list, tuple))
        and len(value[1]) >= 2
        and isinstance(value[1][0], str)
    )


def _metadata_line(box: Any, text: str, confidence: Any) -> dict:
    return {
        "text": text,
        "confidence": float(confidence) if confidence is not None else None,
        "box": box,
    }


def _ocr_text_from_image(image: Image.Image) -> tuple[str, list[dict]]:
    fitted = _fit_for_ocr(image).convert("RGB")
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            temp_path = temp.name
        fitted.save(temp_path)
        result = get_ocr_engine().ocr(temp_path, cls=get_settings().paddleocr_use_angle_cls)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
    lines: list[str] = []
    metadata: list[dict] = []

    for page in _paddleocr_result_pages(result):
        for item in page or []:
            try:
                box, text_info = item
                text, confidence = text_info
            except Exception:
                continue

            cleaned = str(text).strip() if text is not None else ""
            if not cleaned:
                continue
            if confidence is not None and float(confidence) < get_settings().paddleocr_min_confidence:
                continue

            lines.append(cleaned)
            metadata.append(_metadata_line(box, cleaned, confidence))

    return _merge_text(["\n".join(lines)]), metadata


def scan_image(path: Path) -> dict:
    raw_text = ""
    barcodes: list[str] = []
    ocr_lines: list[dict] = []
    ocr_error = ""

    try:
        image = ImageOps.exif_transpose(Image.open(path))
        raw_text, ocr_lines = _ocr_text_from_image(image)
        barcodes = _decode_barcodes([image, _enhanced_image(image), _threshold_image(image), *_rotations(image)[1:]])
    except Exception as exc:  # OCR tooling can fail if binaries or models are missing.
        ocr_error = str(exc)

    fields, serial_debug = parse_label_data_with_debug(raw_text, barcodes)

    detected = any(fields.values())
    return {
        "status": "fields_detected" if detected else "manual_input_required",
        "fields": fields,
        "raw_text": raw_text,
        "raw_ocr_text": raw_text,
        "ocr_lines": ocr_lines,
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

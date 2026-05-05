from functools import lru_cache
from pathlib import Path
from time import perf_counter

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyzbar.pyzbar import decode

from app.config import get_settings
from app.services.barcode_candidates import (
    best_barcode_candidate,
    classify_barcode_candidates,
    needs_barcode_confirmation,
    should_merge_barcode_candidate,
    should_skip_tesseract_from_barcodes,
)
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


def _decode_barcodes_fast(image: Image.Image) -> list[str]:
    barcodes = _decode_barcodes([image])
    if barcodes:
        return barcodes
    return _decode_barcodes([_enhanced_image(image)])


def _decode_barcodes_deep(image: Image.Image) -> list[str]:
    return _decode_barcodes([image, _enhanced_image(image), _threshold_image(image), *_rotations(image)[1:]])


def _enhanced_image(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageEnhance.Contrast(ImageOps.autocontrast(grayscale)).enhance(1.8)
    return contrasted.filter(ImageFilter.SHARPEN)


def _threshold_image(image: Image.Image) -> Image.Image:
    enhanced = _enhanced_image(image)
    return enhanced.point(lambda pixel: 255 if pixel > 165 else 0)


def _upscale(image: Image.Image, factor: int = 2) -> Image.Image:
    return image.resize((image.width * factor, image.height * factor), Image.Resampling.LANCZOS)


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
def _ocr_language_config() -> str:
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception:
        return ""
    preferred = [language for language in ("deu", "eng") if language in languages]
    return f"-l {'+'.join(preferred)} " if preferred else ""


def _ocr_text(image: Image.Image) -> str:
    enhanced = _enhanced_image(_fit_for_ocr(image))
    return pytesseract.image_to_string(
        enhanced,
        config=f"{_ocr_language_config()}--oem 3 --psm 6 -c preserve_interword_spaces=1",
        timeout=get_settings().ocr_timeout_seconds,
    )


def _ocr_fallback_text(image: Image.Image) -> str:
    image = _fit_for_ocr(image)
    images = [
        _upscale(_enhanced_image(image)),
        _upscale(_threshold_image(image)),
    ]
    configs = [
        f"{_ocr_language_config()}--oem 3 --psm 6 -c preserve_interword_spaces=1",
        f"{_ocr_language_config()}--oem 3 --psm 11",
    ]
    texts = []
    for candidate in images:
        for config in configs:
            try:
                texts.append(
                    pytesseract.image_to_string(
                        candidate,
                        config=config,
                        timeout=get_settings().ocr_fallback_timeout_seconds,
                    )
                )
            except RuntimeError:
                continue
    return _merge_text(texts)


def _empty_fields(serial_number: str = "") -> dict[str, str]:
    return {
        "serial_number": serial_number,
        "vendor": "",
        "model": "",
        "asset_type": "",
        "notes": "",
    }


def _barcode_serial_debug(candidate: dict) -> dict:
    return {
        "best_guess_serial": candidate["normalized"],
        "confidence_score": candidate["score"],
        "confidence": min(max(candidate["score"] / 100, 0), 1),
        "confidence_threshold": get_settings().barcode_high_confidence_score,
        "needs_confirmation": False,
        "source": "barcode_candidate_ranker",
        "candidates": [
            {
                "value": candidate["normalized"],
                "score": candidate["score"],
                "source": "barcode_candidate_ranker",
                "line": None,
                "reasons": candidate.get("reasons", []),
                "reason": ", ".join(candidate.get("reasons", [])),
                "rejected": False,
            }
        ],
        "normalized_text": "",
        "warnings": [],
    }


def _build_scan_result(
    fields: dict,
    raw_text: str,
    barcodes: list[str],
    serial_debug: dict,
    barcode_candidates: list[dict],
    ocr_error: str,
    timings: dict[str, float],
    ocr_skipped: bool = False,
    skip_reason: str = "",
) -> dict:
    detected = any(fields.values())
    needs_confirmation = needs_barcode_confirmation(barcode_candidates, fields, serial_debug)
    serial_debug["needs_confirmation"] = bool(serial_debug.get("needs_confirmation") or needs_confirmation)
    return {
        "status": "fields_detected" if detected else "manual_input_required",
        "fields": fields,
        "raw_text": raw_text,
        "raw_ocr_text": raw_text,
        "barcodes": barcodes,
        "barcode_candidates": barcode_candidates,
        "serial_debug": serial_debug,
        "best_guess_serial": serial_debug.get("best_guess_serial", ""),
        "confidence_score": serial_debug.get("confidence_score", 0),
        "confidence": serial_debug.get("confidence", 0),
        "serial_candidates": serial_debug.get("candidates", []),
        "candidates": serial_debug.get("candidates", []),
        "warnings": serial_debug.get("warnings", []),
        "ocr_error": ocr_error,
        "ocr_skipped": ocr_skipped,
        "skip_reason": skip_reason,
        "needs_confirmation": needs_confirmation,
        "timings": timings,
    }


def scan_image(path: Path, mode: str = "fast") -> dict:
    scan_started = perf_counter()
    raw_text = ""
    barcodes: list[str] = []
    barcode_candidates: list[dict] = []
    ocr_error = ""
    timings = {"barcode_decode": 0.0, "ocr_main": 0.0, "parse": 0.0, "total": 0.0}
    mode = mode if mode in {"fast", "deep"} else get_settings().ocr_default_mode

    try:
        image = ImageOps.exif_transpose(Image.open(path))
        barcode_started = perf_counter()
        barcodes = _decode_barcodes_fast(image) if mode == "fast" else _decode_barcodes_deep(image)
        timings["barcode_decode"] = perf_counter() - barcode_started
        barcode_candidates = classify_barcode_candidates(barcodes)
        if should_skip_tesseract_from_barcodes(barcode_candidates):
            best = best_barcode_candidate(barcode_candidates)
            fields = _empty_fields(best["normalized"])
            serial_debug = _barcode_serial_debug(best)
            timings["total"] = perf_counter() - scan_started
            return _build_scan_result(
                fields,
                raw_text,
                barcodes,
                serial_debug,
                barcode_candidates,
                ocr_error,
                timings,
                ocr_skipped=True,
                skip_reason="confident_barcode",
            )

        ocr_started = perf_counter()
        raw_text = _ocr_text(image)
        timings["ocr_main"] = perf_counter() - ocr_started
        if mode == "deep":
            barcode_started = perf_counter()
            barcodes = _decode_barcodes_deep(image)
            timings["barcode_decode"] += perf_counter() - barcode_started
    except Exception as exc:  # OCR tooling can fail if binaries are missing.
        ocr_error = str(exc)

    parse_started = perf_counter()
    fields, serial_debug = parse_label_data_with_debug(raw_text, barcodes)
    barcode_candidates = classify_barcode_candidates(barcodes, raw_text, fields.get("vendor", ""))
    if should_merge_barcode_candidate(fields, serial_debug, barcode_candidates):
        best = best_barcode_candidate(barcode_candidates)
        fields["serial_number"] = best["normalized"]
        serial_debug["best_guess_serial"] = best["normalized"]
        serial_debug["confidence_score"] = max(serial_debug.get("confidence_score", 0), best["score"])
        serial_debug["confidence"] = min(max(serial_debug["confidence_score"] / 100, 0), 1)
        serial_debug["source"] = "barcode_candidate_ranker"

    if serial_debug.get("needs_confirmation") and raw_text and not ocr_error:
        try:
            ocr_started = perf_counter()
            fallback_text = _ocr_fallback_text(image)
            timings["ocr_main"] += perf_counter() - ocr_started
            raw_text = _merge_text([raw_text, fallback_text])
            fields, serial_debug = parse_label_data_with_debug(raw_text, barcodes)
            barcode_candidates = classify_barcode_candidates(barcodes, raw_text, fields.get("vendor", ""))
            if should_merge_barcode_candidate(fields, serial_debug, barcode_candidates):
                best = best_barcode_candidate(barcode_candidates)
                fields["serial_number"] = best["normalized"]
                serial_debug["best_guess_serial"] = best["normalized"]
                serial_debug["confidence_score"] = max(serial_debug.get("confidence_score", 0), best["score"])
                serial_debug["confidence"] = min(max(serial_debug["confidence_score"] / 100, 0), 1)
                serial_debug["source"] = "barcode_candidate_ranker"
        except Exception as exc:  # Keep the fast OCR result if fallback fails.
            ocr_error = str(exc)
    timings["parse"] = perf_counter() - parse_started
    timings["total"] = perf_counter() - scan_started

    return _build_scan_result(fields, raw_text, barcodes, serial_debug, barcode_candidates, ocr_error, timings)

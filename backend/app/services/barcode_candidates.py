import re

from app.config import get_settings

HIGH_CONFIDENCE_SCORE = 50
MARGIN_OVER_SECOND = 25

SERIAL_LABELS = (
    r"S\s*/\s*N",
    r"\bSN\b",
    r"Serial(?:\s+No\.?|\s+Number)?",
    r"Seriennummer",
    r"Service\s+Tag",
    r"Asset\s+Tag",
    r"IMEI",
)
NON_SERIAL_LABELS = (
    r"P\s*/\s*N",
    r"\bPN\b",
    r"Part\s+No\.?",
    r"Model",
    r"Modell",
    r"SKU",
    r"EAN",
    r"UPC",
    r"MAC",
    r"Order",
    r"Batch",
    r"Lot",
)
MAC_PATTERN = re.compile(r"^(?:[0-9A-F]{2}[:-]){5}[0-9A-F]{2}$|^[0-9A-F]{12}$", re.IGNORECASE)
URL_PATTERN = re.compile(r"^https?://|^www\.", re.IGNORECASE)


def normalize_barcode_value(value: str) -> str:
    return value.strip().strip(" .,:;")


def _compact(value: str) -> str:
    return re.sub(r"[\s-]+", "", normalize_barcode_value(value)).upper()


def _looks_like_ean_upc(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return digits == value and len(digits) in {8, 12, 13}


def _looks_like_mac(value: str) -> bool:
    return bool(MAC_PATTERN.fullmatch(value.strip()))


def _label_window_score(raw_text: str, normalized: str) -> tuple[int, list[str]]:
    if not raw_text:
        return 0, []

    score = 0
    reasons = []
    compact_text = _compact(raw_text)
    compact_value = _compact(normalized)
    if compact_value and compact_value in compact_text:
        score += 12
        reasons.append("appears in OCR text")

    for match in re.finditer(re.escape(normalized), raw_text, re.IGNORECASE):
        window = raw_text[max(0, match.start() - 80) : match.end() + 80]
        if any(re.search(label, window, re.IGNORECASE) for label in SERIAL_LABELS):
            score += 32
            reasons.append("near serial label in OCR text")
        if any(re.search(label, window, re.IGNORECASE) for label in NON_SERIAL_LABELS):
            score -= 34
            reasons.append("near non-serial label in OCR text")

    if compact_value and compact_value in compact_text and not reasons:
        for label in SERIAL_LABELS:
            for label_match in re.finditer(label, raw_text, re.IGNORECASE):
                window = raw_text[label_match.start() : label_match.end() + 120]
                if compact_value in _compact(window):
                    score += 32
                    reasons.append("near serial label in OCR text")
                    break
        for label in NON_SERIAL_LABELS:
            for label_match in re.finditer(label, raw_text, re.IGNORECASE):
                window = raw_text[label_match.start() : label_match.end() + 120]
                if compact_value in _compact(window):
                    score -= 34
                    reasons.append("near non-serial label in OCR text")
                    break

    return score, reasons


def classify_barcode_candidates(barcodes: list[str], raw_text: str = "", vendor: str = "") -> list[dict]:
    candidates = []
    seen = set()
    for value in barcodes:
        normalized = normalize_barcode_value(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        compact = _compact(normalized)
        score = 0
        reasons = []
        kind = "unknown"

        if 6 <= len(compact) <= 24:
            score += 25
            reasons.append("serial-like length")
        else:
            score -= 20
            reasons.append("outside serial-like length")

        if re.search(r"[A-Z]", compact) and re.search(r"\d", compact):
            score += 25
            reasons.append("alphanumeric")
            kind = "serial"
        elif compact.isdigit():
            score -= 5
            reasons.append("numeric-only")

        if _looks_like_ean_upc(normalized):
            score -= 45
            kind = "ean_upc"
            reasons.append("EAN/UPC-shaped numeric code")
        elif _looks_like_mac(normalized):
            score -= 42
            kind = "mac"
            reasons.append("MAC-shaped code")
        elif URL_PATTERN.search(normalized):
            score -= 38
            kind = "url"
            reasons.append("URL-shaped code")

        if vendor.lower() == "ubiquiti" and re.fullmatch(r"[0-9A-F]{12}", compact):
            score += 20
            kind = "serial"
            reasons.append("known Ubiquiti serial format")

        label_score, label_reasons = _label_window_score(raw_text, normalized)
        score += label_score
        reasons.extend(label_reasons)

        if kind == "unknown" and score >= 20:
            kind = "serial"

        confidence = (
            "high" if score >= get_settings().barcode_high_confidence_score else "medium" if score >= 25 else "low"
        )
        candidates.append(
            {
                "value": value,
                "normalized": normalized,
                "score": score,
                "kind": kind,
                "confidence": confidence,
                "reasons": list(dict.fromkeys(reasons)),
            }
        )

    return sorted(candidates, key=lambda candidate: candidate["score"], reverse=True)


def should_skip_tesseract_from_barcodes(candidates: list[dict]) -> bool:
    if not candidates:
        return False
    best = candidates[0]
    high_score = get_settings().barcode_high_confidence_score
    margin = get_settings().barcode_margin_over_second
    if best.get("kind") != "serial" or best.get("confidence") != "high" or best.get("score", 0) < high_score:
        return False
    if len(candidates) == 1:
        return True
    return best.get("score", 0) - candidates[1].get("score", 0) >= margin


def best_barcode_candidate(candidates: list[dict]) -> dict | None:
    return candidates[0] if candidates else None


def should_merge_barcode_candidate(fields: dict, serial_debug: dict, candidates: list[dict]) -> bool:
    best = best_barcode_candidate(candidates)
    if not best or best.get("kind") != "serial":
        return False
    parsed_serial = fields.get("serial_number", "")
    if parsed_serial and _compact(parsed_serial) == _compact(best["normalized"]):
        return False
    if not parsed_serial:
        return best.get("score", 0) >= 25
    parsed_score = serial_debug.get("confidence_score", 0)
    return (
        best.get("score", 0) >= get_settings().barcode_high_confidence_score
        and best.get("score", 0) > parsed_score + 10
    )


def needs_barcode_confirmation(candidates: list[dict], fields: dict, serial_debug: dict) -> bool:
    if len(candidates) > 1:
        best = candidates[0]
        second = candidates[1]
        if best.get("kind") == "serial" and best.get("score", 0) - second.get("score", 0) < MARGIN_OVER_SECOND:
            return True
    return bool(serial_debug.get("needs_confirmation")) or not fields.get("serial_number")

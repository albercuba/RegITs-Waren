import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(__file__).resolve().parents[1] / "serial_patterns.json"
NOISE_PATTERN = re.compile(r"[^A-Z0-9:/\-\s]")


@dataclass
class SerialCandidate:
    value: str
    score: int
    source: str
    line: int | None
    reasons: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "score": self.score,
            "source": self.source,
            "line": self.line,
            "reasons": self.reasons,
        }


def _load_config() -> dict[str, Any]:
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        config = {"confidence_threshold": 70, "keywords": [], "candidate_patterns": [], "vendor_rules": {}}
    return _merge_database_patterns(config)


def _merge_database_patterns(config: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.database import get_db

        with get_db() as conn:
            rows = conn.execute(
                "SELECT name, regex, vendor, base_score FROM serial_patterns WHERE enabled = 1"
            ).fetchall()
    except Exception:
        return config

    for row in rows:
        pattern = {"name": row["name"], "regex": row["regex"], "base_score": row["base_score"]}
        vendor = row["vendor"]
        if vendor:
            config.setdefault("vendor_rules", {}).setdefault(vendor, []).append(pattern)
        else:
            config.setdefault("candidate_patterns", []).append(pattern)
    return config


def normalize_ocr_text(text: str) -> tuple[str, list[str]]:
    lines = []
    for line in text.splitlines():
        upper = line.upper()
        cleaned = NOISE_PATTERN.sub(" ", upper)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines), lines


def _clean_candidate(value: str) -> str:
    return value.upper().strip(" :/-")


def _looks_like_serial(value: str, allow_product_barcode_shape: bool = False) -> bool:
    clean = _clean_candidate(value)
    if not 5 <= len(clean) <= 24:
        return False
    if clean.isdigit() and len(clean) in {8, 12, 13, 14} and not allow_product_barcode_shape:
        return False
    if re.fullmatch(r"\d{2,4}", clean):
        return False
    return bool(re.fullmatch(r"[A-Z0-9-]+", clean))


def _looks_like_product_barcode(value: str) -> bool:
    clean = _clean_candidate(value)
    digits = re.sub(r"\D", "", clean)
    return clean.isdigit() and len(digits) in {8, 12, 13, 14}


def _keyword_nearby(text: str, start: int, keywords: list[str]) -> bool:
    window = text[max(0, start - 24):start + 8]
    compact_window = re.sub(r"\s+", " ", window)
    return any(keyword in compact_window for keyword in keywords)


def _line_for_offset(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _score_candidate(
    value: str,
    base_score: int,
    source: str,
    line: int | None,
    line_count: int,
    has_keyword: bool,
    vendor: str,
) -> tuple[int, list[str]]:
    clean = _clean_candidate(value)
    score = base_score
    reasons = [f"base:{source}+{base_score}"]

    if has_keyword:
        score += 30
        reasons.append("keyword_proximity+30")

    if 8 <= len(clean) <= 16:
        score += 16
        reasons.append("preferred_length+16")
    elif 6 <= len(clean) <= 20:
        score += 8
        reasons.append("acceptable_length+8")

    if re.search(r"[A-Z]", clean) and re.search(r"\d", clean):
        score += 18
        reasons.append("letter_number_mix+18")
    elif clean.isdigit():
        score -= 18
        reasons.append("numeric_only-18")

    if line is not None and line_count:
        position_ratio = line / line_count
        if position_ratio <= 0.65:
            score += 8
            reasons.append("upper_middle_position+8")

    if vendor == "Dell" and re.fullmatch(r"[A-Z0-9]{5,7}", clean):
        score += 15
        reasons.append("dell_service_tag_shape+15")
    if vendor == "HP" and re.fullmatch(r"[A-Z0-9]{6,20}", clean):
        score += 10
        reasons.append("hp_serial_shape+10")
    if vendor == "Lenovo" and re.fullmatch(r"[A-Z0-9]{6,20}", clean):
        score += 10
        reasons.append("lenovo_serial_shape+10")

    return max(0, min(score, 100)), reasons


def _add_candidate(
    candidates: dict[str, SerialCandidate],
    value: str,
    base_score: int,
    source: str,
    line: int | None,
    line_count: int,
    has_keyword: bool,
    vendor: str,
) -> None:
    clean = _clean_candidate(value)
    allow_product_barcode_shape = has_keyword or source in {"keyword_serial", "hp_serial", "lenovo_serial"}
    if not _looks_like_serial(clean, allow_product_barcode_shape):
        return

    score, reasons = _score_candidate(clean, base_score, source, line, line_count, has_keyword, vendor)
    existing = candidates.get(clean)
    if not existing or score > existing.score:
        candidates[clean] = SerialCandidate(clean, score, source, line, reasons)


def extract_serial(
    raw_text: str,
    barcodes: list[str] | None = None,
    vendor: str = "",
) -> dict[str, Any]:
    config = _load_config()
    normalized_text, lines = normalize_ocr_text(raw_text)
    keywords = [keyword.upper() for keyword in config.get("keywords", [])]
    line_count = max(len(lines), 1)
    vendor_key = next((name for name in config.get("vendor_rules", {}) if name.lower() == vendor.lower()), "")
    candidates: dict[str, SerialCandidate] = {}

    for barcode in barcodes or []:
        clean = _clean_candidate(re.sub(r"\s+", "", barcode))
        if not clean or _looks_like_product_barcode(clean):
            continue
        candidates[clean] = SerialCandidate(clean, 100, "barcode", None, ["barcode_primary+100"])

    patterns = list(config.get("candidate_patterns", []))
    patterns.extend(config.get("vendor_rules", {}).get(vendor_key, []))
    for pattern in patterns:
        regex = pattern.get("regex", "")
        base_score = int(pattern.get("base_score", 10))
        source = pattern.get("name", "pattern")
        if not regex:
            continue
        for match in re.finditer(regex, normalized_text, re.IGNORECASE):
            value = match.group(match.lastindex or 1)
            start = match.start(match.lastindex or 1)
            _add_candidate(
                candidates,
                value,
                base_score,
                source,
                _line_for_offset(normalized_text, start),
                line_count,
                _keyword_nearby(normalized_text, start, keywords),
                vendor_key or vendor,
            )

    sorted_candidates = sorted(candidates.values(), key=lambda item: item.score, reverse=True)
    best = sorted_candidates[0] if sorted_candidates else None
    threshold = int(config.get("confidence_threshold", 70))
    confidence = best.score if best else 0

    return {
        "best_guess_serial": best.value if best and confidence >= threshold else "",
        "confidence_score": confidence,
        "confidence_threshold": threshold,
        "needs_confirmation": confidence < threshold,
        "candidates": [candidate.as_dict() for candidate in sorted_candidates],
        "normalized_text": normalized_text,
    }

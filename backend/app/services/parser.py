import re


VENDORS = ("Dell", "HP", "HPE", "Lenovo", "Apple", "Microsoft", "Cisco", "Ubiquiti", "Samsung", "iiyama")


SERIAL_PATTERNS = (
    r"(?:S/N|SN|Serial(?: Number)?|Service Tag)\s*[:#-]?\s*([A-Z0-9-]{5,})",
)
MODEL_PATTERNS = (
    r"(?:Model|Product)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 ._/-]{2,40})",
    r"\b(ProLite\s+[A-Z0-9-]{4,})\b",
    r"(?:Part Code|Part No\.?|P/N)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,40})",
)

PART_CODE_PATTERNS = (
    r"(?:Part Code|Part No\.?|P/N)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,40})",
)


def _first_match(patterns: tuple[str, ...], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")
    return ""


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(value)}\b", text, re.IGNORECASE) for value in values)


def _detect_asset_type(text: str) -> str:
    if _contains_any(text, ("monitor", "display", "lcd monitor", "full hd", "ips", "hdmi", "displayport")):
        return "Monitor"
    if re.search(r"\biiyama\b", text, re.IGNORECASE) and re.search(r"\bX\d{4}[A-Z-]*\b", text, re.IGNORECASE):
        return "Monitor"
    return ""


def _build_notes(text: str) -> str:
    notes = []
    part_code = _first_match(PART_CODE_PATTERNS, text)
    size = _first_match((r"\b(\d{2}(?:[.,]\d)?)\s*(?:\"|inch|in|\b(?=IPS|Full\s*HD))",), text)

    if part_code:
        notes.append(f"Part Code: {part_code}")
    if size:
        notes.append(f"{size.replace(' ', '')} inch")
    if re.search(r"\bblack\b", text, re.IGNORECASE):
        notes.append("BLACK")
    if re.search(r"\bIPS\b", text, re.IGNORECASE):
        notes.append("IPS")
    if re.search(r"\bFull\s*HD\b", text, re.IGNORECASE):
        notes.append("Full HD")
    if re.search(r"\bHDMI\b", text, re.IGNORECASE):
        notes.append("HDMI")
    if re.search(r"\bPower cables?\b", text, re.IGNORECASE):
        notes.append("Power cables")

    return ", ".join(dict.fromkeys(notes))


def parse_label_data(text: str, barcodes: list[str] | None = None) -> dict[str, str]:
    clean_text = " ".join(text.split())
    barcodes = barcodes or []
    vendor = next((vendor for vendor in VENDORS if re.search(rf"\b{re.escape(vendor)}\b", clean_text, re.I)), "")

    serial = _first_match(SERIAL_PATTERNS, clean_text)
    if not serial and barcodes:
        serial = barcodes[0]

    return {
        "serial_number": serial,
        "vendor": vendor,
        "model": _first_match(MODEL_PATTERNS, clean_text),
        "asset_type": _detect_asset_type(clean_text),
        "notes": _build_notes(clean_text),
    }

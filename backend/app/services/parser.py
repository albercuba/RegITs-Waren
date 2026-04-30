import re


VENDORS = ("Dell", "HP", "HPE", "Lenovo", "Apple", "Microsoft", "Cisco", "Ubiquiti", "Samsung", "iiyama", "Logitech")

PRODUCT_BARCODES = {
    "4948570127832": {
        "vendor": "iiyama",
        "model": "ProLite X2491H",
        "asset_type": "Monitor",
        "notes": ("Part Code: X2491H-B1", "BLACK"),
    },
    "5099206092372": {
        "vendor": "Logitech",
        "model": "MK295",
        "asset_type": "Tastatur/Maus-Set",
        "notes": ("Part Code: 920-009794",),
    },
}


SERIAL_PATTERNS = (
    r"(?<![A-Z0-9])S\s*/\s*N\s*[:#-]?\s*([A-Z0-9-]{5,})",
    r"(?<![A-Z0-9])SN\s*[:#-]\s*([A-Z0-9-]{5,})",
    r"(?<![A-Z0-9])(?:Serial(?: Number)?|Service Tag)\s*[:#-]?\s*([A-Z0-9-]{5,})",
)
MODEL_PATTERNS = (
    r"(?:Model|Product)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 ._/-]{2,40})",
    r"\b(ProLite\s+[A-Z0-9-]{4,})\b",
    r"\b(MK\d{3,4})\b",
    r"\b(HSN-[A-Z0-9-]{3,})\b",
    r"(?:Part Code|Part No\.?|P/N)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,40})",
)

PART_CODE_PATTERNS = (
    r"(?:Part Code|Part No\.?|P/N)\s*[:#-]?\s*([A-Z0-9][A-Z0-9._/-]{2,40})",
    r"\b(920-\d{6})\b",
    r"\b(N\d{5,}-\d{3})\b",
)

MAC_PATTERNS = (
    r"\bMAC\s*[:#-]?\s*([0-9A-F]{2}(?::[0-9A-F]{2}){5})\b",
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
    if re.search(r"\bMK\d{3,4}\b", text, re.IGNORECASE) or _contains_any(text, ("keyboard", "mouse", "tastatur", "maus")):
        return "Tastatur/Maus-Set"
    if re.search(r"\bHSN-[A-Z0-9-]{3,}\b", text, re.IGNORECASE) or _contains_any(text, ("dock", "docking", "port replicator")):
        return "Dockingstation"
    return ""


def _build_notes(text: str) -> str:
    notes = []
    part_code = _first_match(PART_CODE_PATTERNS, text)
    mac_address = _first_match(MAC_PATTERNS, text)
    size = _first_match((r"\b(\d{2}(?:[.,]\d)?)\s*(?:\"|inch|in|\b(?=IPS|Full\s*HD))",), text)

    if part_code:
        notes.append(f"Part Code: {part_code}")
    if mac_address:
        notes.append(f"MAC: {mac_address}")
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


def _known_product_from_text(text: str) -> dict[str, str | tuple[str, ...]]:
    if re.search(r"\b(?:HSN-IX02|N59407-001)\b", text, re.IGNORECASE):
        return {
            "vendor": "HP",
            "model": "HP USB-C Dock G5",
            "asset_type": "Dockingstation",
            "notes": ("Regulatory Model: HSN-IX02",),
        }
    return {}


def _known_product_from_barcode(text: str, barcodes: list[str]) -> dict[str, str | tuple[str, ...]]:
    if re.search(r"\b(?:HSN-[A-Z0-9-]{3,}|N\d{5,}-\d{3})\b", text, re.IGNORECASE):
        return {}

    haystack = [re.sub(r"\D", "", value) for value in barcodes]
    haystack.append(re.sub(r"\D", "", text))

    for barcode, product in PRODUCT_BARCODES.items():
        if any(barcode in value for value in haystack):
            return product
    return {}


def _merge_notes(*groups: str | tuple[str, ...]) -> str:
    notes = []
    for group in groups:
        if isinstance(group, tuple):
            notes.extend(group)
        elif group:
            notes.extend(part.strip() for part in group.split(",") if part.strip())
    return ", ".join(dict.fromkeys(notes))


def parse_label_data(text: str, barcodes: list[str] | None = None) -> dict[str, str]:
    clean_text = " ".join(text.split())
    barcodes = barcodes or []
    product = _known_product_from_text(clean_text) or _known_product_from_barcode(clean_text, barcodes)
    vendor = next((vendor for vendor in VENDORS if re.search(rf"\b{re.escape(vendor)}\b", clean_text, re.I)), "")
    model = _first_match(MODEL_PATTERNS, clean_text)
    asset_type = _detect_asset_type(clean_text)
    notes = _build_notes(clean_text)

    serial = _first_match(SERIAL_PATTERNS, clean_text)

    return {
        "serial_number": serial,
        "vendor": vendor or str(product.get("vendor", "")),
        "model": str(product.get("model", "")) or model,
        "asset_type": asset_type or str(product.get("asset_type", "")),
        "notes": _merge_notes(notes, product.get("notes", ())),
    }

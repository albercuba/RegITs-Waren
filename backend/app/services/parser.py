import re

from app.services.serial_extractor import extract_serial


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

SERIAL_LABEL_PATTERNS = (
    r"S\s*/\s*N",
    r"SN",
    r"Serial(?:\s+No\.?|\s+Number)?",
    r"Seriennummer",
)

PART_MODEL_LABELS = (
    r"Part\s+Code",
    r"Part\s+No\.?",
    r"P\s*/\s*N",
)

MODEL_NO_LABELS = (
    r"Model\s+No\.?",
    r"Model",
    r"Modell",
    r"Artikelnummer",
    r"Item\s+No\.?",
)

NON_VALUE_PATTERN = re.compile(
    r"^(?:Accessories?|Made\s+in\b.*|HDMI\b.*|BLACK|WHITE|SILVER|GREY|GRAY|UPC|EAN|LCD\s+monitor)$",
    re.IGNORECASE,
)
MODEL_VALUE_PATTERN = r"[A-Z0-9][A-Z0-9._/-]{2,40}"
SERIAL_VALUE_PATTERN = r"[A-Z0-9][A-Z0-9-]{5,29}"
EAN_13_SPACED_PATTERN = re.compile(r"\b(\d\s+\d{6}\s+\d{6})\b")
COLOR_PATTERN = re.compile(r"\b(BLACK|WHITE|SILVER|GREY|GRAY)\b", re.IGNORECASE)

UBIQUITI_MODEL_PATTERN = re.compile(
    r"\b((?:U7|U6|UAP|USW|UDM|UCG|UXG)[ \t-]+[A-Z0-9]+(?:[ \t-]+[A-Z0-9]+){0,6})\b",
    re.IGNORECASE,
)
UBIQUITI_SERIAL_PATTERN = re.compile(r"\(([A-Z]{2})\)\s*([0-9A-Fa-f]{12})\b", re.IGNORECASE)
SPACED_UPC_PATTERN = re.compile(r"\b(\d\s+\d{5}\s+\d{5}\s+\d)\b")
UPC_PATTERN = re.compile(r"\b(\d{12})\b")


def _first_match(patterns: tuple[str, ...], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")
    return ""


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(value)}\b", text, re.IGNORECASE) for value in values)


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_obvious_non_value(value: str) -> bool:
    return bool(NON_VALUE_PATTERN.search(value.strip()))


def _format_code(value: str) -> str:
    return value.strip(" .,:;").upper()


def extract_value_after_label(lines: list[str], label_patterns: tuple[str, ...], value_regex: str) -> str | None:
    value_pattern = re.compile(rf"^({value_regex})\b", re.IGNORECASE)
    for index, line in enumerate(lines):
        for label in label_patterns:
            label_match = re.search(rf"\b{label}\b\s*[:#.-]?", line, re.IGNORECASE)
            if not label_match:
                continue

            tail = line[label_match.end():].strip(" :#.-")
            tail_match = value_pattern.search(tail)
            if tail_match and not _is_obvious_non_value(tail_match.group(1)):
                return _format_code(tail_match.group(1))

            for next_line in lines[index + 1:index + 3]:
                if _is_obvious_non_value(next_line):
                    continue
                next_match = value_pattern.search(next_line.strip(" :#.-"))
                if next_match:
                    return _format_code(next_match.group(1))
    return None


def _extract_product_barcode(text: str, barcode_candidates: list[str]) -> str:
    for match in EAN_13_SPACED_PATTERN.finditer(text):
        digits = re.sub(r"\D", "", match.group(1))
        if len(digits) == 13:
            return digits

    for barcode in barcode_candidates:
        digits = re.sub(r"\D", "", barcode)
        if len(digits) in {12, 13}:
            return digits

    return ""


def _extract_product_line(lines: list[str], text: str) -> str:
    match = re.search(r"\b(ProLite)\s+([A-Z0-9-]{4,})\b", text, re.IGNORECASE)
    if match:
        return f"ProLite {_format_code(match.group(2))}"

    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(r"ProLite", line, re.IGNORECASE):
            next_line = lines[index + 1].strip()
            if re.fullmatch(r"[A-Z0-9-]{4,}", next_line, re.IGNORECASE):
                return f"ProLite {_format_code(next_line)}"
    return ""


def _extract_color(text: str) -> str:
    match = COLOR_PATTERN.search(text)
    return match.group(1).upper() if match else ""


def _generic_serial_debug(serial_number: str) -> dict:
    return {
        "best_guess_serial": serial_number,
        "confidence_score": 100,
        "confidence": 1.0,
        "confidence_threshold": 70,
        "needs_confirmation": False,
        "candidates": [
            {
                "value": serial_number,
                "score": 100,
                "source": "labeled_serial",
                "line": None,
                "reasons": ["explicit_serial_label+100"],
                "reason": "explicit_serial_label+100",
                "rejected": False,
            }
        ],
        "normalized_text": "",
        "warnings": [],
    }


def parse_labeled_fields(text: str, barcode_candidates: list[str] | None = None) -> dict[str, str]:
    lines = _clean_lines(text)
    barcode_candidates = barcode_candidates or []
    fields = {
        "serial_number": extract_value_after_label(lines, SERIAL_LABEL_PATTERNS, SERIAL_VALUE_PATTERN) or "",
        "vendor": next((vendor for vendor in VENDORS if re.search(rf"\b{re.escape(vendor)}\b", text, re.I)), ""),
        "model": "",
        "asset_type": _detect_asset_type(text),
        "notes": "",
    }

    part_model = extract_value_after_label(lines, PART_MODEL_LABELS, MODEL_VALUE_PATTERN) or ""
    model_no = extract_value_after_label(lines, MODEL_NO_LABELS, MODEL_VALUE_PATTERN) or ""
    fields["model"] = part_model or model_no

    notes = []
    product_barcode = _extract_product_barcode(text, barcode_candidates)
    product_line = _extract_product_line(lines, text)
    color = _extract_color(text)
    if product_barcode:
        notes.append(f"UPC/EAN: {product_barcode}")
    if product_line:
        notes.append(f"Product line: {product_line}")
    if model_no and part_model:
        notes.append(f"Model No.: {model_no}")
    if color:
        notes.append(f"Color: {color}")
    fields["notes"] = "; ".join(dict.fromkeys(notes))

    return fields


def is_ubiquiti_label(text: str) -> bool:
    has_model = bool(UBIQUITI_MODEL_PATTERN.search(text))
    has_serial_marker = bool(UBIQUITI_SERIAL_PATTERN.search(text))
    return bool(
        re.search(r"\b(?:Ubiquiti|UniFi)\b", text, re.IGNORECASE)
        or re.search(r"\bui\.com\b", text, re.IGNORECASE)
        or has_model
        or (has_serial_marker and has_model)
    )


def _format_ubiquiti_model(value: str) -> str:
    normalized = re.sub(r"[ \t]+", "-", value.strip(" .,:;"))
    parts = [part for part in normalized.split("-") if part]
    if not parts:
        return ""
    prefix = parts[0].upper()
    if prefix in {"U7", "U6", "UAP", "UDM", "UCG", "UXG"}:
        return "-".join(part.upper() for part in [prefix, *parts[1:]])
    if prefix == "USW":
        formatted = [prefix]
        for part in parts[1:]:
            if part.isdigit():
                formatted.append(part)
            elif part.lower() == "poe":
                formatted.append("PoE")
            else:
                formatted.append(part[:1].upper() + part[1:].lower())
        return "-".join(formatted)
    return normalized


def extract_ubiquiti_model(text: str) -> str | None:
    match = UBIQUITI_MODEL_PATTERN.search(text)
    return _format_ubiquiti_model(match.group(1)) if match else None


def extract_ubiquiti_serial(text: str) -> str | None:
    match = UBIQUITI_SERIAL_PATTERN.search(text)
    return match.group(2).upper() if match else None


def _normalize_upc(value: str) -> str:
    return re.sub(r"\D", "", value)


def extract_upc(text: str, barcode_candidates: list[str] | None = None) -> str | None:
    for match in re.finditer(r"\bUPC\b", text, re.IGNORECASE):
        window = text[match.end():match.end() + 80]
        spaced = SPACED_UPC_PATTERN.search(window)
        if spaced:
            return _normalize_upc(spaced.group(1))
        compact = UPC_PATTERN.search(window)
        if compact:
            return compact.group(1)

    for barcode in barcode_candidates or []:
        digits = _normalize_upc(barcode)
        if len(digits) == 12:
            return digits

    return None


def parse_ubiquiti_label(text: str, barcode_candidates: list[str] | None = None) -> dict[str, str] | None:
    haystack = "\n".join([text, *(barcode_candidates or [])])
    if not is_ubiquiti_label(haystack):
        return None

    fields = {
        "vendor": "Ubiquiti",
        "model": extract_ubiquiti_model(haystack) or "",
        "asset_type": "Netzwerkgerät",
        "serial_number": extract_ubiquiti_serial(haystack) or "",
        "notes": "",
    }
    upc = extract_upc(text, barcode_candidates)
    if upc:
        fields["notes"] = f"UPC: {upc}"
    return fields


def _ubiquiti_serial_debug(serial_number: str) -> dict:
    if not serial_number:
        return {
            "best_guess_serial": "",
            "confidence_score": 0,
            "confidence": 0,
            "confidence_threshold": 70,
            "needs_confirmation": True,
            "candidates": [],
            "normalized_text": "",
            "warnings": ["UniFi serial number needs manual confirmation"],
        }

    return {
        "best_guess_serial": serial_number,
        "confidence_score": 100,
        "confidence": 1.0,
        "confidence_threshold": 70,
        "needs_confirmation": False,
        "candidates": [
            {
                "value": serial_number,
                "score": 100,
                "source": "ubiquiti_identifier",
                "line": None,
                "reasons": ["ubiquiti_parenthesized_identifier+100"],
                "reason": "ubiquiti_parenthesized_identifier+100",
                "rejected": False,
            }
        ],
        "normalized_text": "",
        "warnings": [],
    }


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
    if re.search(r"\b(?:HP\s+USB-C\s+DOCK\s+G5|HSN-IX02|N59407-001)\b", text, re.IGNORECASE):
        return {
            "vendor": "HP",
            "model": "HP USB-C Dock G5",
            "asset_type": "Dockingstation",
            "notes": ("Regulatory Model: HSN-IX02",),
        }
    if re.search(r"\b(?:MK295|920-009794)\b", text, re.IGNORECASE):
        return {
            "vendor": "Logitech",
            "model": "MK295",
            "asset_type": "Tastatur/Maus-Set",
            "notes": ("Part Code: 920-009794",),
        }
    if re.search(r"\b(?:PROLITE\s+X2491H|X2491H-B1|PL2491HA)\b", text, re.IGNORECASE):
        return {
            "vendor": "iiyama",
            "model": "ProLite X2491H",
            "asset_type": "Monitor",
            "notes": ("Part Code: X2491H-B1", "BLACK"),
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
    fields, _serial_debug = parse_label_data_with_debug(text, barcodes)
    return fields


def parse_label_data_with_debug(text: str, barcodes: list[str] | None = None) -> tuple[dict[str, str], dict]:
    clean_text = " ".join(text.split())
    barcodes = barcodes or []
    ubiquiti_fields = parse_ubiquiti_label(text, barcodes) or {}
    labeled_fields = {} if ubiquiti_fields else parse_labeled_fields(text, barcodes)
    product = _known_product_from_text(clean_text) or _known_product_from_barcode(clean_text, barcodes)
    vendor = next((vendor for vendor in VENDORS if re.search(rf"\b{re.escape(vendor)}\b", clean_text, re.I)), "")
    model = _first_match(MODEL_PATTERNS, clean_text)
    asset_type = _detect_asset_type(clean_text)
    notes = _build_notes(clean_text)

    resolved_vendor = ubiquiti_fields.get("vendor", "") or labeled_fields.get("vendor", "") or vendor or str(product.get("vendor", ""))
    serial_debug = (
        _ubiquiti_serial_debug(ubiquiti_fields.get("serial_number", ""))
        if ubiquiti_fields
        else _generic_serial_debug(labeled_fields["serial_number"])
        if labeled_fields.get("serial_number")
        else extract_serial(text, barcodes, resolved_vendor)
    )

    return {
        "serial_number": serial_debug["best_guess_serial"],
        "vendor": resolved_vendor,
        "model": ubiquiti_fields.get("model", "") or labeled_fields.get("model", "") or str(product.get("model", "")) or model,
        "asset_type": ubiquiti_fields.get("asset_type", "") or labeled_fields.get("asset_type", "") or asset_type or str(product.get("asset_type", "")),
        "notes": _merge_notes(
            ubiquiti_fields.get("notes", ""),
            labeled_fields.get("notes", ""),
            notes,
            product.get("notes", ()),
        ),
    }, serial_debug

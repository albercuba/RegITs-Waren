import re


VENDORS = ("Dell", "HP", "HPE", "Lenovo", "Apple", "Microsoft", "Cisco", "Ubiquiti", "Samsung")


SERIAL_PATTERNS = (
    r"(?:S/N|SN|Serial(?: Number)?|Service Tag)\s*[:#-]?\s*([A-Z0-9-]{5,})",
)
TICKET_PATTERNS = (
    r"(?:PO|P/O|Ticket|Request|Case)\s*[:#-]?\s*([A-Z0-9-]{4,})",
)
MODEL_PATTERNS = (
    r"(?:Model|Product)\s*[:#-]?\s*([A-Z0-9][A-Z0-9 ._/-]{2,40})",
)


def _first_match(patterns: tuple[str, ...], text: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,:;")
    return ""


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
        "ticket_number": _first_match(TICKET_PATTERNS, clean_text),
    }

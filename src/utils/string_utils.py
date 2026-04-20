# -- Price & Text Sanitisation Utilities --
# Pure functions for cleaning raw DOM-extracted strings into structured values.
# Handles Turkish locale quirks: dot-as-thousands, comma-as-decimal, currency symbols.

import re

def clean_price(price_text: str | None) -> float:
    # Normalise Turkish-formatted price strings (e.g. "38.500,00 TL") into Python floats
    if not price_text:
        return 0.0

    # Strip currency identifiers and whitespace
    cleaned = price_text.replace("TL", "").replace("tl", "").replace("₺", "").strip()
    cleaned = re.sub(r"\s+", "", cleaned)

    # Convert Turkish decimal notation: dots (thousands) → remove, commas (decimal) → dot
    cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def clean_text(text: str | None) -> str:
    # Extract the primary seller name by splitting on "/" delimiters (e.g. "Trendyol / Satıcı")
    if not text:
        return ""
    return text.split("/")[0].strip()

# Static character map for transliterating Turkish-specific Unicode to ASCII equivalents
_TR_MAP = str.maketrans(
    "çÇğĞıİöÖşŞüÜ",
    "cCgGiIoOsSuU",
)

def to_ascii(text: str | None) -> str:
    # Transliterate Turkish characters to their ASCII counterparts for safe string comparison
    if not text:
        return ""
    return text.translate(_TR_MAP)

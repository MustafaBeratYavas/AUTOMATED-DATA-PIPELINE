"""String normalization helpers for scraped marketplace text."""

import re


def clean_price(price_text: str | None) -> float:
    """Convert localized price text into a float, returning ``0.0`` on failure."""
    if not price_text:
        return 0.0

    cleaned = price_text
    for currency_marker in ("TL", "tl", "\u20ba", "\u00e2\u201a\u00ba", "\u00c3\u00a2\u00e2\u20ac\u0161\u00c2\u00ba"):
        cleaned = cleaned.replace(currency_marker, "")
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_text(text: str | None) -> str:
    """Return the primary marketplace label from slash-delimited text."""
    if not text:
        return ""
    return text.split("/")[0].strip()


def normalize_product_code(code: str | None) -> str:
    """Return a stable product-code representation for queue and search input."""
    if not code:
        return ""
    normalized = to_ascii(code)
    normalized = " ".join(normalized.split())
    return normalized.strip().upper()


def canonical_product_code(code: str | None) -> str:
    """Return an alphanumeric-only key for product-code comparisons."""
    normalized = normalize_product_code(code).casefold()
    return re.sub(r"[^a-z0-9]", "", normalized)


def product_code_matches_text(text: str | None, code: str | None) -> bool:
    """Return whether text contains the product code as a bounded token sequence."""
    normalized_code = normalize_product_code(code).casefold()
    if not text or not normalized_code:
        return False

    code_parts = re.findall(r"[a-z0-9]+", normalized_code)
    if not code_parts:
        return False

    normalized_text = to_ascii(text).casefold()
    separator = r"[\s\-_/.,]*"
    pattern = (
        r"(?<![a-z0-9])"
        + separator.join(re.escape(part) for part in code_parts)
        + r"(?![a-z0-9])"
    )
    return re.search(pattern, normalized_text) is not None


_TR_REPLACEMENTS = {
    "\u00e7": "c",
    "\u00c7": "C",
    "\u011f": "g",
    "\u011e": "G",
    "\u0131": "i",
    "\u0130": "I",
    "\u00f6": "o",
    "\u00d6": "O",
    "\u015f": "s",
    "\u015e": "S",
    "\u00fc": "u",
    "\u00dc": "U",
    "\u00c3\u00a7": "c",
    "\u00c3\u2021": "C",
    "\u00c4\u0178": "g",
    "\u00c4\u017d": "G",
    "\u00c4\u00b1": "i",
    "\u00c4\u00b0": "I",
    "\u00c3\u00b6": "o",
    "\u00c3\u2013": "O",
    "\u00c5\u0178": "s",
    "\u00c5\u017d": "S",
    "\u00c3\u00bc": "u",
    "\u00c3\u0152": "U",
    "\u00c3\u0192\u00c2\u00a7": "c",
    "\u00c3\u0192\u00e2\u20ac\u00a1": "C",
    "\u00c3\u201e\u00c5\u00b8": "g",
    "\u00c3\u201e\u00c2\u017d": "G",
    "\u00c3\u201e\u00c2\u00b1": "i",
    "\u00c3\u201e\u00c2\u00b0": "I",
    "\u00c3\u0192\u00c2\u00b6": "o",
    "\u00c3\u0192\u00e2\u20ac\u201c": "O",
    "\u00c3\u2026\u00c5\u00b8": "s",
    "\u00c3\u2026\u00c2\u017d": "S",
    "\u00c3\u0192\u00c2\u00bc": "u",
    "\u00c3\u0192\u00c5\u201c": "U",
}


def to_ascii(text: str | None) -> str:
    """Transliterate supported Turkish characters to ASCII equivalents."""
    if not text:
        return ""
    for source, target in _TR_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text

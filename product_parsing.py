"""Dependency-free text, price and model primitives for product parsers.

Callers choose their preprocessing before extracting model tokens: the offline
crawler preserves retail text, while runtime metadata removes marketing words.
"""
from __future__ import annotations

from html import unescape
import re
from typing import Any, Optional


PRODUCT_MARKETING_TERMS = (
    "geforce", "radeon", "graphics", "graphic", "series", "desktop", "(tm)", "(r)", "processor",
)
PRODUCT_VARIANT_TOKENS = frozenset({"super", "ti", "xtx", "xt", "gre", "x3d", "kf", "f", "k", "u"})
_MODEL_PATTERNS = (
    r"\b(?:rtx|gtx|rx)\s*\d{3,5}\b",
    r"\bultra\s*[3579]?\s*\d{3}[a-z]*\b",
    r"\bi[3579][-\s]?\d{4,5}[a-z]*\b",
    r"\b(?:a|b|h|x|z)\d{3,4}\b",
    r"\bddr[45]\b",
    r"\b\d+\s*(?:gb|tb|w)\b",
    r"\b\d{4,5}x3d\b",
    r"\b\d{3}[a-z]\b",
    r"\b\d{4,5}[a-z]{0,3}\b",
)


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def clean_visible_text(value: Any) -> str:
    return normalize_whitespace(unescape(str(value or "")))


def strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def strip_html(value: str) -> str:
    return clean_visible_text(strip_html_tags(value))


def remove_product_marketing_terms(text: str) -> str:
    for token in PRODUCT_MARKETING_TERMS:
        text = text.replace(token, "")
    return text


def canonical_name(value: Any) -> str:
    # Preserve runtime's legacy spacing after removing adjacent marketing words.
    return remove_product_marketing_terms(normalize_text(value)).replace("  ", " ").strip()


def parse_price_value(text: Any) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", str(text or ""))
    if not digits:
        return None
    value = int(digits)
    return value if value >= 1000 else None


def model_tokens_from_text(text: str) -> set:
    found = []
    for pattern in _MODEL_PATTERNS:
        found.extend(re.findall(pattern, text))
    return {re.sub(r"[^a-z0-9]", "", token) for token in found}

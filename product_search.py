"""Partial retail-name search, separate from strict price/SKU identity matching."""
from pathlib import Path
import json
import re
import unicodedata
from typing import Any


_ALIASES = json.loads(Path(__file__).with_name("product_search_aliases.json").read_text(encoding="utf-8"))
_ALIAS_SEPARATOR = re.compile(r"[\s._-]+")
_ALIAS_KEYS = {
    _ALIAS_SEPARATOR.sub("", alias): canonical
    for canonical, aliases in _ALIASES.items() for alias in aliases
}


def _alias_pattern(alias: str) -> str:
    pattern = r"[\s._-]*".join(re.escape(word) for word in _ALIAS_SEPARATOR.split(alias))
    # Latin aliases must not replace letters inside another brand (e.g. AMD in
    # GAMDIAS). Korean names can attach directly to a model or English label.
    if re.match(r"[a-z]", alias):
        pattern = r"(?<![a-z])" + pattern
    if re.search(r"[a-z]$", alias):
        pattern += r"(?![a-z])"
    return pattern


_ALIAS_PATTERN = re.compile("|".join(
    _alias_pattern(alias) for alias in sorted(
        (alias for aliases in _ALIASES.values() for alias in aliases), key=len, reverse=True
    )
))
_SEARCH_FIELDS = ("product_name", "name", "brand", "manufacturer", "vendor", "chipset", "model", "gpu_model")


def _literal_search_text(text: str) -> str:
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9가-힣\s]", "", text)
    return " ".join(text.split())


def normalize_search_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = _ALIAS_PATTERN.sub(lambda match: _ALIAS_KEYS[_ALIAS_SEPARATOR.sub("", match.group())], text)
    return _literal_search_text(text)


def product_matches_query(query: Any, product: Any) -> bool:
    """All query fragments may appear anywhere, ignoring case and spacing.

    Use each SKU's own name and identity fields; grouped spec_text can mention
    capacities/variants belonging to other products and is not searchable here.
    """
    raw_query = unicodedata.normalize("NFKC", str(query or "")).lower()
    queries = [_literal_search_text(raw_query).split(), normalize_search_text(query).split()]
    if not queries[0]:
        return True
    text = " ".join(str(product.get(field) or "") for field in _SEARCH_FIELDS) if isinstance(product, dict) else product
    raw_text = unicodedata.normalize("NFKC", str(text or "")).lower()
    compacts = [_literal_search_text(raw_text).replace(" ", ""), normalize_search_text(text).replace(" ", "")]
    # Keep the literal name as well, so fragments inside an alias (삼성전,
    # 웨스턴디) are not lost when its complete name is translated.
    return any(all(any(term in compact for compact in compacts) for term in terms) for terms in queries)

"""Shared Danawa block/price extraction; matching policies stay with callers."""
import re
from typing import List, Optional

from product_metadata import parse_price_value


def danawa_candidate_blocks(html: str) -> List[str]:
    starts = [
        m.start()
        for m in re.finditer(
            r"<li\b[^>]*(?:id=[\"']productItem|class=[\"'][^\"']*prod_item)",
            html,
            re.I,
        )
    ]
    if not starts:
        starts = [m.start() for m in re.finditer(r"<div\b[^>]+class=[\"'][^\"']*prod_main_info", html, re.I)]
    return [html[start:starts[i + 1] if i + 1 < len(starts) else len(html)] for i, start in enumerate(starts)]

def price_from_danawa_block(block: str) -> Optional[int]:
    hidden = re.search(r"id=[\"']min_price_[^\"']+[\"'][^>]+value=[\"'](\d+)[\"']", block, re.I)
    if hidden:
        price = parse_price_value(hidden.group(1))
        if price:
            return price

    price_area = re.search(
        r"<p\b[^>]+class=[\"'][^\"']*price_sect[^\"']*[\"'][^>]*>(.*?)</p>",
        block,
        re.I | re.S,
    )
    target = price_area.group(1) if price_area else block
    price_match = re.search(r"(\d[\d,]{3,})(?:\s*</[^>]+>\s*)*\s*원", target, re.I)
    return parse_price_value(price_match.group(1)) if price_match else None

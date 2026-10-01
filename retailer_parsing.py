"""Shared Danawa extraction; matching policies and optional soup stay with callers."""
import re
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import parse_qsl, urljoin, urlsplit

from product_parsing import clean_visible_text, parse_price_value, strip_html_tags


DANAWA_PRODUCT_LINK_SELECTOR = ".prod_name a, a[name='productName'], a.prod_name, a"
_CATEGORY_TOKENS = {
    "gpu": ("그래픽", "vga"),
    "cpu": ("cpu", "프로세서"),
    "ram": ("ram", "메모리"),
    "memory": ("ram", "메모리"),
    "storage": ("ssd", "hdd", "저장", "스토리지"),
    "ssd": ("ssd", "저장", "스토리지"),
    "psu": ("파워", "power"),
    "mb": ("메인보드", "mainboard", "motherboard"),
    "motherboard": ("메인보드", "mainboard", "motherboard"),
}
_EXTENDED_CATEGORY_TOKENS = {
    "hdd": ("hdd", "하드", "저장", "스토리지"),
    "case": ("케이스", "case", "chassis"),
    "software": ("소프트웨어", "운영체제", "os", "windows", "office"),
}
_QUERY_SUFFIXES = {
    "gpu": "그래픽카드", "ram": "메모리", "memory": "메모리",
    "storage": "SSD", "ssd": "SSD", "psu": "파워",
    "mb": "메인보드", "motherboard": "메인보드",
}
_EXTENDED_QUERY_SUFFIXES = {"hdd": "HDD", "case": "PC 케이스", "software": "소프트웨어"}
_GPU_REJECT_TOKENS = (
    "조립pc", "조립 pc", "완본체", "본체", "데스크탑", "데스크톱", "컴퓨터", "pc방",
    "노트북", "워크스테이션", "서버", "미니pc", "베어본", "egpu",
    "쿨러", "cooler", "cooling", "팬", "fan", "수냉", "워터블럭", "water block",
    "백플레이트", "backplate", "라디에이터", "radiator", "방열판", "히트싱크",
    "지지대", "거치대", "브라켓", "라이저", "riser", "케이블", "cable", "가방", "케이스",
    "섀시", "샤시", "chassis", "no hardware",
    "교체품", "부품용", "중고", "리퍼", "refurb", "채굴", "mining",
)
DANAWA_RUNTIME_GPU_REJECT_TOKENS = ("쿨링", "냉각", "딥러닝", "deep learning")


def danawa_category_label_matches(part_type: str, category: str, *, extended_types: bool = True) -> bool:
    """Match already normalized labels; adapters retain their own text cleanup."""
    if not part_type or not category:
        return part_type != "gpu"
    expected = _CATEGORY_TOKENS.get(part_type)
    if extended_types and expected is None:
        expected = _EXTENDED_CATEGORY_TOKENS.get(part_type)
    return expected is None or any(token in category for token in expected)


def append_danawa_query_suffix(query: str, part_type: str, *, extended_types: bool = True) -> str:
    suffix = _QUERY_SUFFIXES.get(part_type, "")
    if extended_types and not suffix:
        suffix = _EXTENDED_QUERY_SUFFIXES.get(part_type, "")
    return f"{query} {suffix}" if suffix and suffix.lower() not in query.lower() else query


def danawa_gpu_name_rejected(name: str, extra_tokens: Tuple[str, ...] = ()) -> bool:
    if not name:
        return True
    compact = re.sub(r"\s+", "", name)
    return any(token in name or token.replace(" ", "") in compact for token in _GPU_REJECT_TOKENS + extra_tokens)


def danawa_url_category_id(url: Any) -> str:
    try:
        parts = urlsplit(str(url or ""))
    except Exception:
        return ""
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() == "cate" and value:
            return value
    return ""


def category_from_danawa_block(block: str, *, clean_text: Callable[[Any], str] = clean_visible_text) -> str:
    match = re.search(r"id=[\"']productItem_categoryInfo_[^\"']+[\"'][^>]+value=[\"']([^\"']+)[\"']", block, re.I)
    return clean_text(match.group(1)) if match else ""


def first_anchor_from_block(block: str, *, clean_text: Callable[[Any], str] = clean_visible_text) -> Tuple[str, str]:
    name_area = re.search(
        r"<p\b[^>]+class=[\"'][^\"']*prod_name[^\"']*[\"'][^>]*>(.*?)</p>",
        block, re.I | re.S,
    )
    area = name_area.group(1) if name_area else block
    link_match = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", area, re.I | re.S)
    if link_match:
        return link_match.group(1), clean_text(strip_html_tags(link_match.group(2)))
    img_match = re.search(r"<img[^>]+alt=[\"']([^\"']+)[\"']", block, re.I | re.S)
    href_match = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"']", block, re.I | re.S)
    return (href_match.group(1) if href_match else ""), clean_text(img_match.group(1) if img_match else "")


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


def danawa_regex_products(
    html: str,
    search_url: str,
    *,
    clean_text: Callable[[Any], str] = clean_visible_text,
) -> Iterator[Dict[str, Any]]:
    """Yield priced records before caller-specific validity checks and enrichment."""
    for block in danawa_candidate_blocks(html):
        if not re.search(r"prod_item|prod_main_info|price_sect|prod_pricelist|min_price_", block, re.I):
            continue
        price = price_from_danawa_block(block)
        if not price:
            continue
        href, name = first_anchor_from_block(block, clean_text=clean_text)
        yield {
            "name": name,
            "price": price,
            "url": urljoin(search_url, href) if href else search_url,
            "category": category_from_danawa_block(block, clean_text=clean_text),
            "block": block,
        }


def danawa_soup_products(
    soup: Any,
    search_url: str,
    *,
    clean_text: Callable[[Any], str] = clean_visible_text,
    link_selector: str = DANAWA_PRODUCT_LINK_SELECTOR,
) -> Iterator[Dict[str, Any]]:
    """Use a caller-created soup so BeautifulSoup remains an optional dependency."""
    nodes = soup.select("li.prod_item, .main_prodlist li, .prod_main_info")
    if not nodes:
        nodes = soup.select(".prod_list .prod_item, .prod_list li")
    for node in nodes:
        category_el = node.select_one("input[id^='productItem_categoryInfo_']")
        category = category_el.get("value") if category_el else ""
        hidden_price_el = node.select_one("input[id^='min_price_']")
        price = parse_price_value(hidden_price_el.get("value")) if hidden_price_el else None
        price_el = node.select_one(
            ".price_sect strong, .prod_pricelist strong, .prod_price strong, "
            ".price_sect a strong, a .num"
        )
        if not price:
            price = parse_price_value(price_el.get_text(" ")) if price_el else None
        if not price:
            continue
        link_el = node.select_one(link_selector)
        href = link_el.get("href") if link_el else ""
        name = clean_text(link_el.get_text(" ")) if link_el else ""
        if not name:
            image_el = node.select_one("img[alt]")
            name = clean_text(image_el.get("alt")) if image_el else ""
        yield {
            "name": name,
            "price": price,
            "url": urljoin(search_url, href) if href else search_url,
            "category": category,
            "node": node,
        }

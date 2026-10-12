"""RAM/SSD purchasing preferences, separate from measured gaming performance.

Recognition is a transparent preference, not a reliability certification.
Only reported specifications earn specification points; missing data stays unknown.
"""
import math
import re

from product_filters import normalize_specs


BRAND_PATTERNS = {
    'samsung': r'samsung\b|삼성전자|삼성(?=\s|\])',
    'klevv': r'(?:(?:essencore|에센코어)\s+)?(?:klevv\b|클레브)',
    'sk_hynix': r'sk\s*(?:hynix\b|하이닉스)',
    'crucial': r'micron\b|crucial\b|마이크론|크루셜',
    'kingston': r'kingston\b|킹스톤',
    'gskill': r'g[. ]?skill\b|지스킬',
    'corsair': r'corsair\b|커세어',
    'teamgroup': r'team\s*group\b|팀그룹',
    'adata': r'adata\b|xpg\b|에이데이타',
    'wd': r'western\s+digital\b|wd\b|웨스턴디지털',
    'solidigm': r'solidigm\b|솔리다임',
    'kioxia': r'kioxia\b|키오시아',
    'seagate': r'seagate\b|씨게이트',
    'sandisk': r'sandisk\b|샌디스크',
    'lexar': r'lexar\b|렉사',
    'transcend': r'transcend\b|트랜센드',
    'patriot': r'patriot\b|패트리어트',
}
RAM_BRANDS = {'samsung', 'klevv', 'sk_hynix', 'crucial', 'kingston', 'gskill',
              'corsair', 'teamgroup', 'adata', 'lexar', 'transcend', 'patriot'}
SSD_BRANDS = set(BRAND_PATTERNS) - {'gskill'}


def recognized_brand(part, kind):
    # Retail title wins over inherited reference metadata. "Other Samsung IC"
    # does not make an unknown module a Samsung product.
    name = str(part.get('product_name') or part.get('name') or
               part.get('brand') or part.get('manufacturer') or '').strip()
    name = re.sub(r'^\[([^\]]+)\]\s*', r'\1 ', name)
    allowed = RAM_BRANDS if kind == 'ram' else SSD_BRANDS
    return next((brand for brand, pattern in BRAND_PATTERNS.items()
                 if brand in allowed and re.match(pattern, name, re.I)), '')


def number(value):
    try:
        result = float(str(value).replace(',', ''))
        return result if math.isfinite(result) and result > 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def is_nvme(part):
    text = ' '.join(str(part.get(key) or '') for key in
                    ('product_name', 'interface', 'protocol', 'spec_text'))
    if not part.get('product_name'):
        text += ' ' + str(part.get('name') or '')
    return bool(re.search(r'\bnvme\b', text, re.I)) and not bool(re.search(r'\bsata\b', text, re.I))


def component_quality(part, kind):
    specs = normalize_specs(part, kind)
    known = bool(recognized_brand(part, kind))
    if kind == 'ram':
        speed = number(specs.get('speed'))
        memory_type = str(part.get('type') or specs.get('memory_type') or '').upper()
        # Beyond these mainstream transfer rates no speculative gaming gain.
        target = 6000 if 'DDR5' in memory_type else 3600
        cl = number(specs.get('cl'))
        latency_ns = 2000 * cl / speed if cl and speed else 0
        latency_bonus = .15 * min(1.0, 10 / latency_ns) if latency_ns else 0
        return .55 * known + .30 * min(1.0, speed / target) + latency_bonus
    nand = str(part.get('nand') or specs.get('nand') or '').upper()
    dram = str(part.get('dram') or specs.get('dram') or '').lower()
    return (.50 * known + .15 * is_nvme(part)
            + .15 * min(1.0, number(specs.get('read_speed')) / 7000)
            + .08 * min(1.0, number(specs.get('write_speed')) / 6000)
            + .08 * (nand in {'TLC', 'MLC', 'SLC'})
            + .04 * (dram in {'yes', 'true'}))


def quality_value_scores(parts, kind, price_for):
    """Allow a modest quality premium while keeping affordable fallbacks.

    Compare like capacities (and RAM generation), not a small stick/SSD with a
    larger kit/drive. Above a 35% premium the price penalty grows; brand alone
    cannot justify several times the equivalent product's price. Budget and
    compatibility remain hard constraints in the build search.
    """
    def group(part):
        return ((str(part.get('type') or '').upper(), number(part.get('gb')))
                if kind == 'ram' else number(part.get('capacity')))
    prices = [max(1, price_for(part)) for part in parts]
    cheapest = {}
    for part, price in zip(parts, prices):
        key = group(part)
        cheapest[key] = min(price, cheapest.get(key, price))
    return [component_quality(part, kind) - max(0.0, price / cheapest[group(part)] - 1.35)
            for part, price in zip(parts, prices)]

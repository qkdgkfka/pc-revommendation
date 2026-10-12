"""Conservative stock-system PSU sizing. Sources/policy: docs/psu-recommendations.md."""
from __future__ import annotations

import math
import re

from server_catalogs import CPU_CATALOG, GPU_CATALOG


_CPU_BY_ID = {p['id']: p for p in CPU_CATALOG}
_GPU_BY_ID = {p['id']: p for p in GPU_CATALOG}

# Manufacturer system recommendations, not GPU consumption. AMD legacy floors
# use ASUS's conservative recommendations; 7700/7800 XT retain AMD's 700W floor.
GPU_PSU_FLOORS = {
    'gpu_rtx3050': 550, 'gpu_rtx3060': 550, 'gpu_rtx3060ti': 600,
    'gpu_rtx4060': 550, 'gpu_rtx4060ti': 550, 'gpu_rtx4070': 650,
    'gpu_rtx4070super': 650, 'gpu_rtx4070ti': 700, 'gpu_rtx4070tisuper': 700,
    'gpu_rtx4080super': 750, 'gpu_rtx4090': 850,
    'gpu_rtx5060': 550, 'gpu_rtx5060ti8': 600, 'gpu_rtx5060ti16': 600,
    'gpu_rtx5070': 650, 'gpu_rtx5070ti': 750, 'gpu_rtx5080': 850, 'gpu_rtx5090': 1000,
    'gpu_rx6600': 550, 'gpu_rx6650xt': 550, 'gpu_rx6750xt': 650,
    'gpu_rx7600': 550, 'gpu_rx7700xt': 700, 'gpu_rx7800xt': 700,
    'gpu_rx7900gre': 750, 'gpu_rx7900xt': 750, 'gpu_rx7900xtx': 850,
    'gpu_rx9070': 650, 'gpu_rx9070xt': 750,
}

# Intel maximum turbo power, where verified; all other CPUs use the conservative
# sizing allowance below rather than pretending their base TDP is peak power.
CPU_TURBO_WATTS = {
    'cpu_i5_12400f': 117, 'cpu_i7_12700kf': 190,
    'cpu_i7_13700k': 253, 'cpu_i9_14900k': 253,
    'cpu_i7_14700k': 253, 'cpu_i5_14400f': 148, 'cpu_i5_14600kf': 181,
    'cpu_ultra_265k': 250, 'cpu_i5_ultra_245k': 159,
}

_CERTIFICATION = re.compile(
    r'80\s*(?:PLUS|\+)\s*[-:：]?\s*'
    r'(Titanium|Platinum|Gold|Silver|Bronze|Standard|White|티타늄|플래티넘|플래티늄|골드|실버|브론즈|스탠다드)',
    re.I,
)
_GOLD_OR_BETTER = {'gold', 'platinum', 'titanium', '골드', '플래티넘', '플래티늄', '티타늄'}


def gold_or_better(psu):
    # A Gold color/brand or a different certification must not pass the gate.
    # Reject conflicting lower grades instead of silently preferring a Gold tag.
    text = ' / '.join(str(psu.get(k) or '') for k in ('product_name', 'name', 'spec_text'))
    grades = [m.lower() for m in _CERTIFICATION.findall(text)]
    if grades:
        return all(grade in _GOLD_OR_BETTER for grade in grades)
    return str(psu.get('rating') or '').strip().lower() in _GOLD_OR_BETTER


def _positive(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value > 0 else 0.0
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _reference(part, catalog):
    return catalog.get(part.get('performance_ref_id')) or catalog.get(part.get('id')) or {}


def _power(parts, *fields):
    return max((_positive(part.get(field)) for part in parts for field in fields), default=0.0)


def cpu_peak_watt(cpu):
    reference = _reference(cpu, _CPU_BY_ID)
    parts = (cpu, reference)
    base = _power(parts, 'tdp') or 65.0
    turbo = CPU_TURBO_WATTS.get(reference.get('id'), 0)
    explicit = _power(parts, 'max_power_watt', 'max_turbo_power', 'ppt')
    if turbo or explicit:
        return max(base, turbo, explicit)
    vendor = str(cpu.get('vendor') or reference.get('vendor') or '').lower()
    socket = str(cpu.get('socket') or reference.get('socket') or '').upper()
    if vendor == 'amd' or socket.startswith('AM'):
        return base * 1.4
    # Unknown Intel/other desktop CPUs: allow boost, including 65W base parts.
    return max(base * 2.1, 155 if base <= 65 else 253)


def recommended_psu_watt(cpu, gpu):
    reference = _reference(gpu, _GPU_BY_ID)
    parts = (gpu, reference)
    board_power = _power(parts, 'tdp', 'board_power_watt', 'tgp', 'tbp') or 150.0
    spec = str(gpu.get('spec_text') or '')
    consumption = re.findall(r'(?:소비전력|TGP|TBP)\s*[:：]?\s*(\d{2,4})\s*W', spec, re.I)
    board_power = max([board_power] + [float(w) for w in consumption])
    floor = max(GPU_PSU_FLOORS.get(reference.get('id'), 0),
                _power(parts, 'recommended_psu_watt', 'min_psu_watt'))
    requirements = re.findall(r'(?:권장\s*(?:파워|전원|PSU)|recommended\s*PSU)\s*[:：]?\s*(\d{3,4})\s*W', spec, re.I)
    floor = max([floor] + [float(w) for w in requirements])
    # 100W for motherboard, memory, drives and fans. Reserve 20% of rated DC
    # output; this is headroom, not an 80 PLUS efficiency conversion.
    load_with_reserve = (cpu_peak_watt(cpu) + board_power + 100) / 0.8
    return int(math.ceil(max(floor, load_with_reserve) / 50) * 50)

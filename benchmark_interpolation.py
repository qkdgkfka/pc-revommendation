"""Transfer only paired native observations from the same review/test workload.

These ratios are estimates for a different configuration, never new measurements.
For an intermediate resolution, prefer the target GPU's own frame-time curve.
Nearby GPUs receive more weight; a weighted median limits one unusual SKU's
influence without discarding or rewriting the source observation.
"""
import math


def review_context(row):
    return tuple(row.get(key, '') for key in (
        'game', 'source_url', 'published_at', 'game_version', 'workload_note',
        'preset', 'preset_label', 'reference_ram', 'reference_ram_gb'))


def _weighted_median(values):
    ordered = sorted(values)
    middle = sum(weight for _, weight in ordered) / 2
    cumulative = 0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= middle:
            return value


def _resolution_curve(anchor, target, rows, target_gpu):
    """Interpolate frame time against pixel count, never extrapolate.

    The fixed overhead plus per-pixel cost model stays between two observed
    endpoints. An inverted average-FPS curve cannot establish that cost, so
    retain the existing paired-GPU fallback. All supported resolutions are 16:9.
    """
    if anchor['gpu_id'] != target_gpu['id']:
        return None
    peers = [row for row in rows
             if review_context(row) == review_context(anchor)
             and row['gpu_id'] == anchor['gpu_id']
             and row['cpu_id'] == anchor['cpu_id']]
    lower = [row for row in peers if int(row['resolution']) < int(target)]
    upper = [row for row in peers if int(row['resolution']) > int(target)]
    if not lower or not upper:
        return None
    before = max(lower, key=lambda row: int(row['resolution']))
    after = min(upper, key=lambda row: int(row['resolution']))
    if before['avg_fps'] < after['avg_fps']:
        return None
    fraction = ((int(target) ** 2 - int(before['resolution']) ** 2)
                / (int(after['resolution']) ** 2 - int(before['resolution']) ** 2))

    def interpolate(field):
        return 1 / ((1 - fraction) / before[field] + fraction / after[field])

    low_ratio = None
    if (before.get('low1_fps') and after.get('low1_fps') and anchor.get('low1_fps')
            and before['low1_fps'] >= after['low1_fps']):
        low_ratio = interpolate('low1_fps') / anchor['low1_fps']
    return dict(ratio=interpolate('avg_fps') / anchor['avg_fps'],
                low_ratio=low_ratio, axis='resolution', pairs=[],
                method='resolution_frame_time_interpolation',
                target_resolution=target,
                anchors=[{key: row.get(key) for key in
                          ('gpu_id', 'cpu_id', 'resolution', 'avg_fps', 'low1_fps', 'source_url')}
                         for row in (before, after)])


def paired_transfer(anchor, axis, target, rows, gpu_index, target_gpu):
    """Return observed CPU/resolution ratios, or None without comparable pairs."""
    if axis not in {'cpu_id', 'resolution'} or anchor[axis] == target:
        return None
    if axis == 'resolution':
        curve = _resolution_curve(anchor, target, rows, target_gpu)
        if curve:
            return curve
    context = review_context(anchor)
    fixed = 'resolution' if axis == 'cpu_id' else 'cpu_id'
    source, destination = {}, {}
    for row in rows:
        if review_context(row) != context or row[fixed] != anchor[fixed]:
            continue
        if row[axis] == anchor[axis]:
            source[row['gpu_id']] = row
        elif row[axis] == target:
            destination[row['gpu_id']] = row
    pairs = []
    field = 'perf_' + anchor['resolution']
    target_perf = float(target_gpu.get(field) or 0)
    if target_perf <= 0:
        return None
    for gpu_id in source.keys() & destination.keys():
        performance = float(gpu_index.get(gpu_id, {}).get(field) or 0)
        if performance <= 0:
            continue
        before, after = source[gpu_id], destination[gpu_id]
        distance = abs(math.log(performance / target_perf))
        pairs.append((distance, gpu_id, before, after))
    if not pairs:
        return None
    pairs.sort(key=lambda pair: (pair[0], pair[1]))
    pairs = pairs[:3]
    ratios, lows = [], []
    evidence = []
    for distance, gpu_id, before, after in pairs:
        weight = 1 / (.15 + distance)
        ratios.append((after['avg_fps'] / before['avg_fps'], weight))
        if before.get('low1_fps') and after.get('low1_fps'):
            lows.append((after['low1_fps'] / before['low1_fps'], weight))
        evidence.append(dict(gpu_id=gpu_id, source_url=before['source_url'],
                             source_value=before[axis], target_value=after[axis],
                             source_fps=before['avg_fps'], target_fps=after['avg_fps']))
    return dict(ratio=_weighted_median(ratios),
                low_ratio=_weighted_median(lows) if lows else None,
                axis=axis, pairs=evidence)


def interpolate_low(curve, target_perf, gpu_index, resolution):
    """Interpolate measured 1% lows independently of average FPS."""
    if curve is None or not all(row.get('low1_fps') for row in curve[1]):
        return None
    lower, upper = curve[1]
    field = 'perf_' + resolution
    fraction = math.log(target_perf / gpu_index[lower['gpu_id']][field]) / math.log(
        gpu_index[upper['gpu_id']][field] / gpu_index[lower['gpu_id']][field])
    return math.exp(math.log(lower['low1_fps']) * (1 - fraction)
                    + math.log(upper['low1_fps']) * fraction)

"""Condition-specific hardware comparisons, with an explicit model fallback.

An aggregate FPS observation cannot identify separate CPU and GPU execution
times. Controlled comparisons report the gap to the best *tested* alternative;
they do not turn that alternative into a theoretical hardware ceiling. Without
both comparison axes, use the existing capacity estimates with an overlapping
pipeline model, and retain low confidence. Percentages are never utilization.
"""
import math
from statistics import median


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def _percent(current, reference):
    return round(100 * max(0.0, 1 - current / max(current, reference)), 1)


def _limiter(cpu, gpu):
    # A five-point decision margin avoids labelling tiny/noisy differences.
    # This is a display tolerance, not a measured or statistical threshold.
    if abs(cpu - gpu) <= 5:
        return 'balanced'
    return 'cpu' if cpu > gpu else 'gpu'


def frame_time_balance(cpu_ceiling, gpu_ceiling):
    cpu, gpu = _positive(cpu_ceiling), _positive(gpu_ceiling)
    result = dict(estimated=True, method='frame_time_model', confidence='low',
                  cpu_fps_ceiling=cpu, gpu_fps_ceiling=gpu,
                  cpu_frame_time_ms=round(1000 / cpu, 2) if cpu else None,
                  gpu_frame_time_ms=round(1000 / gpu, 2) if gpu else None,
                  cpu_percent=None, gpu_percent=None, percent=None,
                  cpu_penalty_pct=None, gpu_penalty_pct=None,
                  limiting_component='unknown',
                  note='게임별 처리 상한 모델 추정이며 실제 사용률이나 실측 병목률이 아닙니다.')
    if cpu is None or gpu is None:
        return result
    # CPU and GPU normally overlap. Equal estimated service times do not
    # imply that both components lose 1 - 2**(-1/4) of their performance.
    throughput = min(cpu, gpu)
    cpu_loss, gpu_loss = _percent(throughput, gpu), _percent(throughput, cpu)
    result.update(cpu_percent=cpu_loss, gpu_percent=gpu_loss,
                  cpu_penalty_pct=cpu_loss, gpu_penalty_pct=gpu_loss,
                  percent=max(cpu_loss, gpu_loss), limiting_component=_limiter(cpu_loss, gpu_loss))
    return result


def _matched_comparison(gpu, cpu, game, resolution, preset, average, evidence, rows, catalogs):
    if evidence.get('method') != 'measured_benchmark' or evidence.get('ram_capacity_match') is False:
        return None
    cpu_id = cpu.get('performance_ref_id') or cpu.get('id')
    gpu_id = gpu.get('performance_ref_id') or gpu.get('id')
    context = {'source_url': evidence.get('source_url'),
               'published_at': evidence.get('published_at'),
               'preset_label': evidence.get('reference_preset'),
               'game_version': evidence.get('game_version', ''),
               'workload_note': evidence.get('workload_note', ''),
               'reference_ram': evidence.get('reference_ram', '')}
    if not context['source_url'] or not context['preset_label']:
        return None
    peers = [row for row in rows
             if row.get('game') == game and row.get('resolution') == str(resolution)
             and row.get('preset') == preset
             and row.get('ray_tracing') is False and row.get('frame_generation') is False
             and row.get('upscaling') == 'native' and _positive(row.get('avg_fps'))
             and all(row.get(key, '') == value for key, value in context.items())]
    anchors = [row for row in peers if (row.get('cpu_id'), row.get('gpu_id')) == (cpu_id, gpu_id)]
    if not anchors:
        return None
    peers = [row for row in peers
             if row.get('reference_ram_gb') == anchors[0].get('reference_ram_gb')]
    observed = median(row['avg_fps'] for row in anchors)
    if abs(observed - average) > .11:
        return None  # A memory/preset adjustment is not this measured configuration.
    gpu_index = {part['id']: part for part in catalogs.get('gpu', ())}
    vendor = gpu_index.get(gpu_id, gpu).get('vendor')
    cpu_rows = [row for row in peers if row.get('gpu_id') == gpu_id]
    gpu_rows = [row for row in peers if row.get('cpu_id') == cpu_id
                and vendor and gpu_index.get(row.get('gpu_id'), {}).get('vendor') == vendor]
    # Driver overhead can depend on CPU + GPU vendor, so a Radeon/GeForce
    # switch is not an isolated GPU capacity comparison.
    comparisons = {}
    for component, candidates, selected in (('cpu', cpu_rows, cpu_id), ('gpu', gpu_rows, gpu_id)):
        grouped = {}
        for row in candidates:
            grouped.setdefault(row[component + '_id'], []).append(row['avg_fps'])
        if len(grouped) < 2:
            return None
        values = {identifier: median(samples) for identifier, samples in grouped.items()}
        best = max(values, key=lambda identifier: (values[identifier], identifier == selected, identifier))
        comparisons[component] = dict(reference_id=best, reference_fps=values[best],
                                      tested_alternatives=len(values) - 1)
    cpu_reference = max(observed, comparisons['cpu']['reference_fps'])
    gpu_reference = max(observed, comparisons['gpu']['reference_fps'])
    cpu_loss, gpu_loss = _percent(observed, cpu_reference), _percent(observed, gpu_reference)
    return dict(estimated=True, method='matched_hardware_comparison',
                confidence='low' if context['reference_ram'] in ('', 'not reported') else 'medium',
                cpu_percent=cpu_loss, gpu_percent=gpu_loss, percent=max(cpu_loss, gpu_loss),
                cpu_penalty_pct=cpu_loss, gpu_penalty_pct=gpu_loss,
                limiting_component=_limiter(cpu_loss, gpu_loss),
                cpu_fps_ceiling=None, gpu_fps_ceiling=None,
                cpu_frame_time_ms=None, gpu_frame_time_ms=None,
                cpu_reference_fps=cpu_reference, gpu_reference_fps=gpu_reference,
                observed_fps=observed, comparisons=comparisons, source_url=context['source_url'],
                note='동일 테스트에서 해당 부품만 바꾼 최상위 실측 대비 차이입니다. '
                     'CPU·메모리 플랫폼 효과를 포함하며 이론적 상한이나 실제 사용률이 아닙니다.')


def estimate_bottleneck(gpu, cpu, game, resolution, preset, average, evidence, rows, catalogs,
                        *, frame_cap=None):
    result = _matched_comparison(gpu, cpu, game, resolution, preset, average, evidence, rows, catalogs)
    if result is None:
        model = evidence.get('bottleneck') or {}
        # The observed throughput is a lower bound on either stage's capacity.
        def capacity(key):
            value = _positive(model.get(key))
            return max(value, average) if value is not None else None
        result = frame_time_balance(capacity('cpu_fps_ceiling'), capacity('gpu_fps_ceiling'))
    cap = _positive(frame_cap)
    if cap is not None and average >= cap:
        result = dict(result, uncapped=result.copy(), frame_cap=cap,
                      limiting_component='frame_cap', cpu_percent=0.0, gpu_percent=0.0,
                      percent=0.0, cpu_penalty_pct=0.0, gpu_penalty_pct=0.0,
                      note='게임의 FPS 상한에 도달해 표시 성능을 제한합니다.')
    return result

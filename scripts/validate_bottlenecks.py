"""Read-only validation against independently checked controlled review cases.

This tests recovery of published comparisons, not out-of-sample prediction
accuracy. Aggregate FPS cannot provide ground-truth CPU/GPU execution times.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import game_benchmarks
    import game_database
    from pcbuilder import fps
    from server_catalogs import CATALOGS, GAME_FPS_PROFILES

    fixture = json.loads((ROOT / 'tests/fixtures/bottleneck_review_cases.json').read_text())
    indexes = {kind: {row['id']: row for row in rows} for kind, rows in CATALOGS.items()}
    report = {'source': fixture['source_url'], 'validation_kind': 'published_comparison_recovery',
              'snapshot_sha256': hashlib.sha256(game_benchmarks.SNAPSHOT_PATH.read_bytes()).hexdigest(),
              'cases': []}
    with patch.object(game_database, 'load_snapshot', return_value=None):
        game_benchmarks.clear_caches()
        for case in fixture['cases']:
            inputs = (indexes['gpu'][fixture['gpu']], indexes['cpu'][case['cpu']], {'gb': 32},
                      fixture['game'], case['resolution'], 144, 'mid', ['rpg'])
            result = fps.estimate_fps_bundle(*inputs)
            bottleneck = result['bottleneck_by_option'][fixture['preset']]
            expected_cpu = round(100 * (1 - case['average'] / case['cpu_reference']), 1)
            expected_gpu = round(100 * (1 - case['average'] / case['gpu_reference']), 1)
            assert result['fps_by_option'][fixture['preset']] == case['average'], case
            assert bottleneck['method'] == 'matched_hardware_comparison', bottleneck
            assert (bottleneck['cpu_percent'], bottleneck['gpu_percent']) == (expected_cpu, expected_gpu), bottleneck
            assert bottleneck['limiting_component'] == case['limiter'], bottleneck
            entry = dict(case, cpu_percent=expected_cpu, gpu_percent=expected_gpu)
            # Reproduce the former percentage formula from the unchanged FPS
            # model's intermediate ceilings. These quantities have a different
            # interpretation from a finite, controlled hardware comparison.
            average, _, evidence = game_benchmarks.estimate_from_measurements(
                inputs[0], inputs[1], inputs[2], fixture['game'], case['resolution'],
                fixture['preset'], GAME_FPS_PROFILES[fixture['game']], CATALOGS)
            legacy = evidence['bottleneck']
            cpu_loss = legacy['cpu_penalty_pct']
            gpu_loss = round(max(0, 1 - average / max(average, legacy['cpu_fps_ceiling'])) * 100, 1)
            entry['previous_capacity_gap_formula'] = dict(
                cpu_percent=cpu_loss, gpu_percent=gpu_loss,
                limiting_component='balanced' if max(cpu_loss, gpu_loss) < 10
                else 'cpu' if cpu_loss >= gpu_loss else 'gpu')
            report['cases'].append(entry)
        observations = game_benchmarks.load_measurements()
        report['controlled_review_rows'] = sum(row['source_url'] == fixture['source_url'] for row in observations)
    report['passed'] = len(report['cases'])
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

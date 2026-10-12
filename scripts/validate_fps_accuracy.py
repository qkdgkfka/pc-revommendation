#!/usr/bin/env python3
"""Read-only, grouped holdout evaluation of the checked-in native FPS snapshot.

condition hides every duplicate of a CPU/GPU/resolution/preset combination;
gpu hides that GPU at every resolution/CPU for the game. No held-out value is
available to the predictor. Games with no remaining observations are reported
as unsupported, not silently counted as accurate. Results describe this review
dataset, not future game patches or unmeasured games.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from unittest.mock import patch


def error_summary(rows):
    errors = [row['ape'] for row in rows if row['ape'] is not None]
    lows = [row['low1_ape'] for row in rows if row['low1_ape'] is not None]
    return dict(n=len(errors), mape=statistics.mean(errors) if errors else None,
                median_ape=statistics.median(errors) if errors else None,
                low1_n=len(lows), low1_mape=statistics.mean(lows) if lows else None)


def evaluate(benchmarks, catalogs, profiles, observations, mode):
    gpu = {row['id']: row for row in catalogs['gpu']}
    cpu = {row['id']: row for row in catalogs['cpu']}
    keys = ('game', 'gpu_id') if mode == 'gpu' else ('game', 'gpu_id', 'cpu_id', 'resolution', 'preset')
    results = []
    for row in observations:
        training = tuple(other for other in observations if any(other[key] != row[key] for key in keys))
        with patch.object(benchmarks, 'load_measurements', return_value=training):
            prediction = benchmarks.estimate_from_measurements(
                gpu[row['gpu_id']], cpu[row['cpu_id']], {'gb': 32},
                row['game'], row['resolution'], row['preset'],
                profiles.get(row['game'], profiles['default']), catalogs)
        average, low = prediction[:2] if prediction else (None, None)
        actual_low = row.get('low1_fps')
        results.append(dict(
            game=row['game'], gpu=row['gpu_id'], cpu=row['cpu_id'],
            resolution=row['resolution'], preset=row['preset'], source=row['source_url'],
            actual=row['avg_fps'], predicted=average,
            ape=abs(average / row['avg_fps'] - 1) if average is not None else None,
            actual_low1=actual_low, predicted_low1=low,
            low1_ape=abs(low / actual_low - 1) if low is not None and actual_low else None))
    groups = defaultdict(list)
    for row in results:
        groups[row['game']].append(row)
    per_game = {game: error_summary(rows) for game, rows in sorted(groups.items())}
    supported = [values for values in per_game.values() if values['n']]
    supported_lows = [values for values in per_game.values() if values['low1_n']]
    summary = dict(mode=mode, total=len(results), predicted=sum(item['n'] for item in supported),
                   macro_mape=statistics.mean(item['mape'] for item in supported) if supported else None,
                   micro_mape=error_summary(results)['mape'],
                   low1_macro_mape=statistics.mean(item['low1_mape'] for item in supported_lows) if supported_lows else None,
                   low1_micro_mape=error_summary(results)['low1_mape'], per_game=per_game)
    return dict(summary=summary, rows=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--mode', choices=('condition', 'gpu'), default='condition')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve()))
    import game_benchmarks as benchmarks
    import game_database
    from server_catalogs import CATALOGS, GAME_FPS_PROFILES, GAME_OPTIONS

    # Never depend on or update the user's live SQLite/cache/crawling state.
    with patch.object(game_database, 'load_snapshot', return_value=None):
        benchmarks.clear_caches()
        observations = benchmarks.load_measurements()
    report = evaluate(benchmarks, CATALOGS, GAME_FPS_PROFILES, observations, args.mode)
    measured_games = {row['game'] for row in observations}
    report['coverage'] = dict(
        selectable_games=len(GAME_OPTIONS), measured_games=len(measured_games),
        without_measurements=[game['id'] for game in GAME_OPTIONS if game['id'] not in measured_games],
        snapshot_sha256=hashlib.sha256(benchmarks.SNAPSHOT_PATH.read_bytes()).hexdigest())
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(summary=report['summary'], coverage=report['coverage']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

import unittest
from unittest.mock import patch

import game_benchmarks as benchmarks
from pcbuilder import fps
from test_empirical_fps import observation


class BenchmarkIndexPerformanceTests(unittest.TestCase):
    def setUp(self):
        benchmarks.clear_caches()
        self.addCleanup(benchmarks.clear_caches)
        self.catalogs = {
            'gpu': [dict(id='small', name='small', perf_1080=50)],
            'cpu': [dict(id='fast', perf=100)],
        }

    def estimate(self, rows):
        with patch.object(benchmarks, 'load_measurements', return_value=rows):
            return benchmarks.estimate_from_measurements(
                self.catalogs['gpu'][0], self.catalogs['cpu'][0], {'gb': 32},
                'fixture', '1080', 'high', {'cpu_weight': .25}, self.catalogs)

    def test_average_and_low_indexes_are_reused_together(self):
        rows = (observation('small', 100, low=40),)
        first = self.estimate(rows)
        misses = benchmarks._measurement_index.cache_info().misses
        self.assertEqual((100, 40), first[:2])
        for _ in range(3):
            self.assertEqual(first, self.estimate(rows))
        self.assertEqual(misses, benchmarks._measurement_index.cache_info().misses,
                         'Average and 1% Low lookups must not evict each other')

    def test_replaced_snapshot_refreshes_both_indexes(self):
        first = (observation('small', 100, low=40),)
        replacement = (observation('small', 125, low=70),)
        self.assertEqual((100, 40), self.estimate(first)[:2])
        self.assertEqual((125, 70), self.estimate(replacement)[:2])
        self.assertEqual((100, 40), self.estimate(first)[:2])

    def test_explicit_clear_refreshes_in_place_snapshot_changes(self):
        rows = [observation('small', 100, low=40)]
        self.assertEqual((100, 40), self.estimate(rows)[:2])
        rows[0] = observation('small', 125, low=70)
        benchmarks.clear_caches()
        self.assertEqual((125, 70), self.estimate(rows)[:2])


class GameAliasIndexPerformanceTests(unittest.TestCase):
    def options(self):
        return [
            {'id': 'first', 'label': 'First Game', 'aliases': ['Shared Alias']},
            {'id': 'second', 'label': 'Second Game', 'aliases': ['Shared Alias', 'Other Alias']},
        ]

    def test_warm_lookup_only_normalizes_request(self):
        with patch.object(fps, 'GAME_OPTIONS', self.options()):
            self.assertEqual('first', fps.normalized_game_key('Shared Alias'))
            with patch.object(fps, 'normalize_text', wraps=fps.normalize_text) as normalize:
                self.assertEqual('second', fps.normalized_game_key('Other Alias'))
                self.assertEqual('first', fps.normalized_game_key('First Game'))
            self.assertEqual(2, normalize.call_count)

    def test_first_match_and_existing_fallback_aliases_are_preserved(self):
        options = self.options()
        with patch.object(fps, 'GAME_OPTIONS', options):
            self.assertEqual('first', fps.normalized_game_key(' SHARED ALIAS '))
            self.assertEqual('csgo2', fps.normalized_game_key('cs2'))
            self.assertEqual('unknown_game', fps.normalized_game_key('Unknown Game'))
            options[0]['aliases'].append('cs2')
            self.assertEqual('first', fps.normalized_game_key('cs2'))
            options.reverse()
            self.assertEqual('second', fps.normalized_game_key('Shared Alias'))

    def test_in_place_alias_label_and_id_edits_invalidate_index(self):
        options = self.options()
        with patch.object(fps, 'GAME_OPTIONS', options):
            self.assertEqual('first', fps.normalized_game_key('Shared Alias'))
            options[0]['aliases'][0] = 'New Alias'
            self.assertEqual('second', fps.normalized_game_key('Shared Alias'))
            self.assertEqual('first', fps.normalized_game_key('New Alias'))
            options[0]['label'] = 'New Label'
            self.assertEqual('first_game', fps.normalized_game_key('First Game'))
            self.assertEqual('first', fps.normalized_game_key('New Label'))
            options[0]['id'] = 'updated'
            self.assertEqual('updated', fps.normalized_game_key('New Label'))

    def test_same_length_option_replacement_and_append_invalidate_index(self):
        options = self.options()
        with patch.object(fps, 'GAME_OPTIONS', options):
            self.assertEqual('first', fps.normalized_game_key('Shared Alias'))
            options[0] = {'id': 'new', 'label': 'New Game', 'aliases': ['Shared Alias']}
            self.assertEqual('new', fps.normalized_game_key('Shared Alias'))
            options.append({'id': 'third', 'label': 'Third Game'})
            self.assertEqual('third', fps.normalized_game_key('Third Game'))


if __name__ == '__main__':
    unittest.main()

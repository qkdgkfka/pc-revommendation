"""Name matching keeps exact priority, first ties and rejected-quote fallback."""
import unittest

from pcbuilder.database import _best_match_key


class PriceMatchingTests(unittest.TestCase):
    def test_exact_name_wins_even_when_substring_candidate_scores_higher(self):
        self.assertEqual('amd ryzen 5', _best_match_key(
            'AMD Ryzen 5', ['amd ryzen 5 retail', 'amd ryzen 5']))

    def test_first_equal_score_wins_and_generator_inputs_work(self):
        self.assertEqual('amd ryzen 5 retail', _best_match_key(
            'amd ryzen 5', iter(['amd ryzen 5 retail', 'amd ryzen 5 boxed'])))

    def test_rejected_exact_and_best_candidates_do_not_hide_valid_fallback(self):
        keys = ['amd ryzen 5', 'amd ryzen 5 retail', 'amd ryzen boxed']
        self.assertEqual('amd ryzen boxed', _best_match_key(
            'amd ryzen 5', keys, lambda key: key == 'amd ryzen boxed'))

    def test_below_threshold_or_no_eligible_candidate_returns_none(self):
        self.assertIsNone(_best_match_key('', ['amd']))
        self.assertIsNone(_best_match_key('amd ryzen', ['intel core i5']))
        self.assertIsNone(_best_match_key('amd ryzen', ['amd ryzen'], lambda key: False))
        self.assertEqual('amd', _best_match_key('amd ryzen 5 7500', ['amd']))

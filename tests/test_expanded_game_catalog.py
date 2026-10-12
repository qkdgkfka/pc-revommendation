"""New choices must work through the same public FPS/recommendation pipeline."""
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from pcbuilder import fps, database, recommendation
from server_catalogs import GAME_OPTIONS, GAME_FPS_PROFILES
from game_catalog_extended import EXTENDED_GAMES, EXTENDED_FPS_PROFILES
from scripts.sync_game_options import frontend_game_options


ADDED_IDS = {
    'rust', 'palworld', 'helldivers2', 'diablo4', 'path_of_exile2', 'monster_hunter_wilds',
    'valheim', 'warframe', 'gta5_legacy', 'total_war_warhammer3', 'civilization6', 'destiny2',
    'stalker2', 'delta_force', 'jedi_survivor', 'plague_tale_requiem', 'dragon_age_veilguard',
    'war_thunder', 'spider_man_remastered', 'kingdom_come_deliverance2', 'league_of_legends',
    'forza_horizon5', 'shadow_of_tomb_raider', 'control',
}

LEGACY_IDS = ADDED_IDS | {
    'dota2', 'f1_24', 'the_last_of_us1', 'spider_man2', 'ratchet_clank', 'space_marine2',
    'expedition33', 'valorant', 'csgo2', 'csgo', 'overwatch2', 'apex', 'rainbow6', 'pubg',
    'cyberpunk2077', 'baldurs_gate3', 'god_of_war_ragnarok', 'black_myth_wukong', 'witcher3',
    'elden_ring', 'ghost_of_tsushima', 'red_dead_redemption2', 'horizon_forbidden_west',
    'hogwarts_legacy', 'starfield', 'genshin_impact', 'wuthering_waves', 'zenless_zone_zero',
    'lostark', 'wow', 'ffxiv', 'cities_skylines2', 'msfs2024', 'farming_sim', 'fortnite',
    'marvel_rivals', 'cod_black_ops6', 'dragons_dogma2', 'dying_light2', 'resident_evil4',
    'alan_wake2',
}


class ExpandedGameCatalogTests(unittest.TestCase):
    def test_at_least_two_hundred_unique_choices_preserve_legacy_ids(self):
        ids = [game['id'] for game in GAME_OPTIONS]
        self.assertGreaterEqual(len(ids), 200)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(LEGACY_IDS.issubset(ids))
        for game in GAME_OPTIONS:
            if game['id'] not in ADDED_IDS | set(EXTENDED_FPS_PROFILES):
                continue
            with self.subTest(game=game['id']):
                self.assertIn(game['category'], {'fps', 'aaa', 'openworld', 'game'})
                self.assertEqual(game['id'], fps.normalized_game_key(game['label']))
                profile = GAME_FPS_PROFILES[game['id']]
                self.assertEqual({'1080', '1440', '2160'}, set(profile['scale']))
                self.assertTrue(all(value > 0 for value in profile['scale'].values()))
                self.assertEqual({'1080', '1440', '2160'}, set(profile['cpu_cap']))
                self.assertTrue(all(value > 0 for value in profile['cpu_cap'].values()))
                self.assertGreater(profile['cpu_weight'], 0)
                self.assertTrue(0 < profile['low1'] <= 1)
                self.assertEqual('unmeasured_workload_prior', profile['model_basis'])

    def test_reference_identity_is_unique_and_does_not_claim_benchmarks_or_features(self):
        self.assertEqual(len(EXTENDED_GAMES), len({r['english_title'].casefold() for r in EXTENDED_GAMES}))
        self.assertEqual(len(EXTENDED_GAMES), len({r['selection_source'] for r in EXTENDED_GAMES}))
        for game in EXTENDED_GAMES:
            with self.subTest(game=game['id']):
                self.assertRegex(game['selection_source'], r'^https://pc-builds.com/ko/games/[A-Za-z0-9]+/[^/]+$')
                self.assertTrue(game['image_url'].startswith('https://images.igdb.com/igdb/image/upload/'))
                self.assertEqual({'scale', 'cpu_weight', 'cpu_cap', 'low1', 'ram_hungry', 'model_basis'},
                                 set(EXTENDED_FPS_PROFILES[game['id']]))
                for alias in game['aliases']:
                    self.assertEqual(game['id'], fps.normalized_game_key(alias))

    def test_frontend_sync_preserves_optional_search_and_artwork_metadata(self):
        legacy = dict(id='legacy', label='Legacy', group='일반 게임', category='game', genre='sim')
        self.assertEqual([legacy], frontend_game_options([legacy]))
        extended = {**legacy, 'aliases': ['별칭'], 'english_title': 'Title',
                    'steam_app_id': 123, 'image_url': '/cover.jpg'}
        self.assertEqual([extended], frontend_game_options([extended]))

    def test_english_titles_and_korean_shorthand_select_same_game(self):
        for name, key in [('롤', 'league_of_legends'), ('LoL', 'league_of_legends'),
                          ('Path of Exile 2', 'path_of_exile2'), ('POE2', 'path_of_exile2'),
                          ('킹덤컴2', 'kingdom_come_deliverance2'), ('Monster Hunter Wilds', 'monster_hunter_wilds'),
                          ('GTA V', 'gta5_legacy'), ('Shadow of the Tomb Raider', 'shadow_of_tomb_raider')]:
            with self.subTest(name=name):
                self.assertEqual(key, fps.normalized_game_key(name))
                self.assertEqual(key, recommendation.RecommendationRequest.from_payload({'game': name}).game)

    def test_new_games_have_finite_option_fps_at_each_resolution(self):
        with patch.object(database, 'db_lookup_price', return_value=None):
            values = set()
            for game in ADDED_IDS | set(EXTENDED_FPS_PROFILES):
                for resolution in ('1080', '1440', '2160'):
                    result = fps.fps_estimate_response({'gpu': 'gpu_rtx5070', 'cpu': 'cpu_r5_7600',
                                                       'ram': 'ram_32_ddr5', 'game': game, 'resolution': resolution})['fps']
                    with self.subTest(game=game, resolution=resolution):
                        self.assertEqual(game, result['game'])
                        self.assertIn(game, GAME_FPS_PROFILES)
                        values.add(result['fps_by_option']['high'])
                        for option, value in result['fps_by_option'].items():
                            self.assertTrue(math.isfinite(value) and value > 0)
                            low = result['low1_by_option'][option]
                            if low is None:
                                self.assertEqual('unavailable', result['option_evidence'][option]['low1_method'])
                            else:
                                self.assertTrue(0 < low <= value)
                        if result['fps_source'] == 'model_estimate':
                            self.assertEqual('low', result['confidence'])
                            self.assertFalse(result['benchmark_source_url'])
                            self.assertIn('실측 자료 없음', result['fps_source_label'])
                        if game in EXTENDED_FPS_PROFILES:
                            self.assertEqual('model_estimate', result['fps_source'])
                            self.assertTrue(result['low1_is_estimated'])
                            for mode in result['graphics_modes']:
                                if mode['id'] != 'native':
                                    self.assertFalse(mode['supported'])
                                    self.assertIsNone(mode['avg_fps'])
            self.assertGreater(len(values), 24)

    def test_each_new_choice_has_local_store_artwork(self):
        root = Path(__file__).resolve().parents[1] / 'public/assets/game-icons'
        for game in ADDED_IDS:
            with self.subTest(game=game):
                self.assertTrue((root / (game + '.jpg')).is_file())

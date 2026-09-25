import json
from pathlib import Path
import tempfile
import unittest
from game_database import save_snapshot, load_snapshot, save_prediction, read_prediction

class GameDatabaseTests(unittest.TestCase):
    def test_snapshot_roundtrip_and_pending_separation(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"pc.db"
            data={"measurements":[{"game":"a","avg_fps":60}], "pending_measurements":[{"game":"b"}], "graphics_measurements":[]}
            save_snapshot(data,db)
            self.assertEqual(load_snapshot(db),data)
            save_snapshot(data,db)
            self.assertEqual(len(load_snapshot(db)["measurements"]),1)

    def test_prediction_revisions_and_conditions_do_not_collide(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"pc.db"
            a={"game":"a","gpu":"x","cpu":"y","resolution":"1440","native":60}
            b={**a,"native":30}
            save_prediction(a,[{"id":"fg2","avg_fps":110}],"v1",db)
            self.assertEqual(read_prediction(a,"v1",db)[0]["avg_fps"],110)
            self.assertIsNone(read_prediction(a,"v2",db))
            self.assertIsNone(read_prediction(b,"v1",db))

    def test_invalid_refresh_rolls_back_previous_observations(self):
        with tempfile.TemporaryDirectory() as d:
            db=Path(d)/"pc.db"
            initial={"measurements":[{"game":"a","avg_fps":60}]}
            save_snapshot(initial,db)
            with self.assertRaises(ValueError):
                save_snapshot({"measurements":[{"game":"b","avg_fps":float("nan")}]},db)
            self.assertEqual(load_snapshot(db),initial)

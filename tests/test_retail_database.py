from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import market_catalog as catalog
import retail_database as db

class RetailDatabaseTests(unittest.TestCase):
    def test_saved_sku_update_keeps_price_history_and_other_models(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"pc.db"
            row={"id":"danawa_cpu_123","name":"Intel i5-14600KF","price":300000,
                 "url":"https://prod.danawa.com/info/?pcode=123","image_url":"https://img.danuri.io/cpu.jpg",
                 "price_checked_at":"2026-09-25T00:00:00Z","image_checked_at":"2026-09-25T00:00:00Z"}
            db.save_products(path,"cpu",[row])
            db.save_products(path,"cpu",[{**row,"price":290000,"price_checked_at":"2026-09-25T01:00:00Z"}])
            rows=db.read_products(path)["cpu"]
            self.assertEqual(1,len(rows))
            self.assertEqual(290000,rows[0]["price"])
            import sqlite3
            with closing(sqlite3.connect(path)) as conn:
                self.assertEqual(2,conn.execute("SELECT count(*) FROM retail_price_history").fetchone()[0])
            with patch.object(catalog,"DATA_DIR",Path(folder)), patch.object(catalog,"SNAPSHOT_PATH",Path(folder)/"none.json"), patch.object(catalog,"CACHE_PATH",Path(folder)/"none2.json"):
                self.assertEqual(290000,catalog.saved_products("cpu")[0]["price"])

    def test_bad_price_or_unverified_photo_is_not_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"pc.db"
            db.save_products(path,"cpu",[{"id":"bad","price":0},{"id":"no-photo","price":10000}])
            self.assertEqual({},db.read_products(path))

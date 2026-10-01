"""Run regression tests with disposable copies of mutable application data."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def main():
    import game_database
    import market_catalog
    import product_images
    from pcbuilder import runtime

    with tempfile.TemporaryDirectory(prefix='pc-tests-') as temporary:
        data = Path(temporary)
        for name in ('pc.db', 'game_benchmarks.json', 'product_catalog.json', 'market_cache.json'):
            source = ROOT / 'data' / name
            if source.exists():
                shutil.copy2(source, data / name)
        runtime.DB_PATH = game_database.DB_PATH = data / 'pc.db'
        market_catalog.DATA_DIR = data
        market_catalog.SNAPSHOT_PATH = data / 'product_catalog.json'
        market_catalog.CACHE_PATH = data / 'market_cache.json'
        product_images.DISK_CACHE_DIR = data / 'product_images'
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
        return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())

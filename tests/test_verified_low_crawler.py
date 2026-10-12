"""Source boundary tests: metric identity, provenance, and safe persistence."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures'


class VerifiedLowCrawlerTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'scripts/refresh_verified_lows.py'
        self.assertTrue(path.exists(), 'The verified low-FPS source collector must exist')
        spec = importlib.util.spec_from_file_location('verified_lows', path)
        self.crawler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.crawler)
        self.html = (FIXTURES / 'b2g_low_review.html').read_text()
        self.csv = (FIXTURES / 'b2g_low_rows.csv').read_text()

    def test_actual_csv_metric_and_reference_card_survive_normalization(self):
        rows, pending = self.crawler.parse_source(self.html, self.csv, '2026-10-11T00:00:00+00:00')
        self.assertEqual([], pending)
        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(('pubg', 'gpu_rtx5070', 'cpu_r7_9800x3d', '1080'),
                         tuple(row[k] for k in ('game', 'gpu_id', 'cpu_id', 'resolution')))
        self.assertEqual((220.0, 83.6), (row['avg_fps'], row['low1_fps']))
        self.assertEqual('1% low average FPS', row['low_metric_label'])
        self.assertEqual('reported_1_percent_low_average', row['low_metric'])
        self.assertTrue(row['published_at'].startswith('2025-03-05'))
        self.assertTrue(row['source_updated_at'].startswith('2026-02-18'))
        self.assertIsNone(row['reference_ram_gb'])
        self.assertIn('custom scene', row['workload_note'].lower())

    def test_minimum_or_percentile_column_cannot_be_relabelled_as_one_percent_low(self):
        for label in ('Minimum FPS', 'P1 FPS', '1% percentile FPS'):
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.crawler.parse_source(self.html, self.csv.replace('1% low average FPS', label), 'now')

    def test_conflicting_unused_factory_oc_variant_does_not_override_reference(self):
        records = list(csv.DictReader(io.StringIO(self.csv)))
        altered = dict(records[1], **{'1% low average FPS': '90.0'})
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader(); writer.writerows(records + [altered])
        rows, _ = self.crawler.parse_source(self.html, output.getvalue(), 'now')
        self.assertEqual((220.0, 83.6), (rows[0]['avg_fps'], rows[0]['low1_fps']))

    def test_invalid_or_conflicting_source_row_is_not_silently_accepted(self):
        reader = list(csv.DictReader(io.StringIO(self.csv)))
        reference = next(r for r in reader if 'Founders Edition' in r['Model'])
        for bad in ('NaN', '0', '9999', '12 fps'):
            modified = dict(reference, **{'1% low average FPS': bad})
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=reference.keys())
            writer.writeheader(); writer.writerow(modified)
            with self.subTest(value=bad), self.assertRaises(ValueError):
                self.crawler.parse_source(self.html, output.getvalue(), 'now')
        modified = dict(reference, **{'1% low average FPS': '80.0'})
        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=reference.keys())
        writer.writeheader(); writer.writerows([reference, modified])
        with self.assertRaises(ValueError):
            self.crawler.parse_source(self.html, output.getvalue(), 'now')

    def test_failed_reference_conditions_stop_import(self):
        for before, after in [('Ryzen 7 9800X3D', 'Ryzen 9 7950X3D'),
                              ('data-mode=”Raster”', 'data-mode=”Ray Tracing”')]:
            with self.subTest(condition=before), self.assertRaises(ValueError):
                self.crawler.parse_source(self.html.replace(before, after), self.csv, 'now')

    def test_refresh_preserves_other_sources_and_is_idempotent_with_raw_evidence(self):
        from game_database import load_snapshot
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); snapshot = root / 'snapshot.json'; db = root / 'test.db'
            untouched = {'source_url': 'https://other.example/review', 'game': 'other', 'avg_fps': 55}
            initial = {'schema_version': 1, 'measurements': [untouched],
                       'graphics_measurements': [{'mode': 'fg'}], 'feature_support': {'foo': True},
                       'pending_measurements': [{'source_url': 'other-pending'}], 'sources': []}
            snapshot.write_text(json.dumps(initial))
            sources = {self.crawler.REVIEW_URL: self.html.encode(), self.crawler.CSV_URL: self.csv.encode()}
            fetch = lambda url: sources[url]
            for _ in range(2):
                self.crawler.refresh(snapshot, db, root / 'evidence', fetcher=fetch)
            saved = json.loads(snapshot.read_text())
            self.assertEqual(2, len(saved['measurements']))
            self.assertEqual(untouched, saved['measurements'][0])
            self.assertEqual(initial['graphics_measurements'], saved['graphics_measurements'])
            self.assertEqual(initial['feature_support'], saved['feature_support'])
            self.assertEqual(initial['pending_measurements'], saved['pending_measurements'])
            self.assertEqual(saved, load_snapshot(db))
            self.assertEqual(2, len(list((root / 'evidence').glob('*.gz'))))
            evidence = saved['sources'][-1]['raw_evidence']
            self.assertEqual(2, len(evidence))
            import gzip, hashlib
            for item in evidence:
                raw = gzip.decompress((root / 'evidence' / item['filename']).read_bytes())
                self.assertEqual(item['sha256'], hashlib.sha256(raw).hexdigest())

    def test_fetch_or_database_failure_does_not_replace_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); snapshot = root / 'snapshot.json'
            initial = '{"measurements": [], "marker": "keep"}'
            snapshot.write_text(initial)
            with self.assertRaises(OSError):
                self.crawler.refresh(snapshot, root / 'db', root / 'evidence',
                                     fetcher=lambda _: (_ for _ in ()).throw(OSError('offline')))
            self.assertEqual(initial, snapshot.read_text())
            sources = {self.crawler.REVIEW_URL: self.html.encode(), self.crawler.CSV_URL: self.csv.encode()}
            with patch.object(self.crawler, 'save_snapshot', side_effect=OSError('disk failed')):
                with self.assertRaises(OSError):
                    self.crawler.refresh(snapshot, root / 'db', root / 'evidence', fetcher=sources.__getitem__)
            self.assertEqual(initial, snapshot.read_text())


if __name__ == '__main__':
    unittest.main()

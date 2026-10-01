from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import product_images as images


class ImagePerformanceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.disk = patch.object(images, 'DISK_CACHE_DIR', Path(self.folder.name))
        self.disk.start()
        self.addCleanup(self.disk.stop)
        images._cache.clear()
        self.addCleanup(images._cache.clear)

    def test_validated_disk_photo_reuses_memory_without_repeated_disk_reads(self):
        url, data = 'https://img.danuri.io/performance.jpg', b'\xff\xd8\xffphoto'
        images.persist_product_image(url, data)
        with patch.object(images, 'disk_product_image', wraps=images.disk_product_image) as read, \
             patch.object(images, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual((data, 'image/jpeg'), images.fetch_product_image(url))
            self.assertEqual((data, 'image/jpeg'), images.fetch_product_image(url))
        self.assertEqual(1, read.call_count)

    def test_replaced_disk_photo_invalidates_memory(self):
        url = 'https://img.danuri.io/replaced.jpg'
        first, second = b'\xff\xd8\xfffirst', b'\xff\xd8\xffsecond-and-new'
        images.persist_product_image(url, first)
        with patch.object(images, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(first, images.fetch_product_image(url)[0])
            images.persist_product_image(url, second)
            self.assertEqual(second, images.fetch_product_image(url)[0])


if __name__ == '__main__':
    unittest.main()

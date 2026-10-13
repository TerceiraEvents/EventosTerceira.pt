"""Verify original artwork fixture bytes, provenance and deterministic PNG pixels."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / 'scripts/tests/fixtures/artwork'
spec = importlib.util.spec_from_file_location('fixture_generator', ROOT / 'scripts/generate_artwork_fixtures.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class ArtworkFixtures(unittest.TestCase):
    """Checks for source-to-repository byte integrity and complete PNG framing."""

    def test_source_and_hosted_bytes_match_recorded_provenance(self):
        manifest = json.loads((FIXTURES / 'manifest.json').read_text())
        self.assertEqual(manifest['license'], 'CC0-1.0')
        for item in manifest['images']:
            source = (FIXTURES / 'source' / (item['name'] + '.png')).read_bytes()
            hosted = (ROOT / item['repo_image'].lstrip('/')).read_bytes()
            self.assertEqual(source, hosted)
            self.assertEqual(hashlib.sha256(hosted).hexdigest(), item['sha256'])
            self.assertEqual(item['fetch_content_type'], 'image/png')
            self.assertIn('/scripts/tests/fixtures/artwork/source/', item['image_source'])

    def test_png_dimensions_crc_and_edge_pixels_are_intact(self):
        manifest = json.loads((FIXTURES / 'manifest.json').read_text())
        for item in manifest['images']:
            data = (FIXTURES / 'source' / (item['name'] + '.png')).read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            offset = 8
            compressed = []
            while offset < len(data):
                length = struct.unpack('!I', data[offset:offset + 4])[0]
                kind = data[offset + 4:offset + 8]
                payload = data[offset + 8:offset + 8 + length]
                crc = struct.unpack('!I', data[offset + 8 + length:offset + 12 + length])[0]
                self.assertEqual(crc, zlib.crc32(kind + payload))
                if kind == b'IHDR': self.assertEqual(struct.unpack('!IIBBBBB', payload), (item['width'], item['height'], 8, 2, 0, 0, 0))
                if kind == b'IDAT': compressed.append(payload)
                offset += length + 12
            pixels = zlib.decompress(b''.join(compressed))
            stride = 1 + item['width'] * 3
            self.assertEqual(len(pixels), stride * item['height'])
            self.assertEqual(pixels[0], 0)
            self.assertEqual(pixels[1:4], bytes((255, 210, 0)))
            right = 1 + (item['width'] - 1) * 3
            self.assertEqual(pixels[right:right + 3], bytes((0, 80, 255)))
            center = 1 + (item['width'] // 2) * 3
            self.assertEqual(pixels[center:center + 3], bytes((230, 30, 60)))
            bottom = stride * (item['height'] - 1) + center
            self.assertEqual(pixels[bottom:bottom + 3], bytes((0, 160, 90)))
            self.assertIn(b'TEST ONLY', data)
            self.assertIn(b'CC0-1.0', data)

    def test_corrupt_encoded_fixture_is_truncated_original_without_complete_chunks(self):
        original = (FIXTURES / 'source/portrait.png').read_bytes()
        data = (ROOT / 'assets/images/test-fixtures/corrupt-encoded.png').read_bytes()
        self.assertEqual(data, original[:64])
        self.assertNotIn(b'IEND', data)
        offset = 33
        length = struct.unpack('!I', data[offset:offset + 4])[0]
        self.assertLess(len(data), offset + 12 + length)
        manifest = json.loads((FIXTURES / 'manifest.json').read_text())
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest['negative_images'][0]['sha256'])

    def test_generator_is_deterministic(self):
        self.assertEqual(generator._png(600, 900), (FIXTURES / 'source/portrait.png').read_bytes())

    def test_shared_records_are_labelled_non_production_and_record_rights(self):
        data = json.loads((FIXTURES / 'events.json').read_text())
        self.assertIn('TEST ONLY', data['purpose'])
        self.assertEqual(len(data['events']), 7)
        for record in data['events']:
            self.assertTrue(record['name'].startswith('TEST ONLY'))
            self.assertTrue(record['id'].startswith('artwork-fixture-'))
            if record['id'].split('-')[-1] in ['portrait', 'landscape', 'oversized']:
                self.assertIn('CC0-1.0', record['image_rights'])
                self.assertTrue(record['image_alt_en'])
                self.assertTrue(record['image_alt_pt'])
        production = (ROOT / '_data/special_events.yml').read_text()
        self.assertNotIn('artwork-fixture-', production)


if __name__ == '__main__':
    unittest.main()

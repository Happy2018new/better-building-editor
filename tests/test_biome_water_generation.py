"""Resource provenance and missing-default handling, independent of rendering."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import generate_biome_water as generate


class BiomeWaterGenerationTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        self.data = json.loads(generate.DEFAULT_SOURCE.read_text(encoding='utf8'))

    def test_saved_assets_reproduce_runtime_and_distinct_ocean_appearances(self):
        generate.validate(self.data, self.manifest)
        self.assertEqual(generate.DEFAULT_OUTPUT.read_text(encoding='ascii'),
                         generate.runtime_source(self.data))
        rows = dict((row['identifier'], row) for row in self.data['rows'])
        self.assertEqual(87, len(rows))
        self.assertEqual(('02B0E5', .55), (rows['minecraft:warm_ocean']['surface_color'],
                                         rows['minecraft:warm_ocean']['surface_opacity']))
        self.assertEqual('2080C9', rows['minecraft:cold_ocean']['surface_color'])
        self.assertIsNone(rows['minecraft:plains']['surface_opacity'])

    def test_altered_rows_and_registry_provenance_are_rejected(self):
        for field, value in (('schema', 2), ('game_version', 'NEMC next'),
                             ('palette_sha256', '0' * 64), ('rows_sha256', '0' * 64)):
            data = dict(self.data, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                generate.validate(data, self.manifest)
        data = copy.deepcopy(self.data)
        data['rows'][0]['surface_color'] = 'FFFFFF'
        with self.assertRaisesRegex(ValueError, 'have changed'):
            generate.validate(data, self.manifest)

    def test_duplicate_and_invalid_resource_paths_are_rejected(self):
        for change in ('duplicate', 'traversal', 'source_hash'):
            data = copy.deepcopy(self.data)
            if change == 'duplicate':
                data['rows'].append(data['rows'][0])
            elif change == 'traversal':
                data['rows'][0]['source_file'] = 'biomes/../../other.json'
            else:
                data['rows'][0]['source_sha256'] = 'invalid'
            data['rows_sha256'] = generate.digest(data['rows'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                generate.validate(data, self.manifest)

    def test_explicit_zero_opacity_is_not_confused_with_an_unspecified_default(self):
        self.assertEqual(('123ABC', 0), generate.water_fields(
            {'surface_color': '#123abc', 'surface_opacity': 0}))
        self.assertEqual(('123ABC', None), generate.water_fields({'surface_color': '#123abc'}))
        for value in (-.01, 1.01, True, '0.65', float('nan')):
            with self.subTest(opacity=value), self.assertRaises(ValueError):
                generate.water_fields({'surface_color': '#123abc', 'surface_opacity': value})

    def test_capture_preserves_exact_file_fingerprint_and_unresolved_default(self):
        import hashlib
        document = {'format_version': '1.21.120', 'minecraft:client_biome': {
            'description': {'identifier': 'minecraft:plains'}, 'components': {
                'minecraft:water_appearance': {'surface_color': '#44Aff5'}}}}
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory)
            (pack / 'biomes').mkdir()
            path = pack / 'biomes/plains.client_biome.json'
            raw = json.dumps(document).encode('ascii')
            path.write_bytes(raw)
            data = generate.capture(pack, self.manifest)
            generate.validate(data, self.manifest)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), data['rows'][0]['source_sha256'])
            self.assertIsNone(data['rows'][0]['surface_opacity'])
            # A byte-only change must also invalidate the asset snapshot.
            path.write_bytes(raw + b'\n')
            self.assertNotEqual(data, generate.capture(pack, self.manifest))
            document['minecraft:client_biome']['components'] = {}
            path.write_text(json.dumps(document), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'Missing native water'):
                generate.capture(pack, self.manifest)


if __name__ == '__main__':
    unittest.main()

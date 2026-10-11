"""Reject contaminated logical sources before any native corner analysis."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_frozen_liquid_surfaces import checked_fingerprint, difference_mask, fingerprint, isolated_source
from capture_frozen_liquid_controls import fixture_plan
from projection.cell import AIR, encode, make_cell


class FrozenSurfaceAnalysisTests(unittest.TestCase):
    def source(self, identity='water_depth_0_foreground'):
        # Match the JSON report form, including logical cells with tagged layers.
        return json.loads(json.dumps(fixture_plan(identity, (10, 100, 10), (6, 98, 6))))

    def test_foreground_and_standalone_background_sources_keep_layer_identity(self):
        for identity in ('water_depth_0_foreground', 'water_depth_0_background'):
            with self.subTest(identity=identity):
                self.assertEqual(('minecraft:water', 0), isolated_source(self.source(identity)))

    def test_waterlogged_body_actor_or_liquid_pool_are_rejected(self):
        source = self.source()
        for value in (make_cell(('minecraft:water', 0), ('minecraft:oak_fence', 0)),
                      make_cell(('minecraft:water', 0), AIR, {'test': 1})):
            changed = deepcopy(source)
            changed['controls']['liquid_only']['cells'][0][1] = encode(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                isolated_source(changed)
        source['controls']['liquid_only']['cells'].append([[11, 100, 10], ['minecraft:water', 0]])
        with self.assertRaises(ValueError):
            isolated_source(source)

    def test_empty_control_and_supported_union_are_verified(self):
        source = self.source()
        for control in ('empty', 'supported_positive'):
            changed = deepcopy(source)
            changed['controls'][control]['cells'].append([[12, 100, 10], ['minecraft:stone', 0]])
            with self.subTest(control=control), self.assertRaises(ValueError):
                isolated_source(changed)

    def test_changed_context_shell_or_wrong_origin_is_rejected(self):
        for changes in ({'context_changed': True}, {'shell': [[9, 100, 10]]},
                        {'cell_origin': [11, 100, 10]}, {'layer': 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                isolated_source(dict(self.source(), **changes))

    def test_png_difference_uses_original_threshold_and_full_viewport(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ('first.png', 'second.png'))
            image = Image.new('RGB', (20, 10), (10, 20, 30))
            image.save(second)
            image.putpixel((5, 4), (26, 20, 30))
            image.putpixel((6, 4), (27, 20, 30))
            image.save(first)
            mask = difference_mask(first, second, 16)
            self.assertEqual((20, 10), mask.size)
            self.assertEqual(0, mask.getpixel((5, 4)))
            self.assertEqual(255, mask.getpixel((6, 4)))

    def test_changed_evidence_bytes_cannot_pass_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_bytes(b'{"passed":true}')
            record = fingerprint(path)
            self.assertEqual(record, checked_fingerprint(record))
            path.write_bytes(b'{"passed":false}')
            with self.assertRaises(ValueError):
                checked_fingerprint(record)

    def test_archived_source_must_match_original_bytes_and_retains_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.py'
            archive = Path(directory) / 'original.py'
            source.write_bytes(b'original capture source')
            record = fingerprint(source)
            archive.write_bytes(source.read_bytes())
            source.write_bytes(b'new capture source')
            accepted = checked_fingerprint(record, [archive])
            self.assertEqual(record['sha256'], accepted['sha256'])
            self.assertEqual(record['path'], accepted['reported_path'])
            self.assertEqual(str(archive.resolve()), accepted['path'])
            self.assertNotIn('reported_path', record)
            archive.write_bytes(b'new capture source')
            with self.assertRaises(ValueError):
                checked_fingerprint(record, [archive])
            source.unlink()
            with self.assertRaises(ValueError):
                checked_fingerprint(record, [archive])

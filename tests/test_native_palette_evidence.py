"""Replay native palette ownership; malformed or stale evidence stays rejected."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_native_palette_adapter import SIDES, inspect, palette, snapshot_fingerprint
from projection import native_palette_actor_data as source
from projection.cell import actor_data, freeze
from projection.model import Document
from projection.native_palette_actor import resolve_name
from projection.world_capture import merge_palette, native_actor_cells


class NativePaletteEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        version = cls.manifest['game_version'].removeprefix('NEMC ')
        cls.report = json.loads((ROOT / 'tools/data' / ('native_palette_actors_nemc_' + version + '.json')).read_text(encoding='utf8'))

    def test_observed_wet_names_and_explicit_unusable_cases_match_generated_rules(self):
        names, unusable = inspect(self.report, self.manifest)
        self.assertEqual(set(names), source.WET_ACTOR_NAMES)
        self.assertEqual(tuple(unusable), source.UNUSABLE_NATIVE_CASES)
        self.assertIn('minecraft:standing_sign', names)
        self.assertIn('minecraft:decorated_pot', names)
        self.assertNotIn('minecraft:bed', names)
        self.assertNotIn('minecraft:moving_block', names)

    def test_every_verified_native_actor_payload_survives_client_and_server_capture(self):
        excluded = {case for case, side, reason in source.UNUSABLE_NATIVE_CASES}
        replayed = 0
        for row in self.report['rows']:
            if row['id'] in excluded:
                continue
            size = tuple(row['high'][i] - row['low'][i] + 1 for i in range(3))
            for side in SIDES:
                native = palette(row[side]['palette'])
                before = freeze(native)
                document = Document(size)
                merge_palette(document, native, (0, 0, 0), size, (0, 0, 0))
                located = dict(native_actor_cells(native, (0, 0, 0), size))
                expected = {}
                for entries in native.get('actor', {}).values():
                    for index, payload in entries.items():
                        y, remainder = divmod(index, size[0] * size[2])
                        x, z = divmod(remainder, size[2])
                        expected[(x, y, z)] = payload
                self.assertEqual(set(expected), set(located), (row['id'], side))
                for pos, payload in expected.items():
                    self.assertEqual(payload, actor_data(document.get(pos)), (row['id'], side, pos))
                self.assertEqual(before, freeze(native))
                replayed += 1
        self.assertGreater(replayed, 700)

    def test_incomplete_unrestored_or_wrong_registry_evidence_is_rejected(self):
        for key, value in (('completed', False), ('restored', False),
                           ('palette_sha256', '0' * 64), ('game_version', 'NEMC next')):
            report = dict(self.report, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect(report, self.manifest)
        report = dict(self.report, rows=self.report['rows'][:-1])
        with self.assertRaises(ValueError):
            inspect(report, self.manifest)

    def test_stale_runtime_alias_rule_cannot_resolve_wet_actor(self):
        front, back = ('minecraft:standing_sign', 0), ('minecraft:water', 0)
        with patch.object(source, 'SOURCE_VERSION', 'NEMC next'):
            with self.assertRaisesRegex(ValueError, 'need regeneration'):
                resolve_name('minecraft:water', front, back)
            self.assertEqual(front[0], resolve_name(front[0], front, back))

    def test_native_json_fingerprint_survives_windows_checkout_but_detects_content_changes(self):
        raw = json.dumps(self.report, indent=2).replace('\n', '\r\n')
        self.assertEqual(source.SOURCE_SHA256, snapshot_fingerprint(json.loads(raw)))
        changed = dict(self.report, game_version='NEMC next')
        self.assertNotEqual(source.SOURCE_SHA256, snapshot_fingerprint(changed))


if __name__ == '__main__':
    unittest.main()

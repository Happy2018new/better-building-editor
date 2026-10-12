"""Replay native palette ownership; malformed or stale evidence stays rejected."""
import json
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from generate_native_palette_adapter import SIDES, inspect, palette, snapshot_fingerprint
from native_bed_evidence import inspect as inspect_beds
from projection import native_palette_actor_data as source
from projection.cell import actor_data, freeze, make_cell, thaw
from projection.model import Document, Editor, close_group_selection
from projection.visible_actor import chest_is_single, compose_actor
from projection.native_palette_actor import resolve_name
from projection.world_capture import merge_palette, native_actor_cells


class NativePaletteEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        version = cls.manifest['game_version'].removeprefix('NEMC ')
        cls.report = json.loads((ROOT / 'tools/data' / ('native_palette_actors_nemc_' + version + '.json')).read_text(encoding='utf8'))
        cls.beds = json.loads((ROOT / 'tools/data' / ('native_bed_capture_nemc_' + version + '.json')).read_text(encoding='utf8'))

    def test_observed_wet_names_and_explicit_unusable_cases_match_generated_rules(self):
        names, unusable = inspect(self.report, self.manifest)
        bed_names, checked = inspect_beds(self.beds, self.manifest)
        self.assertEqual(set(names) | set(bed_names), source.WET_ACTOR_NAMES)
        self.assertEqual(128, checked)
        self.assertEqual(checked, source.PAIRED_BED_PALETTES)
        self.assertEqual(tuple(unusable), source.UNUSABLE_NATIVE_CASES)
        self.assertIn('minecraft:standing_sign', names)
        self.assertIn('minecraft:decorated_pot', names)
        self.assertNotIn('minecraft:bed', names)
        self.assertNotIn('minecraft:moving_block', names)
        self.assertIn('minecraft:bed', source.WET_ACTOR_NAMES)

    def test_native_server_only_single_chests_keep_contents_and_selection_after_passive_edit(self):
        identities = {'minecraft:chest_dry', 'minecraft:copper_chest_dry',
                      'minecraft:trapped_chest_dry'}
        rows = [row for row in self.report['rows'] if row['id'] in identities]
        self.assertEqual(identities, {row['id'] for row in rows})
        for row in rows:
            captured = row['server_immediate']['actors'][0]
            original = thaw(captured['nbt'])
            self.assertTrue(chest_is_single(original), row['id'])
            value = make_cell(tuple(captured['front']), nbt=compose_actor(None, original))
            first, second = (15, 1, 15), (16, 1, 15)
            editor = Editor(Document((32, 4, 32), {first: value, second: value}))
            before = freeze(actor_data(value))
            self.assertEqual({first}, set(close_group_selection(editor.document, [first])))
            editor.material = ('minecraft:stone', 0)
            editor.paint_at((15, 1, 14), respect_selection=False)
            self.assertEqual(before, freeze(actor_data(editor.document.get(first))))
            self.assertEqual(before, freeze(actor_data(editor.document.get(second))))

    def test_paired_bed_evidence_rejects_coverage_identity_and_cleanup_changes(self):
        for key, value in (('completed', False), ('restored', False),
                           ('palette_sha256', '0' * 64), ('game_version', 'NEMC next')):
            report = dict(self.beds, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect_beds(report, self.manifest)
        for change in ('missing_case', 'missing_actor', 'wrong_color', 'wrong_bounds'):
            report = copy.deepcopy(self.beds)
            if change == 'missing_case':
                report['rows'].pop()
            elif change == 'missing_actor':
                report['rows'][0]['server']['actors'].pop()
            elif change == 'wrong_color':
                report['rows'][0]['server']['actors'][0]['color'] = 14
            else:
                report['rows'][0]['padded_low'][0] -= 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_beds(report, self.manifest)

    def test_all_paired_bed_palettes_recover_both_halves_with_bounded_native_reads(self):
        for row in self.beds['rows']:
            for side in ('server', 'client'):
                for scope in ('exact', 'padded'):
                    tree = row[side]['palettes'][scope]
                    if side == 'server':
                        tree = tree['palette']
                    native = palette(tree)
                    low, high = ((row['low'], row['high']) if scope == 'exact' else
                                 (row['padded_low'], row['padded_high']))
                    size = tuple(high[i] - low[i] + 1 for i in range(3))
                    wanted = {tuple(observed['pos'][i] - low[i] for i in range(3)):
                              tuple(observed['front']) for observed in row['observed']}
                    reads = []
                    def read(pos):
                        reads.append(pos)
                        return wanted.get(pos, ('minecraft:air', 0))
                    before = freeze(native)
                    self.assertEqual(wanted, dict(native_actor_cells(native, (0, 0, 0), size, read)),
                                     (row['case'], side, scope))
                    self.assertEqual(1, len(reads), (row['case'], side, scope))
                    self.assertIn(reads[0], wanted)
                    self.assertEqual(before, freeze(native))

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
        self.assertEqual(source.SINGLE_CELL_SHA256, snapshot_fingerprint(json.loads(raw)))
        self.assertEqual(source.PAIRED_BED_SHA256, snapshot_fingerprint(self.beds))
        self.assertEqual(source.SOURCE_SHA256, snapshot_fingerprint({
            'single_cells': self.report, 'paired_beds': self.beds}))
        changed = dict(self.report, game_version='NEMC next')
        self.assertNotEqual(source.SINGLE_CELL_SHA256, snapshot_fingerprint(changed))


if __name__ == '__main__':
    unittest.main()

"""Supported public native neighborhoods keep semantic states and fixed views."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, foreground
from projection.debug_blueprints import VISUAL_CASES, build, entries, material
from projection.debug_neighborhood_blueprints import source_document


class ExtendedConnectionBlueprintTests(unittest.TestCase):
    def test_public_entry_has_only_four_small_pending_families(self):
        metadata = VISUAL_CASES['extended_neighbors']
        self.assertIn(metadata['fixture'], {row[0] for row in entries('connections')})
        self.assertEqual(8, len(metadata['cases']))
        self.assertEqual({'scaffolding', 'pale_moss_carpet', 'redstone', 'vine_chain'},
                         {row['family'] for row in metadata['cases']})
        self.assertEqual({'editor': 'pending', 'full': 'pending', 'missing': 'pending'}, metadata['acceptance'])

    def test_every_original_state_support_and_focus_is_registry_resolved(self):
        metadata = VISUAL_CASES['extended_neighbors']
        document = build(metadata['fixture'])
        all_positions = set()
        self.assertEqual(len(metadata['cases']), len({row['id'] for row in metadata['cases']}))
        for row in metadata['cases']:
            with self.subTest(case=row['id']):
                self.assertIn(row['keep'], row['cells'])
                self.assertIn(row['occupied'], row['cells'])
                self.assertNotEqual(row['keep'], row['occupied'])
                positions = {pos for pos, name, properties in row['supports'] + row['blocks']}
                self.assertFalse(all_positions & positions)
                all_positions.update(positions)
                self.assertEqual(len(positions), len(row['supports']) + len(row['blocks']))
                for pos, name, properties in row['supports'] + row['blocks']:
                    value = foreground(document.get(pos))
                    self.assertNotEqual(AIR, value)
                    self.assertEqual(material(name, properties), value)
                    self.assertEqual(value, registry.from_states(value[0], registry.states(value)))
                self.assertIn(row['camera']['view'], ('side', 'top'))
                self.assertEqual(3, len(row['camera']['offset']))

    def test_vertical_and_thin_families_have_explicit_native_supports(self):
        for row in VISUAL_CASES['extended_neighbors']['cases']:
            supports = {pos for pos, name, properties in row['supports']}
            cells = set(row['cells'])
            if row['id'] == 'weeping_vines_chain':
                top = max(cells, key=lambda pos: pos[1])
                self.assertIn((top[0], top[1] + 1, top[2]), supports)
            else:
                for x, y, z in cells:
                    self.assertIn((x, y - 1, z), supports | cells)
            if row['family'] in ('redstone', 'pale_moss_carpet'):
                self.assertEqual('top', row['camera']['view'])

    def test_source_controls_extract_exact_cells_without_floor_or_other_cases(self):
        for row in VISUAL_CASES['extended_neighbors']['cases']:
            with self.subTest(case=row['id']):
                source = source_document(row['id'])
                isolated = source_document(row['id'], include_supports=False)
                self.assertEqual(set(row['cells']), set(isolated.blocks))
                self.assertEqual(set(row['cells']) | {pos for pos, name, properties in row['supports']},
                                 set(source.blocks))
                self.assertTrue(all(source.get(pos) == value for pos, value in isolated.blocks.items()))


if __name__ == '__main__':
    unittest.main()

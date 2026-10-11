"""Liquid fixture coverage and controls are host evidence, not visual acceptance."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import VISUAL_CASES, build, entries
from projection.debug_liquid_blueprints import METADATA, NAMES, source_document


class PureLiquidBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visual = VISUAL_CASES['pure_liquids']
        cls.document = build(cls.visual['fixture'])

    def test_public_layer_catalog_covers_all_four_native_state_tables_in_both_layers(self):
        self.assertIn(METADATA, entries('layers'))
        native = {(name, aux) for name in NAMES for aux in registry.aux_values(name)}
        self.assertEqual(64, len(native))
        self.assertEqual(native, {row['value'] for row in self.visual['states']})
        for layer in (0, 1):
            cases = [row for row in self.visual['cases'] if row['kind'] == 'state' and row['layer'] == layer]
            self.assertEqual(64, len(cases))
            self.assertEqual(native, {row['liquid_cells'][0][1] for row in cases})
            for row in cases:
                value = self.document.get(row['keep'])
                self.assertEqual(row['liquid_cells'][0][1], foreground(value) if layer == 0 else background(value))
                self.assertEqual(AIR, background(value) if layer == 0 else foreground(value))
        self.assertEqual(registry.source_version(), self.visual['registry_version'])
        self.assertEqual(registry.fingerprint(), self.visual['registry_fingerprint'])

    def test_every_public_case_is_in_bounds_and_has_its_exact_native_cells(self):
        cases = self.visual['cases']
        self.assertEqual(160, len(cases))
        self.assertEqual(len(cases), len({row['id'] for row in cases}))
        occupied = set()
        for row in cases:
            with self.subTest(case=row['id']):
                self.assertFalse(set(row['cells']) & set(row['supports']))
                footprint = set(row['cells']) | set(row['supports'])
                self.assertFalse(footprint & occupied)
                occupied.update(footprint)
                for pos, expected in row['liquid_cells']:
                    self.assertTrue(self.document.contains(pos))
                    value = self.document.get_layer(pos, row['layer'])
                    self.assertEqual(expected, value)
                    self.assertEqual(value, registry.from_states(value[0], registry.states(value)))
                for pos in row['supports']:
                    self.assertEqual('minecraft:stone', foreground(self.document.get(pos))[0])
        self.assertEqual(occupied, set(self.document.blocks))
        self.assertTrue(all(actor_data(value) is None for value in self.document.blocks.values()))

    def test_original_and_isolated_sources_preserve_both_layers_and_camera_focus(self):
        for row in self.visual['cases']:
            with self.subTest(case=row['id']):
                original = source_document(row['id'])
                isolated = source_document(row['id'], isolated=True)
                self.assertEqual(METADATA[3], original.size)
                self.assertEqual(self.visual['size'], isolated.size)
                self.assertEqual(original.get(row['keep']), isolated.get(self.visual['focus']))
                for pos, value in original.blocks.items():
                    target = tuple(pos[i] - row['keep'][i] + self.visual['focus'][i] for i in range(3))
                    self.assertTrue(isolated.contains(target))
                    self.assertEqual(value, isolated.get(target))
                self.assertEqual(len(original.blocks), len(isolated.blocks))
        self.assertEqual(3, len(self.visual['camera']['editor']))
        self.assertEqual(3, len(self.visual['camera']['world_offset']))
        self.assertGreater(self.visual['projection_height'], METADATA[3][1])

    def test_supported_negative_removes_only_liquid_and_retains_identical_supports(self):
        for row in self.visual['cases']:
            with self.subTest(case=row['id']):
                positive = source_document(row['id'], control='supported_positive')
                negative = source_document(row['id'], control='supported_negative')
                liquid_only = source_document(row['id'], control='liquid_only')
                empty = source_document(row['id'], control='empty')
                self.assertEqual(set(row['supports']), set(negative.blocks))
                self.assertEqual(set(row['cells']), set(liquid_only.blocks))
                self.assertFalse(empty.blocks)
                changed = {pos for pos in positive.blocks if positive.get(pos) != negative.get(pos)}
                self.assertEqual(set(row['cells']), changed)
                for pos in row['supports']:
                    self.assertEqual(positive.get(pos), negative.get(pos))
                    self.assertEqual(AIR, liquid_only.get(pos))
                for pos in row['cells']:
                    self.assertEqual(AIR, negative.get(pos))
                    self.assertEqual(positive.get(pos), liquid_only.get(pos))

    def test_neighbor_cases_include_source_gradient_corner_falling_and_above_in_each_layer(self):
        kinds = {'source_pair', 'flow_gradient', 'flow_corner', 'falling_column',
                 'liquid_above', 'solid_side', 'source_pool', 'falling_to_flow'}
        for family in ('water', 'lava'):
            for layer in (0, 1):
                rows = [row for row in self.visual['cases'] if row['kind'] != 'state'
                        and row['id'].startswith(family + '_') and row['layer'] == layer]
                self.assertEqual(kinds, {row['kind'] for row in rows})
                for row in rows:
                    depths = [registry.states(value)['liquid_depth'] for unused, value in row['liquid_cells']]
                    offsets = {tuple(pos[i] - row['keep'][i] for i in range(3)) for pos in row['cells']}
                    if row['kind'] == 'flow_gradient':
                        self.assertEqual([0, 1, 3, 7], depths)
                        self.assertEqual({(x, 0, 0) for x in range(4)}, offsets)
                    elif row['kind'] == 'flow_corner':
                        self.assertIn((-1, 0, -1), offsets)
                        self.assertEqual({0, 1, 3, 7}, set(depths))
                    elif row['kind'] == 'falling_column':
                        self.assertEqual([8, 8, 8], depths)
                        self.assertEqual({(0, y, 0) for y in range(3)}, offsets)
                    elif row['kind'] == 'liquid_above':
                        self.assertEqual({(0, 0, 0), (0, 1, 0)}, offsets)
                    elif row['kind'] == 'source_pool':
                        self.assertEqual([0] * 4, depths)
                        self.assertEqual({(x, 0, z) for x in range(2) for z in range(2)}, offsets)

    def test_mask_contract_requires_liquid_only_and_native_positive_signals(self):
        mask = self.visual['mask']
        self.assertEqual(('liquid_only', 'empty'), (mask['positive_control'], mask['negative_control']))
        self.assertEqual(('supported_positive', 'supported_negative'), mask['supported_pair'])
        self.assertEqual('supports', mask['excluded_cells'])
        self.assertTrue(mask['require_native_liquid_pixels'])
        self.assertTrue(mask['require_liquid_only_pixels'])
        self.assertTrue(mask['require_supported_difference_pixels'])
        self.assertFalse(mask['support_pixels_can_satisfy_gate'])
        self.assertEqual(1., mask['fixed_cell_hull_height'])
        self.assertEqual({'editor': 'pending', 'projection_full': 'pending',
                          'projection_missing': 'pending'}, self.visual['acceptance'])
        self.assertEqual('pending_four_corner_heights_and_neighbor_faces',
                         self.visual['native_shape_acceptance'])

    def test_unknown_case_or_control_is_rejected(self):
        with self.assertRaises(ValueError):
            source_document('unknown')
        with self.assertRaises(ValueError):
            source_document(self.visual['cases'][0]['id'], control='unknown')


if __name__ == '__main__':
    unittest.main()

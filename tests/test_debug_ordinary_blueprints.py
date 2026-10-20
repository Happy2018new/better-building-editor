"""The review inventory covers native states without implying visual acceptance."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import debug_ordinary_blueprints as ordinary
from projection.block_groups import group_partner
from projection.cell import AIR, foreground, background
from projection.debug_blueprints import build, entries
from projection.entity_defaults_data import DEFAULTS


class OrdinaryReviewBlueprintTests(unittest.TestCase):
    def test_complete_ordinary_inventory_and_every_legal_state(self):
        expected_names = {name for name in registry.BLOCKS if ordinary.exclusion(name) is None}
        defaults = {row['material'] for identity, cases in ordinary.CASES.items()
                    if '.catalogue.' in identity for row in cases}
        self.assertEqual({(name, registry.DEFAULT_AUX[name]) for name in expected_names}, defaults)
        expected_states = {(name, aux) for name in expected_names for aux in registry.aux_values(name)}
        actual_states = {row['material'] for cases in ordinary.CASES.values() for row in cases}
        self.assertEqual(expected_states, actual_states)
        self.assertEqual(36, len(ordinary.DYNAMIC_NAMES))
        self.assertEqual({(name, aux) for name in ordinary.DYNAMIC_NAMES for aux in registry.aux_values(name)},
                         {row['material'] for identity, cases in ordinary.CASES.items()
                          if '.dynamic.' in identity for row in cases})

    def test_scope_exclusions_are_explicit_and_not_visual_passes(self):
        placeholder = 'minecraft:client_request_placeholder_block'
        self.assertEqual('internal_or_invisible', ordinary.exclusion(placeholder))
        self.assertNotIn(placeholder, ordinary.NAMES)
        # Barrier visibility is an explicit product requirement; keep its case.
        self.assertIn('minecraft:barrier', ordinary.NAMES)
        for name in DEFAULTS:
            self.assertEqual('block_entity', ordinary.exclusion(name))
        for short in ('element_0', 'chemical_heat', 'colored_torch_blue',
                      'hard_glass', 'white_hard_stained_glass', 'underwater_tnt'):
            self.assertEqual('education', ordinary.exclusion('minecraft:' + short))
        for cases in ordinary.CASES.values():
            for case in cases:
                self.assertEqual('pending_manual_review', case['status'])

    def test_bounded_galleries_preserve_exact_states_and_reciprocal_parts(self):
        public = {row[0] for row in entries('manual')}
        for identity, cases in ordinary.CASES.items():
            with self.subTest(identity=identity):
                self.assertIn(identity, public)
                self.assertLessEqual(len(cases), ordinary.PAGE_CAPACITY)
                document = build(identity)
                self.assertEqual(ordinary.PAGE_SIZE, document.size)
                self.assertEqual(len(cases), len({case['anchor'] for case in cases}))
                for case in cases:
                    value, anchor = case['material'], case['anchor']
                    self.assertEqual(value, foreground(document.get(anchor)))
                    relationship = group_partner(value)
                    if relationship:
                        offset, expected = relationship
                        partner = tuple(anchor[i] + offset[i] for i in range(3))
                        self.assertEqual(expected, foreground(document.get(partner)))
                self.assertTrue(all(document.contains(pos) for pos in document.blocks))
                for cell in document.blocks.values():
                    for value in (foreground(cell), background(cell)):
                        self.assertEqual(value, registry.canonical(value))

    def test_context_entries_reuse_the_original_scenes(self):
        contexts = [row for row in entries('manual') if '.context.' in row[0]]
        self.assertEqual(8, len(contexts))
        for metadata in contexts:
            identity = metadata[0]
            original = build(identity[len('test.ordinary.context.'):])
            review = build(identity)
            self.assertEqual(original.blocks, review.blocks)
            self.assertEqual(metadata[2], review.name)
            self.assertIsNot(original.blocks, review.blocks)


if __name__ == '__main__':
    unittest.main()

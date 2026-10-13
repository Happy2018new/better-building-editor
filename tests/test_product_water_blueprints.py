"""Public source fidelity and independent water/body/rear controls."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import AIR, background, foreground
from projection.debug_blueprints import BLUEPRINTS, VISUAL_CASES, build
from projection.debug_product_water_blueprints import CASES, FOCUS, METADATA, source_document


class ProductWaterBlueprintTests(unittest.TestCase):
    def test_public_gallery_matches_all_isolated_wet_sources(self):
        self.assertIn(METADATA, BLUEPRINTS)
        self.assertEqual(METADATA[0], VISUAL_CASES['water_style']['fixture'])
        gallery = build(METADATA[0])
        self.assertEqual(14, len(CASES))
        for row in CASES:
            source = source_document(row['id'])
            for pos, value in source.blocks.items():
                public = tuple(pos[i] - FOCUS[i] + row['anchor'][i] for i in range(3))
                self.assertEqual(gallery.get(public), value)

    def test_fence_controls_isolate_water_body_and_rear_below_the_waterline(self):
        sources = {name: source_document('wet_oak_fence', name)
                   for name in ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty')}
        rear = (FOCUS[0], FOCUS[1], FOCUS[2] - 2)
        support = (FOCUS[0], FOCUS[1] - 1, FOCUS[2])
        self.assertEqual('minecraft:oak_fence', foreground(sources['wet'].get(FOCUS))[0])
        self.assertEqual('minecraft:water', background(sources['wet'].get(FOCUS))[0])
        self.assertEqual('minecraft:oak_fence', foreground(sources['dry'].get(FOCUS))[0])
        self.assertEqual(AIR, background(sources['dry'].get(FOCUS)))
        self.assertEqual(AIR, foreground(sources['liquid_only'].get(FOCUS)))
        self.assertEqual(background(sources['wet'].get(FOCUS)), background(sources['liquid_only'].get(FOCUS)))
        self.assertEqual(sources['wet'].get(FOCUS), sources['rearless'].get(FOCUS))
        self.assertEqual(AIR, sources['rearless'].get(rear))
        self.assertEqual(AIR, sources['empty'].get(FOCUS))
        for name, source in sources.items():
            self.assertEqual('minecraft:stone', foreground(source.get(support))[0], name)
            if name not in ('rearless', 'water_only', 'empty'):
                self.assertEqual('minecraft:gold_block', foreground(source.get(rear))[0], name)

    def test_drop_below_neighbor_and_four_direction_gradients_are_exact_snapshots(self):
        drop = source_document('drop_north')
        self.assertEqual('minecraft:water', foreground(drop.get((3, 2, 2)))[0])
        self.assertEqual(AIR, drop.get((3, 3, 2)))
        for identity in ('flow_east', 'flow_south', 'flow_west', 'flow_north'):
            source = source_document(identity)
            water = [value for unused, value in source.blocks.items() if foreground(value)[0] == 'minecraft:water']
            self.assertEqual(3, len(water), identity)

    def test_invalid_cases_and_controls_do_not_silently_select_a_fixture(self):
        for identity, control in (('missing', 'wet'), ('source', 'missing')):
            with self.assertRaises(ValueError):
                source_document(identity, control)


if __name__ == '__main__':
    unittest.main()

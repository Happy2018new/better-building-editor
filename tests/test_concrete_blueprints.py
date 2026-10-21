"""Public OB-10 comparison keeps legal dry cells and separate wire controls."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import build, entries
from projection.debug_concrete_blueprints import METADATA, PATCHES
from projection.model import Document


class ConcreteBlueprintTests(unittest.TestCase):
    def test_public_gallery_has_six_separate_legal_comparisons(self):
        self.assertIn(METADATA, entries('registry'))
        document = build(METADATA[0])
        self.assertEqual((18, 4, 18), document.size)
        self.assertEqual(66, len(document.blocks))
        for row in PATCHES:
            x, y, z = row['center']
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    self.assertEqual((row['material'], 0), foreground(document.get((x + dx, y, z + dz))))
            top = document.get((x, y + 1, z))
            if row['kind'] == 'reference':
                self.assertEqual(AIR, top)
            else:
                self.assertEqual(('minecraft:lever', 5), foreground(top))
                self.assertEqual('up_north_south', registry.states(foreground(top))['lever_direction'])
        for pos, value in document.blocks.items():
            self.assertTrue(all(0 < pos[axis] < document.size[axis] - 1 for axis in range(3)))
            self.assertEqual(AIR, background(value))
            self.assertIsNone(actor_data(value))
        self.assertEqual(8, sum(foreground(value)[0] == 'minecraft:redstone_wire'
                                for value in document.blocks.values()))
        restored = Document.from_data(document.to_data())
        self.assertEqual(document.blocks, restored.blocks)


if __name__ == '__main__':
    unittest.main()

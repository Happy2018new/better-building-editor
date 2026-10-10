"""A native neighbour shape must not be truncated at a 16-cube boundary."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.model import Document
from projection.preview_regions import regions


STONE = ('minecraft:stone', 0)
STAIRS = ('minecraft:oak_stairs', 0)
GLASS = ('minecraft:glass', 0)


class PreviewRegionTests(unittest.TestCase):
    def test_ordinary_solid_volume_keeps_all_128_incremental_regions(self):
        document = Document((64, 128, 64))
        for x in range(4):
            for y in range(8):
                for z in range(4):
                    document.blocks.fill_chunk((x, y, z), STONE)
        output = regions(document)
        self.assertEqual(128, len(set(entry[0] for entry in output.values())))
        self.assertTrue(all(len(entry[3]) == 1 for entry in output.values()))

    def test_only_real_cross_boundary_neighbours_join(self):
        document = Document((48, 3, 16), {
            (15, 0, 0): STAIRS, (16, 1, 0): STAIRS,
            (31, 0, 0): STAIRS, (32, 0, 0): STONE,
        })
        output = regions(document)
        self.assertEqual((0, 0, 0), output[(0, 0, 0)][0])
        self.assertEqual((1, 0, 0), output[(2, 0, 0)][0])
        self.assertEqual(((1, 0, 0), (16, 0, 0), (48, 3, 16),
                          ((1, 0, 0), (2, 0, 0))), output[(1, 0, 0)])

    def test_unknown_and_background_only_blocks_keep_native_neighbour_context(self):
        for value in (('custom:new_shape', 0), GLASS,
                      make_cell(AIR, ('minecraft:water', 0))):
            with self.subTest(value=value):
                document = Document((32, 1, 1), {(15, 0, 0): value, (16, 0, 0): STONE})
                output = regions(document)
                self.assertEqual(output[(0, 0, 0)], output[(1, 0, 0)])
                self.assertEqual((32, 1, 1), output[(0, 0, 0)][2])

    def test_rectangle_closure_owns_all_tiles_inside_l_shaped_bounds_once(self):
        document = Document((32, 1, 32), {
            (15, 0, 0): GLASS, (16, 0, 0): GLASS,
            (16, 0, 15): STAIRS, (16, 0, 16): STAIRS,
            (0, 0, 31): STONE,
        })
        output = regions(document)
        self.assertEqual(1, len(set(output.values())))
        self.assertEqual(((0, 0, 0), (0, 0, 0), (32, 1, 32),
                          ((0, 0, 0), (0, 0, 1), (1, 0, 0), (1, 0, 1))),
                         output[(0, 0, 0)])

    def test_random_rectangles_partition_the_entire_document_without_overlap(self):
        rng = random.Random(137)
        document = Document((64, 17, 64))
        for unused in range(1000):
            pos = (rng.randrange(64), rng.randrange(17), rng.randrange(64))
            document.blocks[pos] = GLASS if rng.randrange(2) else STONE
        output = regions(document)
        owners = set()
        for root, low, high, members in set(output.values()):
            rectangular = {(x, y, z)
                           for x in range(low[0] // 16, (high[0] - 1) // 16 + 1)
                           for y in range(low[1] // 16, (high[1] - 1) // 16 + 1)
                           for z in range(low[2] // 16, (high[2] - 1) // 16 + 1)}
            self.assertEqual(rectangular, set(members))
            self.assertFalse(owners.intersection(members))
            owners.update(members)
            self.assertEqual(min(members), root)
        self.assertEqual(set(output), owners)


if __name__ == '__main__':
    unittest.main()

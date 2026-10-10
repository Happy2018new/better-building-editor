import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import AIR, make_cell
from projection.large_preview import SurfacePalette

GLASS = ('minecraft:glass', 0)
WATER = ('minecraft:water', 0)


class SurfacePaletteBudgetTests(unittest.TestCase):
    def test_full_supported_volume_can_hold_two_native_layers(self):
        palette = SurfacePalette((64, 128, 64))
        volume = 64 * 128 * 64
        palette.add_indices(make_cell(GLASS, WATER), range(volume))
        self.assertEqual(volume, palette.count)
        self.assertEqual(2 * volume, palette.layer_count)
        self.assertEqual(volume, len(palette.common[GLASS]))
        self.assertEqual(volume, len(palette.extra[WATER]))

    def test_budget_counts_cells_and_rejects_excess_before_mutating_palette(self):
        palette = SurfacePalette((3, 1, 1))
        with patch('projection.large_preview.MAX_SURFACE_BLOCKS', 2):
            palette.add_indices(make_cell(GLASS, WATER), (0, 1))
            with self.assertRaises(ValueError):
                palette.add((2, 0, 0), make_cell(GLASS, WATER))
        self.assertEqual(2, palette.count)
        self.assertEqual(4, palette.layer_count)
        self.assertEqual({GLASS: [0, 1]}, palette.common)
        self.assertEqual({WATER: [0, 1]}, palette.extra)

    def test_foreground_background_and_empty_cells_have_separate_native_entry_counts(self):
        palette = SurfacePalette((4, 1, 1))
        palette.add((0, 0, 0), GLASS)
        palette.add((1, 0, 0), make_cell(AIR, WATER))
        palette.add((2, 0, 0), make_cell(GLASS, WATER))
        palette.add((3, 0, 0), AIR)
        self.assertEqual(3, palette.count)
        self.assertEqual(4, palette.layer_count)


if __name__ == '__main__':
    unittest.main()

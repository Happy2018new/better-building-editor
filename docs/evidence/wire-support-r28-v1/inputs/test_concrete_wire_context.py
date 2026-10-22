"""Native-context ownership contracts for dry wires on concrete supports."""
import copy
import unittest

from test_concrete_floor_context import _entries, _tile, WaterOwner, WATER, STONE
from projection.block_registry import canonical
from projection.cell import make_cell
from projection.model import Document

WIRE = 'minecraft:redstone_wire'


class ConcreteWireContextTests(unittest.TestCase):
    def test_each_signal_and_concrete_color_keeps_own_geometry(self):
        # Cross every signal and color; exercise aliases and named materials.
        for signal in range(16):
            for color in range(16):
                legacy = ('minecraft:concrete', color)
                concrete = canonical(legacy)
                for support in (legacy, concrete):
                    with self.subTest(signal=signal, support=support):
                        target, below = (1, 1, 1), (1, 0, 1)
                        wire = (WIRE, signal)
                        doc = Document((3, 3, 3), {target: wire, below: support})
                        saved = copy.deepcopy(doc.to_data())
                        for result in _entries(doc):
                            self.assertNotIn(('common', concrete, (0, -1, 0)), _tile(result, target))
                            self.assertIn(('common', wire, (0, 0, 0)), _tile(result, target))
                            self.assertIn(('common', concrete, (0, 0, 0)), _tile(result, below))
                        self.assertEqual(saved, doc.to_data())

    def test_cross_chunk_slopes_keep_side_support_and_neighbor_wires(self):
        concrete = canonical(('minecraft:concrete', 0))
        for direction in (-1, 1):
            for delta_y in (-1, 1):
                target, below = (15, 16, 15), (15, 15, 15)
                other = (15 + direction, 16 + delta_y, 15)
                cells = {target: (WIRE, 15), below: concrete,
                         other: (WIRE, 15), (other[0], other[1]-1, other[2]): concrete}
                if delta_y > 0:
                    cells[(other[0], 16, other[2])] = concrete
                doc = Document((32, 32, 32), cells)
                saved = copy.deepcopy(doc.to_data())
                for result in _entries(doc):
                    rows = _tile(result, target)
                    self.assertNotIn(('common', concrete, (0, -1, 0)), rows)
                    self.assertIn(('common', (WIRE, 15), (direction, delta_y, 0)), rows)
                    if delta_y > 0:
                        self.assertIn(('common', concrete, (direction, 0, 0)), rows)
                self.assertEqual(saved, doc.to_data())

    def test_wet_reversed_and_two_solid_cells_keep_support(self):
        concrete = canonical(('minecraft:concrete', 0))
        wire = (WIRE, 15)
        cases = ((make_cell(wire, WATER), concrete),
                 (wire, make_cell(concrete, WATER)),
                 (make_cell(WATER, wire), concrete),
                 (wire, make_cell(WATER, concrete)),
                 (make_cell(wire, STONE), concrete),
                 (wire, make_cell(concrete, STONE)))
        for profile in (None, WaterOwner()):
            for front, support in cases:
                with self.subTest(profile=profile is not None, front=front, support=support):
                    doc = Document((3, 3, 3), {(1, 1, 1): front, (1, 0, 1): support})
                    before = copy.deepcopy(doc.to_data())
                    for result in _entries(doc, profile):
                        self.assertTrue(any(row[1] == concrete and row[2] == (0, -1, 0)
                                            for row in _tile(result, (1, 1, 1))))
                    self.assertEqual(before, doc.to_data())

    def test_stone_support_is_retained(self):
        doc = Document((3, 3, 3), {(1, 1, 1): (WIRE, 15), (1, 0, 1): STONE})
        for result in _entries(doc):
            self.assertIn(('common', STONE, (0, -1, 0)), _tile(result, (1, 1, 1)))


if __name__ == '__main__':
    unittest.main()

"""Door context belongs to door targets without leaking into adjacent targets."""
import copy
import unittest

import test_render_context
from projection import render_context, block_registry
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.large_preview import SurfacePalette
from projection.model import Document
from projection.render_layout import context_position, local_context_position


def index(pos, volume):
    return (pos[1] * volume[1] + pos[0]) * volume[0] + pos[2]


class DoorContextOwnershipTests(unittest.TestCase):
    def fixture(self, direction=0, hinge=False, opened=False):
        lower, upper, base = (15, 15, 15), (15, 16, 15), (15, 14, 15)
        door = material('wooden_door', {'minecraft:cardinal_direction': ('east','south','west','north')[direction], 'door_hinge_bit': hinge,
                                       'open_bit': opened, 'upper_block_bit': False})
        partner = material('wooden_door', {'minecraft:cardinal_direction': ('east','south','west','north')[direction], 'door_hinge_bit': hinge,
                                          'open_bit': opened, 'upper_block_bit': True})
        water = material('water')
        doc = Document((32, 32, 32), {lower: door, upper: partner,
                                    base: material('stone')})
        return doc, lower, upper, base, door, partner, water

    def palette(self, document, positions):
        result = SurfacePalette(document.size)
        for pos in positions:
            result.add(pos, document.get(pos))
        return result.palette_data()

    def test_both_door_parts_keep_partner_context_while_other_targets_drop_door_bodies(self):
        for direction in range(4):
            for hinge in (False, True):
                for opened in (False, True):
                    doc, lower, upper, base, door, partner, water = self.fixture(direction, hinge, opened)
                    before = copy.deepcopy(doc.to_data())
                    for points in ((base,), (lower,), (upper,), (base, lower, upper), (base, upper)):
                        with self.subTest(direction=direction, hinge=hinge, opened=opened, points=points):
                            targets = self.palette(doc, points)
                            data = render_context.prepare_context_batches(doc, targets)
                            batches = {origin:palette for origin, packed, palette in data['_context_batches'] if packed}
                            for target in points:
                                origin = tuple(axis & ~15 for axis in target)
                                palette = batches[origin]
                                for source, value in ((lower, door), (upper, partner)):
                                    delta = tuple(source[i] - target[i] for i in range(3))
                                    if any(abs(axis) > 1 for axis in delta):
                                        continue
                                    encoded = local_context_position(target, delta)
                                    present = index(encoded, palette['volume']) in palette['common'].get(value, ())
                                    self.assertEqual(target != base, present)
                            reference = render_context.prepare_context_palette(doc.palette_data(), targets)
                            incremental = render_context.ContextPaletteBuilder(doc, targets)
                            for unused in incremental.prepare():
                                pass
                            self.assertEqual(reference, incremental.data)
                            for target in points:
                                for source, value in ((lower, door), (upper, partner)):
                                    delta = tuple(source[i] - target[i] for i in range(3))
                                    if any(abs(axis) > 1 for axis in delta):
                                        continue
                                    encoded = index(context_position(target, delta), reference['volume'])
                                    self.assertEqual(target != base, encoded in reference['common'].get(value, ()))
                    self.assertEqual(before, doc.to_data())

    def test_cached_write_for_same_door_has_distinct_ownership_plans_in_both_orders(self):
        door, stone, water = material('wooden_door'), material('stone'), material('water')
        actor = ('minecraft:wooden_door', {'x': 3, 'opaque': {'bytes': b'\xff'}})
        rendered = ({'common':door, 'extra':water, 'actor':actor}, None, {}, {})
        before = copy.deepcopy(rendered)
        for targets in ((stone, door), (door, stone)):
            palette = {'common':{}, 'extra':{}, 'actor':{}}
            writer = render_context._ContextWriter(palette)
            for number, target in enumerate(targets, 1):
                writer.put(rendered, number, (0, 0, 0), {'common':target})
            allowed = targets.index(door) + 1
            self.assertEqual([allowed], palette['common'][door])
            self.assertEqual([1, 2], palette['extra'][water])
            self.assertEqual({allowed}, set(palette['actor'][door[0]]))
            self.assertEqual(2, len(writer.cache))
        # Existing callers that omit a target retain their full-context contract.
        palette = {'common':{}, 'extra':{}, 'actor':{}}
        render_context._ContextWriter(palette).put(rendered, 7, (0, 0, 0))
        self.assertEqual([7], palette['common'][door])
        self.assertEqual(before, rendered)

    def test_rule_preserves_bed_double_plant_custom_door_and_trapdoor_neighbors(self):
        stone = {'common':material('stone')}
        for name in ('bed', 'sunflower', 'rose_bush', 'tall_grass', 'trapdoor'):
            value = material(name)
            cell = {'common':value}
            self.assertIs(cell, render_context._context_cell(cell, stone), name)
        custom = {'common':('example:custom_door', 0)}
        self.assertIs(custom, render_context._context_cell(custom, stone))
        for name in block_registry.BLOCKS:
            if name.startswith('minecraft:') and name.endswith('_door'):
                value = (name, block_registry.aux_values(name)[0])
                cell = {'common':value}
                self.assertEqual({}, render_context._context_cell(cell, stone), name)
                self.assertIs(cell, render_context._context_cell(cell, cell), name)
        # A secondary-only target owns its water, without borrowing a door body.
        self.assertEqual({}, render_context._context_cell({'common':material('wooden_door')},
                                                       {'extra':material('water')}))


if __name__ == '__main__':
    unittest.main()

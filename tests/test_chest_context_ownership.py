"""Hidden chest bodies must not leave boundary faces in unrelated target tiles."""
import copy
import unittest

import test_render_context
from projection import render_context
from projection.cell import actor_data, foreground
from projection.debug_blueprints import build, material
from projection.debug_transform_acceptance import PREFIX, prepare
from projection.entity_render import CHEST_PROXIES, chest_proxy, document_chest_part
from projection.model import Editor
from projection.render_layout import context_position, local_context_position


CHEST_BODIES = frozenset((name, 0) for family in CHEST_PROXIES.values()
                         for name in family.values())


def index(pos, volume):
    return (pos[1] * volume[1] + pos[0]) * volume[0] + pos[2]


def sorted_palette(palette):
    result = copy.deepcopy(palette)
    for layer in ('common', 'extra'):
        result[layer] = {value: sorted(entries) for value, entries in result[layer].items()}
    return result


class ChestContextOwnershipTests(unittest.TestCase):
    def test_t04_mirrored_missing_four_stages_keep_pair_context_and_support_ownership(self):
        editor = Editor(build(PREFIX + 't04'))
        self.assertTrue(prepare(editor, PREFIX + 't04'))
        editor.run('mirror_x')
        document = editor.document
        saved = copy.deepcopy(document.to_data())
        self.assertEqual(34, len(document.blocks))
        points = ((17, 2, 4), (16, 2, 4))
        expected_bodies = {}
        for pos, value in document.blocks.items():
            front = foreground(value)
            if front[0] in CHEST_PROXIES:
                expected_bodies[pos] = chest_proxy(front, actor_data(value),
                    document_chest_part(document, pos, front))
        self.assertEqual({(17, 2, 4), (16, 2, 4), (17, 2, 7), (16, 2, 7)},
                         set(expected_bodies))
        for label, occupied in (('empty', ()), ('single_half', points[:1]),
                                ('occupied', points), ('restored', ())):
            with self.subTest(stage=label):
                targets = document.palette_data(lambda pos: pos not in occupied)
                packed = {origin: palette for origin, context, palette in
                          render_context.prepare_context_batches(document, targets)['_context_batches']
                          if context}
                # Each output 4-cube belongs to its target; no borrowed chest
                # body may be emitted into a support or other non-chest tile.
                for origin, palette in packed.items():
                    for value, entries in palette['common'].items():
                        if value not in CHEST_BODIES:
                            continue
                        for encoded in entries:
                            coord = (encoded // 64 % 64, encoded // 4096, encoded % 64)
                            owner = tuple(origin[axis] + coord[axis] // 4 for axis in range(3))
                            self.assertIn(owner, expected_bodies, (label, owner, value))
                            self.assertNotIn(owner, occupied)
                reference = render_context.prepare_context_palette(document.palette_data(), targets)
                incremental = render_context.ContextPaletteBuilder(document, targets)
                for unused in incremental.prepare():
                    pass
                self.assertEqual(sorted_palette(reference), sorted_palette(incremental.data))
                retained = 0
                for target in expected_bodies:
                    if target in occupied:
                        continue
                    palette = packed[tuple(axis & ~15 for axis in target)]
                    for source, body in expected_bodies.items():
                        delta = tuple(source[axis] - target[axis] for axis in range(3))
                        if any(abs(axis) > 1 for axis in delta):
                            continue
                        local = index(local_context_position(target, delta), palette['volume'])
                        self.assertIn(local, palette['common'][body], (label, target, source))
                        global_index = index(context_position(target, delta), reference['volume'])
                        self.assertIn(global_index, reference['common'][body], (label, target, source))
                        retained += 1
                self.assertEqual(2 * (4 - len(occupied)), retained)
                # The red platform is a real target in every stage, so it
                # retains its own material at its center while chest copies
                # from directly above are absent in both packing routes.
                for target in ((17, 1, 4), (16, 1, 4)):
                    support = foreground(document.get(target))
                    self.assertEqual(material('red_concrete'), support)
                    palette = packed[tuple(axis & ~15 for axis in target)]
                    self.assertIn(index(local_context_position(target, (0, 0, 0)), palette['volume']),
                                  palette['common'][support])
                    for source, body in expected_bodies.items():
                        delta = tuple(source[axis] - target[axis] for axis in range(3))
                        if all(abs(axis) <= 1 for axis in delta):
                            self.assertNotIn(index(local_context_position(target, delta), palette['volume']),
                                             palette['common'].get(body, ()))
                            self.assertNotIn(index(context_position(target, delta), reference['volume']),
                                             reference['common'].get(body, ()))
                self.assertEqual(saved, document.to_data())

    def test_all_registered_chest_bodies_strip_actor_but_keep_extra_for_unrelated_targets(self):
        water = material('water')
        for chest in sorted(CHEST_BODIES):
            with self.subTest(chest=chest):
                cell = {'common': chest, 'extra': water,
                        'actor': (chest[0], {'opaque': {'bytes': b'\xff', 'items': [1, 2]}})}
                saved = copy.deepcopy(cell)
                for target in ({'common': material('stone')}, {'extra': water}):
                    self.assertEqual({'extra': water}, render_context._context_cell(cell, target))
                self.assertEqual({}, render_context._context_cell({'common': chest},
                                                                  {'common': material('stone')}))
                self.assertIs(cell, render_context._context_cell(cell))
                self.assertIs(cell, render_context._context_cell(cell, {'common': chest}))
                self.assertEqual(saved, cell)

    def test_cached_chest_write_uses_distinct_ownership_plans_in_both_orders(self):
        stone, water = material('stone'), material('water')
        for chest in sorted(CHEST_BODIES):
            actor = (chest[0], {'x': 3, 'opaque': {'bytes': b'\xff', 'items': [1, 2]}})
            rendered = ({'common': chest, 'extra': water, 'actor': actor}, None, {}, {})
            saved = copy.deepcopy(rendered)
            for targets in ((stone, chest), (chest, stone)):
                with self.subTest(chest=chest, targets=targets):
                    palette = {'common': {}, 'extra': {}, 'actor': {}}
                    writer = render_context._ContextWriter(palette)
                    for number, target in enumerate(targets, 1):
                        writer.put(rendered, number, (0, 0, 0), {'common': target})
                    allowed = targets.index(chest) + 1
                    self.assertEqual([allowed], palette['common'][chest])
                    self.assertEqual([1, 2], palette['extra'][water])
                    self.assertEqual({allowed}, set(palette['actor'][chest[0]]))
                    self.assertEqual(2, len(writer.cache))
                    palette['actor'][chest[0]][allowed]['opaque']['items'][0] = 99
                    self.assertEqual(saved, rendered)
            palette = {'common': {}, 'extra': {}, 'actor': {}}
            render_context._ContextWriter(palette).put(rendered, 7, (0, 0, 0))
            self.assertEqual([7], palette['common'][chest])
            self.assertEqual({7}, set(palette['actor'][chest[0]]))

    def test_rule_preserves_unrelated_native_and_custom_actor_families(self):
        stone, water = material('stone'), material('water')
        for value in (material('barrel'), material('bed'), material('trapdoor'),
                      ('example:custom_door', 0), ('example:custom_chest', 0),
                      ('modern_projection:preview_chest_unregistered', 0)):
            with self.subTest(material=value):
                cell = {'common': value, 'extra': water,
                        'actor': (value[0], {'opaque': {'bytes': b'\xff', 'items': [1, 2]}})}
                self.assertIs(cell, render_context._context_cell(cell, {'common': stone}))
                palette = {'common': {}, 'extra': {}, 'actor': {}}
                render_context._ContextWriter(palette).put((cell, None, {}, {}), 3, (0, 0, 0),
                                                         {'common': stone})
                self.assertEqual([3], palette['common'][value])
                self.assertEqual([3], palette['extra'][water])
                self.assertEqual({3}, set(palette['actor'][value[0]]))


if __name__ == '__main__':
    unittest.main()

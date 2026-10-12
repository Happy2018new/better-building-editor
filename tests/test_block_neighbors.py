"""Connection edits are local, undoable and independent of document size."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_groups import (chest_pair_actor, paired_cell_position,
                                     chest_render_pair_position, hydrate_chest_actor,
                                     actor_pair_position)
from projection.block_neighbors import _solid_face, _stair_mask
from projection.entity_render import _chest_part
from projection.cell import actor_data, background, foreground, make_cell
from projection.jobs import EditJob
from projection.model import AIR, Document, Editor, close_group_selection
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import chest_is_single, compose_actor, entity_nbt, render_actor

SIZES = ((8, 5, 8), (64, 128, 64))
STONE = ('minecraft:stone', 0)
WATER = ('minecraft:water', 0)
WALL = ('minecraft:cobblestone_wall', 0)
RAIL = ('minecraft:rail', 0)
CHEST = registry.from_states('minecraft:chest', {'minecraft:cardinal_direction': 'north'})


def states(editor, pos):
    return registry.states(foreground(editor.document.get(pos)))


def place(editor, pos, value):
    editor.material = value
    return editor.paint_at(pos, respect_selection=False)


class BlockNeighborTests(unittest.TestCase):
    def test_single_chest_recognition_rejects_unknown_and_partial_actor_records(self):
        nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
               'Items': {'__type__': 9, '__value__': []}}
        self.assertTrue(chest_is_single(nbt))
        for actor in (None, {}, {'id': 'Chest'},
                      {'Items': {'__type__': 9, '__value__': []}},
                      dict(nbt, pairx={'__type__': 3, '__value__': 3}),
                      dict(nbt, pairz={'__type__': 3, '__value__': 2}),
                      compose_actor({'chestIsLargeChest': True}, nbt),
                      compose_actor({'chestIsLargeChest': 0}, nbt),
                      {'__modern_projection_actor__': 2, 'render': None, 'nbt': nbt}):
            with self.subTest(actor=actor):
                self.assertFalse(chest_is_single(actor))
        self.assertIsNone(_chest_part(compose_actor({'chestIsLargeChest': 0}, nbt)))
        self.assertIsNone(_chest_part({'chestIsLargeChest': True, 'chestMainSubChest': 1}))

    def test_explicit_single_renderer_overrides_stale_pair_nbt_without_rewriting_it(self):
        left, right = (15, 1, 15), (16, 1, 15)
        nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
               'pairx': {'__type__': 3, '__value__': right[0]},
               'pairz': {'__type__': 3, '__value__': right[2]}}
        single = make_cell(CHEST, WATER, compose_actor({'chestIsLargeChest': False}, nbt))
        editor = Editor(Document((32, 4, 32), {left: single, right: CHEST}))
        self.assertIsNone(actor_pair_position(single, left))
        self.assertEqual({left}, set(close_group_selection(editor.document, [left])))
        editor.material = STONE
        editor.paint_at((15, 1, 14), respect_selection=False)
        self.assertEqual(single, editor.document.get(left))
        self.assertEqual(nbt, entity_nbt(actor_data(editor.document.get(left))))

    def test_passive_neighbor_edits_keep_explicit_single_chests_and_their_nbt(self):
        left, right = (15, 1, 15), (16, 1, 15)
        nbt = {'Items': [{'Slot': 0, 'Count': 5}], 'CustomName': 'kept'}
        single = make_cell(CHEST, WATER, compose_actor({'chestIsLargeChest': False}, nbt))
        for operation in ('paint', 'erase', 'job'):
            with self.subTest(operation=operation):
                edit_pos = (15, 1, 14)
                original = {left: single, right: single}
                if operation == 'erase':
                    original[edit_pos] = STONE
                editor = Editor(Document((32, 4, 32), original))
                if operation == 'job':
                    editor.select_box(edit_pos, edit_pos)
                    editor.material = STONE
                    job = EditJob(editor, 'fill')
                    while not job.done:
                        job.step(budget=65536, seconds=1)
                    self.assertFalse(job.error)
                else:
                    editor.material = STONE
                    editor.paint_at(edit_pos, erase=operation == 'erase', respect_selection=False)
                for pos in (left, right):
                    self.assertEqual(single, editor.document.get(pos))
                    self.assertEqual({pos}, set(close_group_selection(editor.document, [pos])))
                self.assertEqual(1, len(editor.undo_stack))
                after = dict(editor.document.blocks.items())
                self.assertTrue(editor.undo())
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertTrue(editor.redo())
                self.assertEqual(after, dict(editor.document.blocks.items()))

    def test_whole_cell_paste_keeps_supplied_single_chests_beside_each_other(self):
        left, right = (15, 1, 15), (16, 1, 15)
        single = make_cell(CHEST, WATER, compose_actor({'chestIsLargeChest': False},
                                                       {'Items': [{'Slot': 0, 'Count': 5}]}))
        editor = Editor(Document((32, 4, 32)))
        editor.clipboard = {'size': (2, 1, 1), 'origin': (0, 0, 0),
                            'blocks': {(0, 0, 0): single, (1, 0, 0): single}}
        editor.start = left
        editor.run('paste')
        self.assertEqual({left: single, right: single}, dict(editor.document.blocks.items()))
        self.assertEqual({left}, set(close_group_selection(editor.document, [left])))
        editor.undo()
        self.assertFalse(editor.document.blocks)

    def test_explicit_single_chests_are_not_grouped_by_selection_copy_or_erase(self):
        left, right = (15, 1, 15), (16, 1, 15)
        nbt = {'Items': [{'Slot': 0, 'Count': 5}], 'CustomName': 'kept'}
        explicit_single = make_cell(CHEST, WATER, compose_actor({'chestIsLargeChest': False}, nbt))
        for size in ((32, 4, 32), SIZES[1]):
            for other in (CHEST, explicit_single):
                with self.subTest(size=size, other=other):
                    original = {left: explicit_single, right: other}
                    editor = Editor(Document(size, original))
                    self.assertEqual({left}, set(close_group_selection(editor.document, [left])))
                    self.assertEqual({right}, set(close_group_selection(editor.document, [right])))
                    editor.select_box(left, left)
                    editor.run('copy')
                    self.assertEqual(1, len(editor.clipboard.get('selection', editor.clipboard['blocks'])))
                    editor.paint_at(left, erase=True, respect_selection=False)
                    self.assertEqual(CHEST, foreground(editor.document.get(right)))
                    if other == explicit_single:
                        self.assertEqual(nbt, entity_nbt(actor_data(editor.document.get(right))))
                    editor.undo()
                    self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_actor_only_chest_change_reconciles_partner_in_the_same_history_entry(self):
        left, right = (15, 1, 15), (16, 1, 15)
        nbt = {'Items': [{'Slot': 0, 'Count': 5}], 'CustomName': 'kept'}
        original = {left: CHEST, right: CHEST}
        for size in ((32, 4, 32), SIZES[1]):
            with self.subTest(size=size):
                editor = Editor(Document(size, original))
                paired = chest_pair_actor(make_cell(CHEST, WATER, compose_actor({}, nbt)), left, right)
                self.assertEqual(2, editor._commit('actor', {left: paired}, False, whole=True))
                self.assertEqual(left, chest_render_pair_position(editor.document.get(right), right))
                self.assertEqual(nbt, entity_nbt(actor_data(editor.document.get(left))))
                self.assertEqual(WATER, background(editor.document.get(left)))
                self.assertEqual({(0, 0, 0), (1, 0, 0)}, editor.last_changed_chunks)
                after = dict(editor.document.blocks.items())
                self.assertTrue(editor.undo())
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertTrue(editor.redo())
                self.assertEqual(after, dict(editor.document.blocks.items()))

    def test_wall_placement_and_break_update_neighbors_in_one_history_entry(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                place(editor, (2, 1, 2), WALL)
                self.assertTrue(states(editor, (2, 1, 2))['wall_post_bit'])
                before = editor.document.blocks.copy()
                place(editor, (3, 1, 2), WALL)
                self.assertEqual('short', states(editor, (2, 1, 2))['wall_connection_type_east'])
                self.assertEqual('short', states(editor, (3, 1, 2))['wall_connection_type_west'])
                paired = editor.document.blocks.copy()
                self.assertEqual(2, len(editor.undo_stack))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.redo()
                self.assertEqual(paired, editor.document.blocks)
                editor.paint_at((3, 1, 2), erase=True, respect_selection=False)
                self.assertEqual('none', states(editor, (2, 1, 2))['wall_connection_type_east'])
                editor.undo()
                self.assertEqual(paired, editor.document.blocks)

    def test_straight_wall_omits_post_and_above_block_controls_arm_height(self):
        editor = Editor(Document(SIZES[0]))
        for pos in ((2, 1, 2), (3, 1, 2), (4, 1, 2)):
            place(editor, pos, WALL)
        center = (3, 1, 2)
        self.assertFalse(states(editor, center)['wall_post_bit'])
        before = editor.document.blocks.copy()
        place(editor, (3, 2, 2), STONE)
        current = states(editor, center)
        self.assertEqual('tall', current['wall_connection_type_west'])
        self.assertEqual('tall', current['wall_connection_type_east'])
        self.assertFalse(current['wall_post_bit'])
        editor.undo()
        self.assertEqual(before, editor.document.blocks)
        editor.redo()
        editor.paint_at((3, 2, 2), erase=True, respect_selection=False)
        self.assertEqual('short', states(editor, center)['wall_connection_type_east'])

    def test_imported_manual_wall_states_survive_unrelated_edits(self):
        properties = registry.states(WALL)
        properties.update(wall_connection_type_north='short', wall_post_bit=True)
        manual = registry.from_states(WALL[0], properties)
        editor = Editor(Document(SIZES[0], {(2, 1, 2): manual}))
        self.assertEqual(manual, editor.document.get((2, 1, 2)))
        place(editor, (6, 1, 6), STONE)
        self.assertEqual(manual, editor.document.get((2, 1, 2)))
        place(editor, (3, 1, 2), STONE)
        current = states(editor, (2, 1, 2))
        self.assertEqual('short', current['wall_connection_type_east'])
        self.assertEqual('short', current['wall_connection_type_north'])

    def test_unknown_historical_native_states_do_not_block_unrelated_edits(self):
        unknown = ('minecraft:stone', 32767)
        removed = ('minecraft:unknown_old_block', 0)
        old_chest = ('minecraft:chest', 32767)
        editor = Editor(Document(SIZES[0], {(1, 1, 1): unknown, (1, 1, 2): removed,
                                            (2, 1, 2): old_chest}))
        self.assertIsNone(registry.try_canonical(unknown))
        self.assertIsNone(registry.try_canonical(removed))
        self.assertEqual(('minecraft:blue_wool', 0), registry.try_canonical(('minecraft:wool', 11)))
        with self.assertRaises(ValueError):
            registry.canonical(unknown)
        place(editor, (3, 1, 3), WALL)
        self.assertTrue(states(editor, (3, 1, 3))['wall_post_bit'])
        self.assertEqual(unknown, editor.document.get((1, 1, 1)))
        self.assertEqual(removed, editor.document.get((1, 1, 2)))
        self.assertEqual(old_chest, editor.document.get((2, 1, 2)))

    def test_every_native_wall_family_uses_schema_connection_rules(self):
        families = [name for name in registry.BLOCKS
                    if 'wall_post_bit' in registry.states((name, registry.DEFAULT_AUX[name]))]
        self.assertGreater(len(families), 20)
        for name in families:
            with self.subTest(name=name):
                editor = Editor(Document(SIZES[0]))
                place(editor, (2, 1, 2), (name, registry.DEFAULT_AUX[name]))
                place(editor, (3, 1, 2), STONE)
                self.assertEqual('short', states(editor, (2, 1, 2))['wall_connection_type_east'])
                editor.paint_at((3, 1, 2), erase=True, respect_selection=False)
                self.assertEqual('none', states(editor, (2, 1, 2))['wall_connection_type_east'])

    def test_all_copper_bar_variants_connect_walls_in_both_placement_orders_and_undo(self):
        # NEMC 3.9 native probe: all eight variants form short arms in all
        # four directions, independent of whether the wall or bar is placed first.
        names = sorted(name for name in registry.BLOCKS if name.endswith('copper_bars'))
        self.assertEqual(8, len(names))
        center = (15, 1, 15)
        neighbors = {'east': (16, 1, 15), 'west': (14, 1, 15),
                     'south': (15, 1, 16), 'north': (15, 1, 14)}
        for name in names:
            for face, target in neighbors.items():
                for wall_first in (False, True):
                    with self.subTest(name=name, face=face, wall_first=wall_first):
                        editor = Editor(Document((32, 4, 32)))
                        entries = [(center, WALL), (target, (name, registry.DEFAULT_AUX[name]))]
                        for pos, value in entries if wall_first else reversed(entries):
                            place(editor, pos, value)
                        self.assertEqual('short', states(editor, center)['wall_connection_type_' + face])
                        connected = editor.document.blocks.copy()
                        editor.paint_at(target, erase=True, respect_selection=False)
                        self.assertEqual('none', states(editor, center)['wall_connection_type_' + face])
                        editor.undo()
                        self.assertEqual(connected, editor.document.blocks)

    def test_stair_corners_and_side_blockers_provide_complete_faces(self):
        pos = (3, 1, 3)
        for upside_down in (False, True):
            with self.subTest(upside_down=upside_down):
                def stair(direction):
                    return registry.from_states('minecraft:oak_stairs',
                                                {'weirdo_direction': direction,
                                                 'upside_down_bit': upside_down})
                north, east = stair(3), stair(0)
                cells = {pos: north}
                get = lambda target: cells.get(target, AIR)
                self.assertEqual(3, _stair_mask(get, pos, north))
                self.assertTrue(_solid_face(north, 'north', get, pos))
                cells[(3, 1, 2)] = east
                self.assertEqual(2, _stair_mask(get, pos, north))
                self.assertFalse(any(_solid_face(north, face, get, pos)
                                     for face in ('north', 'east', 'south', 'west')))
                cells[(2, 1, 3)] = north
                self.assertEqual(3, _stair_mask(get, pos, north))
                del cells[(3, 1, 2)]
                del cells[(2, 1, 3)]
                cells[(3, 1, 4)] = east
                self.assertEqual(11, _stair_mask(get, pos, north))
                self.assertTrue(_solid_face(north, 'north', get, pos))
                self.assertTrue(_solid_face(north, 'east', get, pos))
                self.assertFalse(_solid_face(north, 'west', get, pos))

    def test_indirect_stair_corner_edit_updates_wall_and_undo(self):
        north = registry.from_states('minecraft:oak_stairs',
                                     {'weirdo_direction': 3, 'upside_down_bit': False})
        west = registry.from_states('minecraft:oak_stairs',
                                    {'weirdo_direction': 1, 'upside_down_bit': False})
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                place(editor, (3, 1, 3), WALL)
                place(editor, (4, 1, 3), north)
                self.assertEqual('none', states(editor, (3, 1, 3))['wall_connection_type_east'])
                before = editor.document.blocks.copy()
                place(editor, (4, 1, 4), west)
                self.assertEqual('short', states(editor, (3, 1, 3))['wall_connection_type_east'])
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.redo()
                editor.paint_at((4, 1, 4), erase=True, respect_selection=False)
                self.assertEqual('none', states(editor, (3, 1, 3))['wall_connection_type_east'])

    def test_stair_corner_context_across_chunk_boundary_updates_wall(self):
        north = registry.from_states('minecraft:oak_stairs',
                                     {'weirdo_direction': 3, 'upside_down_bit': False})
        west = registry.from_states('minecraft:oak_stairs',
                                    {'weirdo_direction': 1, 'upside_down_bit': False})
        editor = Editor(Document(SIZES[1]))
        place(editor, (15, 1, 14), WALL)
        place(editor, (16, 1, 14), north)
        place(editor, (16, 1, 15), west)
        self.assertEqual('short', states(editor, (15, 1, 14))['wall_connection_type_east'])
        editor.undo()
        self.assertEqual('none', states(editor, (15, 1, 14))['wall_connection_type_east'])

    def test_locked_neighbor_layer_is_not_changed_by_passive_updates(self):
        properties = registry.states(WALL)
        properties.update(wall_connection_type_east='short', wall_post_bit=True)
        manual = registry.from_states(WALL[0], properties)
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size, {(2, 1, 2): manual, (3, 1, 2): STONE}))
                editor.locked_layers.add(1)
                place(editor, (2, 2, 2), STONE)
                self.assertEqual(manual, editor.document.get((2, 1, 2)))
                editor.undo()
                self.assertEqual(manual, editor.document.get((2, 1, 2)))

    def test_background_and_actor_data_survive_passive_connection_update(self):
        actor = {'custom': {'keep': [1, 2, 3]}}
        editor = Editor(Document(SIZES[0], {(2, 1, 2): make_cell(WALL, WATER, actor)}))
        place(editor, (3, 1, 2), STONE)
        self.assertEqual(WATER, background(editor.document.get((2, 1, 2))))
        self.assertEqual(actor, actor_data(editor.document.get((2, 1, 2))))

    def test_gate_connects_on_its_sides_and_tracks_in_wall_bit(self):
        gate = ('minecraft:fence_gate', 0)
        editor = Editor(Document(SIZES[0]))
        place(editor, (3, 1, 2), gate)
        place(editor, (2, 1, 2), WALL)
        self.assertEqual('short', states(editor, (2, 1, 2))['wall_connection_type_east'])
        self.assertTrue(states(editor, (3, 1, 2))['in_wall_bit'])
        editor.paint_at((2, 1, 2), erase=True, respect_selection=False)
        self.assertFalse(states(editor, (3, 1, 2))['in_wall_bit'])

    def test_rails_form_and_remove_curves_with_passive_neighbor_history(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                place(editor, (2, 1, 1), RAIL)
                place(editor, (2, 1, 2), RAIL)
                before = editor.document.blocks.copy()
                place(editor, (3, 1, 2), RAIL)
                self.assertEqual(9, states(editor, (2, 1, 2))['rail_direction'])
                self.assertEqual(1, states(editor, (3, 1, 2))['rail_direction'])
                curve = editor.document.blocks.copy()
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.redo()
                self.assertEqual(curve, editor.document.blocks)
                editor.paint_at((3, 1, 2), erase=True, respect_selection=False)
                self.assertEqual(0, states(editor, (2, 1, 2))['rail_direction'])

    def test_every_rail_family_connects_slopes_and_preserves_power_states(self):
        families = []
        for name in registry.BLOCKS:
            default = (name, registry.DEFAULT_AUX[name])
            if 'rail_direction' in registry.states(default):
                families.append(name)
        self.assertEqual(4, len(families))
        for name in families:
            with self.subTest(name=name):
                properties = registry.states((name, registry.DEFAULT_AUX[name]))
                if 'rail_data_bit' in properties:
                    properties['rail_data_bit'] = True
                value = registry.from_states(name, properties)
                editor = Editor(Document(SIZES[0]))
                place(editor, (2, 1, 2), value)
                place(editor, (3, 2, 2), value)
                self.assertEqual(2, states(editor, (2, 1, 2))['rail_direction'])
                self.assertEqual(1, states(editor, (3, 2, 2))['rail_direction'])
                if 'rail_data_bit' in properties:
                    self.assertTrue(states(editor, (2, 1, 2))['rail_data_bit'])

    def test_whole_cell_paste_keeps_supplied_wall_and_rail_states(self):
        properties = registry.states(WALL)
        properties.update(wall_connection_type_east='tall', wall_post_bit=False)
        wall = registry.from_states(WALL[0], properties)
        curved = registry.from_states(RAIL[0], {'rail_direction': 6})
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                editor.clipboard = {'size': (2, 1, 1), 'origin': (0, 0, 0),
                                    'blocks': {(0, 0, 0): wall, (1, 0, 0): curved}}
                editor.start = (2, 1, 2)
                editor.run('paste')
                self.assertEqual(wall, editor.document.get((2, 1, 2)))
                self.assertEqual(curved, editor.document.get((3, 1, 2)))

    def test_native_double_chest_placement_groups_and_preserves_client_actor(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                place(editor, (2, 1, 2), CHEST)
                place(editor, (3, 1, 2), CHEST)
                left, right = editor.document.get((2, 1, 2)), editor.document.get((3, 1, 2))
                self.assertTrue(actor_data(left)['chestIsLargeChest'])
                self.assertTrue(actor_data(left)['chestMainSubChest'])
                self.assertFalse(actor_data(right)['chestMainSubChest'])
                self.assertEqual(-0.5, actor_data(right)['chestModelOffset'])
                self.assertEqual({(2, 1, 2), (3, 1, 2)}, set(close_group_selection(editor.document, [(2, 1, 2)])))
                place(editor, (4, 1, 2), CHEST)
                self.assertFalse(actor_data(editor.document.get((4, 1, 2)))['chestIsLargeChest'])
                self.assertEqual({(4, 1, 2)}, set(close_group_selection(editor.document, [(4, 1, 2)])))
                before = editor.document.blocks.copy()
                self.assertEqual(0, place(editor, (2, 1, 2), CHEST))
                self.assertEqual(before, editor.document.blocks)
                editor.paint_at((2, 1, 2), erase=True, respect_selection=False)
                self.assertEqual(AIR, editor.document.get((2, 1, 2)))
                self.assertEqual(AIR, editor.document.get((3, 1, 2)))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)

    def test_typed_chest_root_and_four_touching_chests_resolve_actual_pairs(self):
        for name in ('minecraft:chest', 'minecraft:trapped_chest'):
            base = registry.from_states(name, {'minecraft:cardinal_direction': 'north'})
            values = {}
            for x in (1, 2, 3, 4):
                partner = x + 1 if x % 2 else x - 1
                data = {'__type__': 10, '__value__': {'keep': {'__type__': 8, '__value__': 'name'}}}
                value = make_cell(base, WATER, data)
                values[(x, 1, 2)] = chest_pair_actor(value, (x, 1, 2), (partner, 1, 2))
            editor = Editor(Document(SIZES[0], values))
            get = lambda pos: editor.document.get(pos) if editor.document.contains(pos) else None
            for x in values:
                partner = chest_render_pair_position(values[x], x)
                self.assertEqual(partner, paired_cell_position(get, x))
                self.assertEqual('name', scalar(root_payload(actor_data(values[x])), 'keep'))
            self.assertEqual({(2, 1, 2), (1, 1, 2)}, set(close_group_selection(editor.document, [(2, 1, 2)])))

    def test_ambiguous_actorless_chest_chain_does_not_expand_selection(self):
        editor = Editor(Document(SIZES[0], {(x, 1, 2): CHEST for x in (1, 2, 3)}))
        for x in (1, 2, 3):
            self.assertEqual({(x, 1, 2)}, set(close_group_selection(editor.document, [(x, 1, 2)])))

    def test_chest_pairing_preserves_full_nbt_separate_from_renderer_fields(self):
        nbt = {'pairx': {'__type__': 3, '__value__': 3},
               'pairz': {'__type__': 3, '__value__': 2},
               'Items': {'__type__': 9, '__value__': [{'Slot': 0, 'Count': 5}]},
               'CustomName': {'__type__': 8, '__value__': 'kept'}}
        render = {'chestOpenness': 0.25}
        left = make_cell(CHEST, WATER, compose_actor(render, nbt))
        updated = chest_pair_actor(left, (2, 1, 2), (3, 1, 2))
        actor = actor_data(updated)
        self.assertEqual(nbt, entity_nbt(actor))
        self.assertNotIn('chestIsLargeChest', entity_nbt(actor))
        self.assertTrue(render_actor(actor)['chestIsLargeChest'])
        self.assertEqual(0.25, render_actor(actor)['chestOpenness'])
        self.assertEqual((3, 1, 2), chest_render_pair_position(updated, (2, 1, 2)))
        unpaired = chest_pair_actor(updated, (2, 1, 2))
        self.assertNotIn('pairx', entity_nbt(actor_data(unpaired)))
        self.assertNotIn('pairz', entity_nbt(actor_data(unpaired)))
        self.assertEqual(nbt['Items'], entity_nbt(actor_data(unpaired))['Items'])
        self.assertFalse(render_actor(actor_data(unpaired))['chestIsLargeChest'])
        self.assertEqual(WATER, background(unpaired))

    def test_chest_pairing_adds_renderer_fields_to_nbt_only_cell_without_mixing(self):
        nbt = {'Items': {'__type__': 9, '__value__': []}}
        left = make_cell(CHEST, AIR, nbt)
        updated = chest_pair_actor(left, (2, 1, 2), (3, 1, 2))
        self.assertEqual(nbt, entity_nbt(actor_data(updated)))
        self.assertTrue(render_actor(actor_data(updated))['chestIsLargeChest'])
        self.assertEqual((3, 1, 2), chest_render_pair_position(updated, (2, 1, 2)))

    def test_all_native_pairable_chest_families_use_the_same_editor_connection_path(self):
        families = [name for name in registry.BLOCKS
                    if (name == 'minecraft:chest' or name.endswith('_chest')) and
                    name != 'minecraft:ender_chest']
        self.assertEqual(10, len(families))
        for name in families:
            with self.subTest(name=name):
                material = registry.from_states(name, {'minecraft:cardinal_direction': 'north'})
                editor = Editor(Document(SIZES[0]))
                place(editor, (2, 1, 2), material)
                place(editor, (3, 1, 2), material)
                self.assertTrue(render_actor(actor_data(editor.document.get((2, 1, 2))))['chestIsLargeChest'])
                self.assertEqual({(2, 1, 2), (3, 1, 2)},
                                 set(close_group_selection(editor.document, [(2, 1, 2)])))
                editor.paint_at((2, 1, 2), erase=True, respect_selection=False)
                self.assertEqual(AIR, editor.document.get((3, 1, 2)))

    def test_copper_chest_missing_client_actor_is_hydrated_from_separate_server_pairing_nbt(self):
        material = registry.from_states('minecraft:copper_chest',
                                        {'minecraft:cardinal_direction': 'north'})
        nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
               'pairx': {'__type__': 3, '__value__': 3},
               'pairz': {'__type__': 3, '__value__': 2},
               'pairlead': {'__type__': 1, '__value__': 1},
               'Items': [{'Slot': 0, 'Count': 5}]}
        original = make_cell(material, WATER, compose_actor({}, nbt))
        updated = hydrate_chest_actor(original, (2, 1, 2))
        payload = actor_data(updated)
        self.assertEqual(nbt, entity_nbt(payload))
        self.assertTrue(render_actor(payload)['chestIsLargeChest'])
        self.assertTrue(render_actor(payload)['chestMainSubChest'])
        self.assertEqual(0.0, render_actor(payload)['chestModelOffset'])
        self.assertEqual((3, 1, 2), chest_render_pair_position(updated, (2, 1, 2)))
        self.assertEqual(WATER, background(updated))
        self.assertEqual(updated, hydrate_chest_actor(updated, (2, 1, 2)))
        sub_nbt = dict(nbt, pairx={'__type__': 3, '__value__': 2})
        sub = hydrate_chest_actor(make_cell(material, AIR, compose_actor({}, sub_nbt)), (3, 1, 2))
        self.assertFalse(render_actor(actor_data(sub))['chestMainSubChest'])
        self.assertEqual(-0.5, render_actor(actor_data(sub))['chestModelOffset'])

    def test_cancelled_job_during_neighbor_reconciliation_does_not_publish(self):
        editor = Editor(Document(SIZES[1], {(2, 1, 2): WALL}))
        editor.select_box((3, 1, 2), (3, 1, 2))
        editor.material = WALL
        before = editor.document.blocks.copy()
        job = EditJob(editor, 'fill')
        job.step(budget=2, seconds=1)
        self.assertFalse(job.done)
        job.cancel()
        job.step()
        self.assertEqual(before, editor.document.blocks)
        self.assertFalse(editor.undo_stack)


if __name__ == '__main__':
    unittest.main()

"""All edit paths share explicit layers and automatic composition semantics."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_groups import group_partner
from projection.block_traits_data import SNOW_COVERABLE_BLOCKS
from projection.cell import actor_data, background, foreground, make_cell
from projection.model import AIR, Document, Editor, close_group_selection
from projection.session import Session

FENCE = ('minecraft:oak_fence', 0)
WATER = ('minecraft:water', 0)
PLANT = ('minecraft:short_grass', 0)
SNOW = ('minecraft:snow_layer', 2)
STONE = ('minecraft:stone', 0)
DOOR = ('minecraft:wooden_door', 0)
SIZES = ((8, 5, 8), (64, 128, 64))


def place(editor, pos, value):
    editor.material = value
    return editor.paint_at(pos, respect_selection=False)


class PreferenceBridge(object):
    def __init__(self, preferences=None):
        self.preferences = preferences

    def load_preferences(self):
        return self.preferences

    def save_preferences(self, data):
        self.preferences = data
        return True


class AutomaticEditorTests(unittest.TestCase):
    def setUp(self):
        self.water = patch('projection.block_traits.is_waterloggable',
                           lambda material: material[0] in (FENCE[0], DOOR[0]), create=True)
        self.water.start()
        self.addCleanup(self.water.stop)

    def test_automatic_water_composes_both_orders_and_erases_the_foreground_first(self):
        pos = (2, 1, 2)
        for first, second in ((FENCE, WATER), (WATER, FENCE)):
            editor = Editor(Document(SIZES[0]))
            editor.edit_layer = 2
            place(editor, pos, first)
            place(editor, pos, second)
            self.assertEqual(make_cell(FENCE, WATER), editor.document.get(pos))
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(WATER, editor.document.get(pos))
            editor.undo()
            self.assertEqual(make_cell(FENCE, WATER), editor.document.get(pos))
            editor.redo()
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(AIR, editor.document.get(pos))

    def test_automatic_snow_keeps_native_order_and_explicit_modes_keep_their_layer(self):
        pos = (2, 1, 2)
        for first, second in ((PLANT, SNOW), (SNOW, PLANT)):
            editor = Editor(Document(SIZES[0]))
            editor.edit_layer = 2
            place(editor, pos, first)
            place(editor, pos, second)
            cell = editor.document.get(pos)
            self.assertEqual('minecraft:snow_layer', foreground(cell)[0])
            self.assertEqual(PLANT, background(cell))
            self.assertTrue(registry.states(foreground(cell))['covered_bit'])
            self.assertEqual(2, registry.states(foreground(cell))['height'])
            editor.edit_layer = 1
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(SNOW, editor.document.get(pos))
            editor.undo()
            editor.edit_layer = 0
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(make_cell(AIR, PLANT), editor.document.get(pos))
            editor.undo()
            editor.edit_layer = 2
            editor.paint_at(pos, erase=True, respect_selection=False)
            self.assertEqual(PLANT, editor.document.get(pos))

    def test_batch_fill_and_erase_use_the_same_automatic_water_semantics(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size, {(2, 1, 2): FENCE, (3, 1, 2): FENCE}))
                editor.edit_layer, editor.material = 2, WATER
                editor.select_box((2, 1, 2), (3, 1, 2))
                self.assertEqual(2, editor.run('fill'))
                for x in (2, 3):
                    self.assertEqual(make_cell(FENCE, WATER), editor.document.get((x, 1, 2)))
                before = editor.document.blocks.copy()
                self.assertEqual(2, editor.run('erase'))
                self.assertEqual(WATER, editor.document.get((2, 1, 2)))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.edit_layer = 1
                self.assertEqual(2, editor.run('erase'))
                self.assertEqual(FENCE, editor.document.get((2, 1, 2)))

    def test_automatic_snow_fill_preserves_each_plant_and_undo(self):
        for size in SIZES:
            with self.subTest(size=size):
                positions = ((2, 1, 2), (3, 1, 2))
                editor = Editor(Document(size, dict.fromkeys(positions, PLANT)))
                editor.edit_layer, editor.material = 2, SNOW
                editor.select_box(*positions)
                before = editor.document.blocks.copy()
                self.assertEqual(2, editor.run('fill'))
                for pos in positions:
                    self.assertEqual(PLANT, background(editor.document.get(pos)))
                    self.assertTrue(registry.states(foreground(editor.document.get(pos)))['covered_bit'])
                editor.undo()
                self.assertEqual(before, editor.document.blocks)

    def test_every_measured_native_snow_coverable_block_uses_the_same_editor_path(self):
        self.assertEqual(29, len(SNOW_COVERABLE_BLOCKS))
        pos = (2, 1, 2)
        for name in SNOW_COVERABLE_BLOCKS:
            with self.subTest(name=name):
                plant = (name, registry.DEFAULT_AUX[name])
                for first, second in ((plant, SNOW), (SNOW, plant)):
                    editor = Editor(Document(SIZES[0]))
                    editor.edit_layer = 2
                    place(editor, pos, first)
                    place(editor, pos, second)
                    self.assertEqual(plant, background(editor.document.get(pos)))
                    self.assertTrue(registry.states(foreground(editor.document.get(pos)))['covered_bit'])
                    editor.paint_at(pos, erase=True, respect_selection=False)
                    self.assertEqual(plant, editor.document.get(pos))

    def test_locked_group_partner_prevents_atomic_background_or_auto_erasure(self):
        bottom, top = (2, 1, 2), (2, 2, 2)
        for mode in (0, 1, 2):
            with self.subTest(mode=mode):
                front_bottom, front_top = DOOR, group_partner(DOOR)[1]
                if mode == 1:
                    front_bottom, front_top = make_cell(STONE, front_bottom), make_cell(STONE, front_top)
                editor = Editor(Document(SIZES[0], {bottom: front_bottom, top: front_top}))
                editor.edit_layer = mode
                editor.locked_layers.add(top[1])
                before = editor.document.blocks.copy()
                self.assertEqual(0, editor.paint_at(bottom, erase=True, respect_selection=False))
                self.assertEqual(before, editor.document.blocks)
                self.assertFalse(editor.undo_stack)

    def test_automatic_overlay_preserves_door_group_and_group_erasure_leaves_water(self):
        bottom, top = (2, 1, 2), (2, 2, 2)
        door_top = group_partner(DOOR)[1]
        editor = Editor(Document(SIZES[0]))
        editor.edit_layer = 2
        place(editor, bottom, DOOR)
        place(editor, bottom, WATER)
        self.assertEqual(make_cell(DOOR, WATER), editor.document.get(bottom))
        self.assertEqual(door_top, editor.document.get(top))
        place(editor, top, WATER)
        before = editor.document.blocks.copy()
        self.assertEqual(2, editor.paint_at(bottom, erase=True, respect_selection=False))
        self.assertEqual(WATER, editor.document.get(bottom))
        self.assertEqual(WATER, editor.document.get(top))
        editor.undo()
        self.assertEqual(before, editor.document.blocks)

    def test_cross_layer_group_links_find_and_erase_the_actual_partner_layer(self):
        plant = ('minecraft:tall_grass', 0)
        bottom, top = (2, 1, 2), (2, 2, 2)
        plant_top = group_partner(plant)[1]
        editor = Editor(Document(SIZES[0], {bottom: make_cell(STONE, plant), top: plant_top}))
        self.assertEqual({bottom, top}, set(close_group_selection(editor.document, [bottom])))
        editor.edit_layer = 1
        self.assertEqual(2, editor.paint_at(bottom, erase=True, respect_selection=False))
        self.assertEqual(STONE, editor.document.get(bottom))
        self.assertEqual(AIR, editor.document.get(top))
        editor.undo()
        self.assertEqual(plant_top, editor.document.get(top))

    def test_automatic_background_only_erasure_and_same_material_preserve_actor(self):
        pos = (2, 1, 2)
        editor = Editor(Document(SIZES[0], {pos: make_cell(AIR, PLANT)}))
        editor.edit_layer = 2
        editor.paint_at(pos, erase=True, respect_selection=False)
        self.assertEqual(AIR, editor.document.get(pos))
        actor = {'keep': [1, 2, 3]}
        editor = Editor(Document(SIZES[0], {pos: make_cell(FENCE, AIR, actor)}))
        editor.edit_layer = 2
        place(editor, pos, WATER)
        self.assertEqual(actor, actor_data(editor.document.get(pos)))
        editor.edit_layer = 1
        editor.paint_at(pos, erase=True, respect_selection=False)
        self.assertEqual(actor, actor_data(editor.document.get(pos)))

    def test_session_defaults_mode_preferences_and_targeting_are_reachable(self):
        bridge = PreferenceBridge()
        session = Session(bridge)
        self.assertEqual(2, session.editor.edit_layer)
        session.set_editor('edit_layer', 1)
        self.assertEqual(2, bridge.preferences['version'])
        self.assertEqual(1, bridge.preferences['edit_layer'])
        restored = Session(bridge)
        restored._load_preferences()
        self.assertEqual(1, restored.editor.edit_layer)
        legacy = Session(PreferenceBridge({'edit_layer': 0, 'spectrum_speed': 3.0}))
        legacy._load_preferences()
        self.assertEqual(0, legacy.editor.edit_layer)
        for bad in (-1, 3, True, 2.0):
            with self.assertRaises(ValueError):
                session.set_editor('edit_layer', bad)
        pos = (2, 1, 2)
        session.editor = Editor(Document(SIZES[0], {pos: FENCE}))
        session.editor.edit_layer, session.editor.material = 2, WATER
        self.assertEqual((pos, None), session.placement_target(pos, (1, 0, 0)))
        session.editor.edit_layer = 0
        self.assertEqual(((3, 1, 2), None), session.placement_target(pos, (1, 0, 0)))
        session.editor.edit_layer = 1
        self.assertEqual((pos, None), session.placement_target(pos, (1, 0, 0)))

    def test_air_material_selection_checks_the_selected_layer_in_small_and_large_documents(self):
        cells = {(2, 1, 2): STONE,
                 (3, 1, 2): make_cell(AIR, WATER),
                 (4, 1, 2): make_cell(FENCE, WATER)}
        for size in SIZES:
            for mode in (0, 1, 2):
                with self.subTest(size=size, mode=mode):
                    editor = Editor(Document(size, cells))
                    editor.edit_layer, editor.source = mode, AIR
                    occupied = ((2, 1, 2), (4, 1, 2)) if mode == 0 else (
                        ((3, 1, 2), (4, 1, 2)) if mode == 1 else tuple(cells))
                    editor.run('select_material')
                    self.assertEqual(size[0] * size[1] * size[2] - len(occupied),
                                     len(editor.selection))
                    for pos in cells:
                        self.assertEqual(pos not in occupied, pos in editor.selection)
                    self.assertIn((0, 0, 0), editor.selection)

    def test_automatic_group_overlap_removes_only_the_old_parts_and_promotes_their_water(self):
        bed = ('minecraft:bed', 0)
        bottom, top, old_head = (2, 1, 2), (2, 2, 2), (2, 2, 3)
        cells = {top: make_cell(bed, WATER), old_head: make_cell(group_partner(bed)[1], WATER)}
        for size in SIZES:
            editor = Editor(Document(size, cells))
            editor.edit_layer, editor.material = 2, DOOR
            self.assertEqual(3, editor.paint_at(bottom, respect_selection=False))
            self.assertEqual(DOOR, editor.document.get(bottom))
            self.assertEqual(make_cell(group_partner(DOOR)[1], WATER), editor.document.get(top))
            self.assertEqual(WATER, editor.document.get(old_head))
            editor.undo()
            self.assertEqual(cells, dict(editor.document.blocks.items()))


if __name__ == '__main__':
    unittest.main()

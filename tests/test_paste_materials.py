import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.model import AIR, Document, Editor, bounds
from projection.jobs import EditJob
from projection.materials import entry, search_blocks, normalize_palette, inventory_info, unique_inventory
from projection.session import Session

STONE = ('minecraft:stone', 0)
WOOD = ('minecraft:planks', 1)


class Bridge:
    def later(self, delay, callback):
        self.callback = callback

    def save_preferences(self, value):
        self.preferences = value


class PasteTests(unittest.TestCase):
    def editor(self, large=False):
        e = Editor(Document((64, 128, 64) if large else (12, 8, 12)))
        e.document.blocks[(1, 1, 1)] = STONE
        e.document.blocks[(3, 2, 2)] = WOOD
        e.select_box((1, 1, 1), (3, 2, 2))
        e.run('copy')
        e.select_box((5, 2, 4), (5, 2, 4))
        return e

    def test_complete_clip_pastes_from_one_cell_and_undoes_in_one_step(self):
        for large in (False, True):
            e = self.editor(large)
            e.document.blocks[(6, 2, 4)] = STONE
            self.assertEqual(3, e.run('paste'))
            self.assertEqual(STONE, e.document.get((5, 2, 4)))
            self.assertEqual(WOOD, e.document.get((7, 3, 5)))
            self.assertEqual(AIR, e.document.get((6, 2, 4)))
            self.assertEqual(((5, 2, 4), (7, 3, 5)), bounds(e.selection))
            self.assertEqual(1, len(e.undo_stack))
            e.undo()
            self.assertEqual(AIR, e.document.get((7, 3, 5)))
            self.assertEqual(STONE, e.document.get((6, 2, 4)))

    def test_airless_filters_locks_and_empty_destination_selection(self):
        e = self.editor()
        e.document.blocks[(6, 2, 4)] = STONE
        e.selection = set()
        e.locked_layers.add(3)
        e.run('paste_airless')
        self.assertEqual(STONE, e.document.get((5, 2, 4)))
        self.assertEqual(STONE, e.document.get((6, 2, 4)))
        self.assertEqual(AIR, e.document.get((7, 3, 5)))
        e.undo()
        e.mask = 'solid'
        e.run('paste_airless')
        self.assertEqual(AIR, e.document.get((5, 2, 4)))

    def test_out_of_bounds_and_cancel_are_atomic(self):
        e = self.editor(True)
        before = dict(e.document.blocks.items())
        e.start = (63, 0, 0)
        with self.assertRaisesRegex(ValueError, '边界'):
            e.run('paste_airless')
        self.assertEqual(before, dict(e.document.blocks.items()))
        e.start = (5, 2, 4)
        job = EditJob(e, 'paste')
        job.step(budget=1)
        self.assertEqual(12, job.total)
        job.cancel(); job.step()
        self.assertEqual(before, dict(e.document.blocks.items()))
        self.assertFalse(e.undo_stack)

    def test_session_paste_click_locates_without_edit_or_selection_change(self):
        s = Session(Bridge()); s.editor = self.editor()
        s.choose_tool('paste')
        before = (s.editor.revision, s.editor.selection_revision)
        s.point_action((7, 2, 6))
        self.assertEqual((7, 2, 6), s.paste_origin)
        self.assertTrue(s.paste_pinned)
        self.assertEqual(before, (s.editor.revision, s.editor.selection_revision))
        s.run()
        self.assertEqual(WOOD, s.editor.document.get((9, 3, 7)))


class MaterialsTests(unittest.TestCase):
    def test_material_lists_resolve_legacy_variants_without_opening_catalogue(self):
        from unittest.mock import patch
        from projection.materials import DISPLAY_NAMES, display_name
        translations = {
            ('minecraft:grass_block', 0): '草方块',
            ('minecraft:spruce_planks', 0): '云杉木板',
            ('minecraft:oak_leaves', 0): '橡树树叶',
            ('minecraft:cyan_stained_glass', 0): '青色染色玻璃',
        }
        legacy = [('minecraft:grass', 0), WOOD,
                  ('minecraft:leaves', 0), ('minecraft:stained_glass', 9)]
        s = Session(Bridge())
        before = s.editor.document.to_data()
        calls = []
        def describe(value):
            calls.append(value)
            return translations[value]
        s.bridge.describe_material = describe
        with patch.dict(DISPLAY_NAMES, {}, clear=True):
            names = [s.describe_material(value) for value in legacy]
            self.assertEqual(list(translations.values()), names)
            self.assertEqual(list(translations), calls)
            # The picker and both material lists reuse one cache, including aux aliases.
            self.assertEqual(names, [display_name(value) for value in legacy])
            self.assertEqual(names, [s.describe_material(value) for value in translations])
            self.assertEqual(4, len(calls))
        self.assertFalse(s.catalogue_loading)
        self.assertFalse(s.catalogue_ready)
        self.assertEqual(before, s.editor.document.to_data())

    def test_material_names_follow_picker_cache_and_retry_missing_translations(self):
        from unittest.mock import Mock, patch
        from projection.materials import DISPLAY_NAMES, display_name
        s = Session(Bridge())
        value = ('custom:unloaded_block', 3)
        s.bridge.describe_material = Mock(side_effect=[None, '定制方块'])
        with patch.dict(DISPLAY_NAMES, {}, clear=True):
            self.assertEqual('unloaded_block', s.describe_material(value))
            self.assertNotIn(value, DISPLAY_NAMES)
            self.assertEqual('定制方块', s.describe_material(value))
            entry('minecraft:spruce_planks', 0, '云杉木板')
            self.assertEqual('云杉木板', s.describe_material(WOOD))
            self.assertEqual('云杉木板', display_name(WOOD))
            self.assertEqual(2, s.bridge.describe_material.call_count)

    def test_custom_aux_is_independent_and_does_not_invalidate_workspace(self):
        from projection.materials import MATERIAL_CHANNELS, with_aux
        s = Session(Bridge())
        workspace, palette, browser = [], [], []
        s.subscribe(lambda: workspace.append(True), ())
        s.subscribe(lambda: palette.append(True), ('materials',))
        s.subscribe(lambda: browser.append(True), ('material_browser',))
        before = (s.content_revision, s.editor.revision, dict(s.editor.document.blocks.items()))
        for channel in MATERIAL_CHANNELS:
            s.material_browser = channel
            s.add_material(with_aux(('minecraft:wool', 0), '15'))
            self.assertEqual(('minecraft:wool', 15), getattr(s.editor, channel))
            s.set_editor(channel, ('minecraft:wool', 3))
        self.assertEqual(1, s.palette.count(('minecraft:wool', 15)))
        self.assertIn(('minecraft:wool', 15), normalize_palette(s.bridge.preferences['palette']))
        self.assertFalse(workspace)
        self.assertEqual(8, len(palette))
        self.assertEqual(4, len(browser))
        self.assertEqual(before, (s.content_revision, s.editor.revision, dict(s.editor.document.blocks.items())))

    def test_aux_validation_and_localized_fallback(self):
        from projection.materials import with_aux, display_name
        value = ('custom:aux_test', 0)
        entry(value[0], 0, '测试方块')
        entry(value[0], 4, '测试方块变体')
        self.assertEqual('测试方块', display_name(with_aux(value, '32767')))
        self.assertEqual('测试方块变体', display_name(with_aux(value, '4')))
        self.assertEqual(AIR, with_aux(AIR, '2'))
        for invalid in ('', '**', '-1', '32768', '1.5', 'not a number', '羊毛'):
            with self.assertRaises(ValueError):
                with_aux(value, invalid)
        s = Session(Bridge())
        before = s.editor.material
        with self.assertRaises(ValueError):
            s.set_editor('material', (value[0], -1))
        self.assertEqual(before, s.editor.material)

    def test_internal_names_are_hidden_and_legacy_aliases_share_one_tile(self):
        self.assertFalse(inventory_info({'itemCategory':'construction','itemName':'tile.internal.name'}))
        self.assertFalse(inventory_info({'itemCategory':'none','itemName':'Hidden'}))
        self.assertTrue(inventory_info({'itemCategory':'construction','itemName':'白色混凝土'}))
        legacy=entry('minecraft:concrete',0,'白色混凝土')
        modern=entry('minecraft:white_concrete',0,'白色混凝土')
        self.assertEqual([legacy],unique_inventory([modern,legacy],[legacy['value']]))

    def test_chinese_search_categories_and_aux(self):
        values = [entry('minecraft:concrete', 0, '§f白色混凝土'), entry('minecraft:concrete', 15, '黑色混凝土'),
                  entry('minecraft:planks', 0, '橡木木板'), entry('custom:test', 0, '定制石材')]
        self.assertEqual([values[0]], search_blocks(values, query='白色 混凝土'))
        self.assertEqual(values[:2], search_blocks(values, 'color', 'CONCRETE'))
        self.assertEqual([values[2]], search_blocks(values, 'wood'))
        self.assertEqual([values[3]], search_blocks(values, 'custom'))

    def test_palette_order_remove_and_preferences_do_not_edit_document(self):
        s = Session(Bridge()); before = s.editor.revision
        s.palette = [STONE, WOOD]
        s.edit_palette(WOOD, -1)
        self.assertEqual([WOOD, STONE], s.palette)
        s.edit_palette(STONE)
        self.assertEqual([WOOD], s.palette)
        self.assertEqual(before, s.editor.revision)
        self.assertEqual([WOOD], normalize_palette(s.bridge.preferences['palette']))
        s.range_value('spectrum_speed', 4., editor=False); s.bridge.callback()
        self.assertEqual(4., s.bridge.preferences['spectrum_speed'])
        self.assertEqual([WOOD], s.bridge.preferences['palette'])


if __name__ == '__main__':
    unittest.main()

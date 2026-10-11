"""Whole-cell copy/cut preserves real layered materials and typed inventory."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'behavior_pack/modern_projection'))
from projection.cell import AIR, actor_data, background, foreground, make_cell, rebase
from projection.debug_blueprints import material
from projection.model import Document, Editor
from projection.visible_actor import entity_nbt


class RichCellClipboardTests(unittest.TestCase):
    def test_copy_cut_both_paths_and_all_edit_layers_keep_rich_cells(self):
        source, target = (2, 1, 2), (8, 1, 8)
        nbt = {
            'id': {'__type__': 8, '__value__': 'Chest'},
            'x': {'__type__': 3, '__value__': source[0]},
            'y': {'__type__': 3, '__value__': source[1]},
            'z': {'__type__': 3, '__value__': source[2]},
            'Items': [{'Name': {'__type__': 8, '__value__': 'minecraft:diamond'},
                       'Count': {'__type__': 1, '__value__': 7},
                       'tag': {'x': 900, 'y': 901, 'z': 902}}],
            'future_field': {'__type__': 10, '__value__': {'keep': True}},
        }
        cases = {
            'waterlogged_fence': make_cell(material('oak_fence'), material('water')),
            'snowlogged_fern': make_cell(
                material('snow_layer', {'height': 4, 'covered_bit': True}), material('fern')),
            'waterlogged_nbt_chest': make_cell(material('chest'), material('water'), nbt=nbt),
        }
        for name, cell in cases.items():
            for force_job in (False, True):
                for edit_layer in (2, 0, 1):
                    for tool in ('copy', 'cut'):
                        with self.subTest(case=name, job=force_job, layer=edit_layer, tool=tool), \
                                patch('projection.model.SMALL_VOLUME', 0 if force_job else 32768):
                            editor = Editor(Document((12, 4, 12), {source: cell}))
                            editor.edit_layer = edit_layer
                            editor.select_box(source, source)
                            editor.run(tool)
                            self.assertEqual(AIR if tool == 'cut' else cell, editor.document.get(source))
                            editor.start = target
                            editor.run('paste')
                            expected = rebase(cell, tuple(target[i]-source[i] for i in range(3)))
                            pasted = editor.document.get(target)
                            self.assertEqual(foreground(expected), foreground(pasted))
                            self.assertEqual(background(expected), background(pasted))
                            # Chest connection poses are derived metadata; native NBT is exact.
                            self.assertEqual(entity_nbt(actor_data(expected)), entity_nbt(actor_data(pasted)))
                            self.assertTrue(editor.undo())
                            self.assertEqual(AIR, editor.document.get(target))
                            self.assertTrue(editor.redo())
                            self.assertEqual(pasted, editor.document.get(target))
                            if tool == 'cut':
                                self.assertTrue(editor.undo())
                                self.assertTrue(editor.undo())
                                self.assertEqual(cell, editor.document.get(source))
        self.assertEqual(nbt, entity_nbt(actor_data(cases['waterlogged_nbt_chest'])))


if __name__ == '__main__':
    unittest.main()

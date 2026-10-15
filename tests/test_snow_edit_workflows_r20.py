"""Snow/plant cells retain both layers through Scene commands and local storage."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from projection import block_registry as registry
from projection.cell import AIR, make_cell
from projection.model import Document, Editor
from projection.session import Session
from projection.block_traits_data import SNOW_COVERABLE_BLOCKS
from test_complete_cell_workflows_r11 import WorkflowBridge


class SnowEditWorkflowR20Tests(unittest.TestCase):
    def session(self, plant, height, covered=False):
        bridge = WorkflowBridge()
        session = Session(bridge)
        position = (1, 1, 1)
        snow = registry.from_states('minecraft:snow_layer', {'height': height, 'covered_bit': True})
        cell = make_cell(snow, plant) if covered else plant
        neighbor = ('minecraft:stone', 0)
        session.editor = Editor(Document((3, 3, 3), {position: cell, (2, 1, 1): neighbor}))
        session.editor.select_box(position, position)
        session.name = 'snow workflow'
        return session, bridge, position, snow

    def test_scene_strict_and_automatic_erase_undo_redo_keep_other_layer(self):
        for name in sorted(SNOW_COVERABLE_BLOCKS):
            plant = (name, registry.DEFAULT_AUX[name])
            for height in range(8):
                for layer in (0, 1, 2):
                    with self.subTest(plant=plant, height=height, layer=layer):
                        session, bridge, position, snow = self.session(plant, height, covered=True)
                        before = copy.deepcopy(session.editor.document.blocks)
                        session.set_editor('edit_layer', layer)
                        session.choose_mode('erase')
                        self.assertEqual(1, session.point_action(position))
                        expected = {0: make_cell(AIR, plant), 1: snow, 2: plant}[layer]
                        self.assertEqual(expected, session.editor.document.get(position))
                        after = copy.deepcopy(session.editor.document.blocks)
                        self.assertTrue(session.action(session.editor.undo))
                        self.assertEqual(before, session.editor.document.blocks)
                        self.assertTrue(session.action(session.editor.redo))
                        self.assertEqual(after, session.editor.document.blocks)
                        bridge.settle()

    def test_scene_add_remove_snow_and_saved_library_round_trip(self):
        for name in sorted(SNOW_COVERABLE_BLOCKS):
            plant = (name, registry.DEFAULT_AUX[name])
            for height in range(8):
                with self.subTest(plant=plant, height=height):
                    session, bridge, position, snow = self.session(plant, height)
                    original = copy.deepcopy(session.editor.document.blocks)
                    session.set_editor('edit_layer', 2)
                    session.editor.material = snow
                    session.choose_mode('place')
                    self.assertEqual((position, None), session.placement_target(position, (0, 1, 0)))
                    self.assertEqual(1, session.point_action(position, (0, 1, 0)))
                    self.assertEqual(make_cell(snow, plant), session.editor.document.get(position))
                    covered = copy.deepcopy(session.editor.document.blocks)
                    self.assertEqual({position}, set(session.editor.selection))
                    session.choose_mode('erase')
                    self.assertEqual(1, session.point_action(position))
                    self.assertEqual(original, session.editor.document.blocks)
                    self.assertTrue(session.action(session.editor.undo))
                    self.assertEqual(covered, session.editor.document.blocks)
                    self.assertTrue(session.action(session.editor.redo))
                    self.assertEqual(original, session.editor.document.blocks)
                    self.assertTrue(session.action(session.editor.undo))
                    session.action(session.save)
                    self.assertEqual(1, len(session.library))
                    self.assertIsNotNone(bridge.index)
                    identity = session.library[0]['id']
                    session.editor.document = Document((3, 3, 3))
                    session.load(identity)
                    bridge.settle()
                    self.assertIsNone(session.io_job)
                    self.assertEqual(covered, session.editor.document.blocks)
                    self.assertEqual(2, session.editor.edit_layer)


if __name__ == '__main__':
    unittest.main()

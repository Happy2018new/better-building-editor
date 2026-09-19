import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.camera import OrbitCamera, behind_plane, raycast
from projection.model import Document, Editor, AIR, DIRECTIONS, add
from projection.session import Session
from test_session import Bridge
from test_exact_preview import preview_cells

STONE = ('minecraft:stone', 0)
GLASS = ('minecraft:glass', 0)


class EditNavigationTests(unittest.TestCase):
    def session(self, size=(8,8,8)):
        s = Session(Bridge())
        s.editor = Editor(Document(size))
        s.scene_size = size
        return s

    def test_preview_target_matches_placement_on_all_six_faces(self):
        s = self.session(); s.editor.document.blocks[(3,3,3)] = STONE
        s.choose_mode('place')
        for normal in DIRECTIONS:
            before = (s.editor.selection_revision,s.editor.revision,len(s.editor.undo_stack))
            target,error = s.placement_target((3,3,3),normal)
            self.assertIsNone(error)
            self.assertEqual(before,(s.editor.selection_revision,s.editor.revision,len(s.editor.undo_stack)))
            self.assertEqual(1,s.point_action((3,3,3),normal))
            self.assertEqual({target},s.editor.selection)
            self.assertEqual(target,s.focused)
            self.assertNotEqual(AIR,s.editor.document.get(target))
            s.editor.undo()

    def test_placement_validation_rejects_locked_occupied_and_clipped_targets(self):
        s = self.session(); s.editor.document.blocks[(3,3,3)] = STONE
        s.editor.locked_layers.add(4)
        self.assertIsNotNone(s.placement_target((3,3,3),(0,1,0))[1])
        self.assertIsNotNone(s.placement_target((3,3,3),(0,0,0))[1])
        s.editor.hidden_layers.add(3)
        self.assertIsNotNone(s.placement_target((3,3,6),(0,0,1))[1])

    def test_erase_region_survives_click_and_undo_respects_masks_and_locks(self):
        s = self.session(); e=s.editor; e.material=STONE; e.run('fill')
        e.select_box((1,1,1),(2,2,2)); e.locked_layers.add(2)
        e.document.blocks[(1,1,1)]=GLASS; e.mask='material'; e.filter_material=STONE
        s.choose_mode('erase')
        self.assertEqual('selection',s.erase_scope)
        self.assertFalse(s.point_action((6,6,6)))
        self.assertEqual(8,len(e.selection))
        self.assertEqual(3,s.erase_selection())
        self.assertEqual(8,len(e.selection))
        self.assertEqual(GLASS,e.document.get((1,1,1)))
        self.assertEqual(STONE,e.document.get((1,2,1)))
        e.undo(); self.assertEqual(512,len(e.document.blocks))
        s.set('erase_scope','single'); s.point_action((1,1,2))
        self.assertEqual(1,len(e.selection))

    def test_approach_and_recede_change_scale_without_filtering_or_rebuilding(self):
        s=self.session();e=s.editor;e.material=STONE;e.run('fill')
        s.camera_pose=(0,0,2);s.zoom=2
        before=(len(e.selection),e.revision,len(e.undo_stack),s.preview_signature())
        s.move_depth(1)
        self.assertAlmostEqual(2.4,s.zoom)
        self.assertTrue(s.visible_position((3,3,7)))
        self.assertTrue(s.visible_position((3,3,6)))
        origin,direction=OrbitCamera(0,0).ray(200,150,e.document.size,400,300,20)
        self.assertEqual(7,raycast(e.document,origin,direction,s.visible_position)[0][2])
        s.move_depth(-1)
        self.assertIsNone(s.depth_plane())
        self.assertEqual(2,s.zoom)
        self.assertEqual(before,(len(e.selection),e.revision,len(e.undo_stack),s.preview_signature()))

    def test_oblique_cut_exposes_chunk_interiors_and_matches_brute_force(self):
        s=self.session((35,34,33));e=s.editor;e.material=STONE;e.run('fill')
        e.document.blocks[(16,16,16)]=GLASS
        e.document.blocks[(15,16,15)]=AIR
        for angles, depth in (((0,0),1),((0,0),16),((37,29),22),((217,-23),25)):
            toward=OrbitCamera(*angles).basis()[2]
            plane=(toward,sum((abs(toward[i])+toward[i])*e.document.size[i]/2. for i in range(3))-depth)
            for focus in (None,(30,30,30)):
                origin=(0,0,0) if focus is None else (3,2,1)
                size=e.document.size if focus is None else (32,32,32)
                def visible(p):
                    return all(origin[i]<=p[i]<origin[i]+size[i] for i in range(3)) and p[1]!=17 and behind_plane(p,plane)
                expected={p:value for p,value in e.document.blocks.items() if visible(p) and
                          any(not visible(add(p,d)) or e.document.get(add(p,d))!=STONE for d in DIRECTIONS)}
                self.assertEqual(expected,preview_cells(e.document,hidden=(17,),plane=plane,focus=focus))

    def test_large_region_erase_uses_cancellable_job(self):
        s=self.session((64,100,64));e=s.editor;e.material=STONE
        e.document.blocks[(0,0,0)]=STONE;e.document.blocks[(63,99,63)]=STONE
        s.choose_mode('erase');self.assertTrue(s.erase_selection())
        self.assertIsNotNone(s.edit_job)
        s.cancel_edit();s.edit_job.step()
        self.assertEqual(2,len(e.document.blocks))
        self.assertFalse(e.undo_stack)

    def test_approach_preserves_sparse_content_and_recede_stops_at_minimum(self):
        s = self.session((24,16,24))
        s.editor.document.blocks[(12,8,3)] = STONE
        s.editor.document.blocks[(12,8,2)] = STONE
        s.camera_pose = (0,0,1)
        s.move_depth(1)
        self.assertTrue(s.visible_position((12,8,3)))
        self.assertTrue(s.visible_position((12,8,2)))
        s.move_depth(-1)
        self.assertIsNone(s.depth_plane())
        self.assertTrue(s.visible_position((12,8,3)))
        for unused in range(100):
            s.move_depth(-1)
        self.assertEqual(.25,s.zoom)
        self.assertFalse(s.preview_pending)

    def test_unified_view_modes_share_layer_and_do_not_stack_filters(self):
        s = self.session(); s.layer(3)
        s.display_mode('single')
        self.assertEqual([3],[y for y in range(8) if s.visible_layer(y)])
        s.display_mode('section')
        self.assertEqual([0,1,2,3],[y for y in range(8) if s.visible_layer(y)])
        s.layer(5)
        self.assertEqual(list(range(6)),[y for y in range(8) if s.visible_layer(y)])
        s.display_mode('full')
        self.assertEqual(list(range(8)),[y for y in range(8) if s.visible_layer(y)])
        self.assertEqual(5,s.editor.layer)

import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import Document, Editor, AIR, DIRECTIONS, add
from projection.large_preview import build_preview
from projection.scene_lines import grid_lines, clip_line
from projection.session import Session
from test_session import Bridge

STONE = ('minecraft:stone', 0)
GLASS = ('minecraft:glass', 0)


def preview_cells(doc, **kwargs):
    result = next(v for v in build_preview(doc, **kwargs) if v is not None)
    palette, origin, scale = result
    sx, sy, sz = palette.size
    return {add((i // sz % sx, i // (sx * sz), i % sz), origin): value
            for value, indices in palette.common.items() for i in indices}


class ExactPreviewTests(unittest.TestCase):
    def test_surface_matches_brute_force_across_chunks_holes_hidden_and_crop(self):
        e = Editor(Document((35, 34, 33))); e.material = STONE; e.run('fill')
        e.document.blocks[(15, 16, 15)] = AIR
        e.document.blocks[(17, 16, 16)] = GLASS
        for hidden, layer, focus in (((), None, None), ((17,), None, None), (tuple(range(17,34)), None, None),
                                     ((), 20, None), ((), None, (30,30,30))):
            size = e.document.size if focus is None else (16,16,16)
            origin = (0,0,0) if focus is None else (16,16,16)
            def visible(p):
                return all(origin[i] <= p[i] < origin[i]+size[i] for i in range(3)) and p[1] not in hidden and (layer is None or p[1] == layer)
            expected = {p: value for p, value in e.document.blocks.items() if visible(p) and
                        any(not visible(add(p,d)) or e.document.get(add(p,d)) != STONE for d in DIRECTIONS)}
            self.assertEqual(expected, preview_cells(e.document, hidden=hidden, layer=layer, focus=focus))

    def test_thin_landmarks_and_material_aux_keep_exact_far_coordinates(self):
        doc = Document((64,100,64))
        for i in range(64):
            doc.blocks[(i,0,63)] = ('minecraft:concrete', i%16)
        doc.blocks[(63,99,0)] = GLASS
        self.assertEqual(dict(doc.blocks.items()), preview_cells(doc))

    def test_selection_fields_and_two_click_box_drive_same_batch_scope(self):
        s = Session(Bridge()); s.editor = Editor(Document((8,8,8)))
        s.set_editor('end',(3,3,3)); self.assertEqual(64,len(s.editor.selection))
        s.choose_tool('fill'); s.choose_mode('box')
        s.point_action((1,1,1)); self.assertEqual({(1,1,1)},s.editor.selection)
        self.assertFalse(s.run())
        s.point_action((2,2,2)); self.assertEqual(8,len(s.editor.selection))
        self.assertEqual((1,1,1),s.editor.start)
        s.run(); self.assertEqual(8,len(s.editor.document.blocks))
        s.choose_tool('checker'); self.assertEqual(8,len(s.editor.selection))
        s.action(s.editor.run,'select_all'); self.assertEqual((7,7,7),s.editor.end)
        before = (s.editor.start,s.editor.end,s.editor.selection)
        s.set_editor('end',(99,99,99)); self.assertEqual(before,(s.editor.start,s.editor.end,s.editor.selection))

    def test_filter_material_is_independent_of_replacement_source(self):
        e = Editor(Document((2,2,2))); e.material=STONE; e.run('fill')
        e.source=GLASS; e.filter_material=STONE; e.mask='material'; e.material=GLASS
        self.assertEqual(8,e.run('fill'))
        e.run('select_material'); self.assertEqual(8,len(e.selection))

    def test_grid_is_bounded_and_uses_same_current_layer_as_empty_picking(self):
        for origin,size in (((0,0,0),(64,100,64)),((32,68,32),(32,32,32))):
            lines = grid_lines(origin,size,origin[1])
            self.assertEqual(len(lines), size[0]+size[2]+2)
            self.assertEqual(list(range(origin[0],origin[0]+size[0]+1)),[a[0] for a,b in lines if a[0]==b[0]])
            for a,b in lines:
                self.assertEqual(origin[1],a[1]); self.assertEqual(a[1],b[1])
        self.assertEqual([],grid_lines((0,32,0),(32,32,32),0))
        self.assertEqual(((0.,5.),(10.,5.)),clip_line((-5,5),(15,5),10,10))
        self.assertIsNone(clip_line((-5,-5),(15,-5),10,10))

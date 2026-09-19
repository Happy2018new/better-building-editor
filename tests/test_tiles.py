import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import Document, Editor
from projection.session import Session
from projection.tiles import tile_edge
import projection.tiles as tiles
from projection.large_preview import build_preview
from projection.chunks import painter_order
import math
import itertools


def cells(palette):
    return {(material, index) for material, values in palette.common.items() for index in values}


def scene_cells(session):
    result = set()
    dx, unused, dz = session.editor.document.size
    for key in session.tiles.slots:
        part = session.tiles.parts[key]
        sx, unused, sz = part['size']
        ox, oy, oz = part['origin']
        for material, values in part['data'].items():
            for index in values:
                x, y, z = index//sz%sx+ox, index//(sx*sz)+oy, index%sz+oz
                result.add((material,y*dx*dz+x*dz+z))
    return result


class Bridge:
    def __init__(self):
        self.queue, self.builds = [], []
    def later(self, delay, callback):
        self.queue.append(callback)
    def geometry(self, palette, name=None):
        self.builds.append((name, cells(palette)))
        return name if palette.common else None
    def settle(self, session):
        for _ in range(10000):
            for part in session.tiles.parts.values():
                part['pending'] = False
            if not self.queue:
                return
            self.queue.pop(0)()
        raise AssertionError('preview did not settle')


class TileTests(unittest.TestCase):
    def test_painter_order_agrees_with_ray_traversal_and_is_stable_within_octant(self):
        keys = list(itertools.product(range(4), range(8), range(4)))
        for signs in itertools.product((-1,1), repeat=3):
            toward = tuple(signs[i]*v for i,v in enumerate((.31,.77,.42)))
            order = painter_order(keys,toward)
            self.assertEqual(order,painter_order(keys,tuple(signs[i]*v for i,v in enumerate((.8,.1,.9)))))
            for center in ((1.5,3.5,1.5),(.3,6.7,2.9),(3.9,.1,.2)):
                visited = []
                for step in range(-200,201):
                    point = tuple(center[i]+step*.05*toward[i] for i in range(3))
                    key = tuple(int(math.floor(v)) for v in point)
                    if key in order and (not visited or visited[-1] != key):
                        visited.append(key)
                # Marching toward the observer must only move forward in depth.
                ranks = [order[key] for key in visited]
                self.assertEqual(sorted(ranks),ranks)

    def test_tile_budget_includes_maximum_dimensions(self):
        for size in ((24,16,24), (23,15,21), (64,100,64)):
            edge = tile_edge(size)
            self.assertLessEqual(((size[0]+edge-1)//edge)*((size[1]+edge-1)//edge)*((size[2]+edge-1)//edge), 128)

    def test_partitioned_surface_matches_whole_surface_including_halo_and_filters(self):
        doc = Document((19,18,17))
        e = Editor(doc); e.run('fill')
        # A hole across a tile boundary must expose a face in the neighbour.
        doc.blocks.pop((8, 7, 7)); doc.blocks[(9,7,7)] = ('minecraft:glass',0)
        for hidden, layer, plane in (((),None,None), ((3,4),None,None), ((),8,None),
                                      ((),None,((1.,0.,0.),8.5))):
            whole = cells(list(build_preview(doc,hidden,layer,None,plane))[-1][0])
            parts = set()
            for x in range(0,19,8):
                for y in range(0,18,8):
                    for z in range(0,17,8):
                        part = list(build_preview(doc,hidden,layer,None,plane,((x,y,z),(x+8,y+8,z+8))))[-1][0]
                        self.assertFalse(parts & cells(part))
                        parts.update(cells(part))
            self.assertEqual(whole,parts)

    def test_burst_updates_local_tiles_retains_other_meshes_and_has_individual_undo(self):
        b = Bridge(); s = Session(b)
        s._loaded(Document((24,16,24)))
        s.editor.select_box((0,0,0),(23,0,23)); s.editor.run('fill')
        s.refresh_preview(); b.settle(s)
        before = dict(s.tiles.parts)
        builds = len(b.builds)
        s.choose_mode('place')
        calls = []; s.subscribe(lambda: calls.append('root'), ())
        for y in range(1,7):
            s.point_action((3,y-1,3),(0,1,0))
        self.assertEqual([], calls)
        self.assertEqual(582,len(s.editor.document.blocks))
        b.settle(s)
        self.assertEqual(builds+1,len(b.builds))
        self.assertEqual(1,len(calls))
        self.assertTrue(all(p is before[k] for k,p in s.tiles.parts.items() if k!=(0,0,0)))
        self.assertEqual(cells(list(build_preview(s.editor.document))[-1][0]), scene_cells(s))
        self.assertEqual(4,len(s.tiles.slots))
        for _ in range(6): s.action(s.editor.undo)
        b.settle(s)
        self.assertEqual(576,len(s.editor.document.blocks))

    def test_pending_upload_is_never_overwritten_by_next_edit(self):
        b = Bridge(); s = Session(b); s._loaded(Document((8,8,8))); b.settle(s)
        s.choose_mode('place'); s.point_action((3,0,3)); b.settle(s)
        part = s.tiles.parts[(0,0,0)]; part['pending'] = True
        builds = len(b.builds)
        s.point_action((3,0,3),(0,1,0))
        s.tiles.advance()
        self.assertEqual(builds,len(b.builds))
        part['pending'] = False; b.settle(s)
        self.assertEqual(builds+1,len(b.builds))
        self.assertNotEqual(part['name'],s.tiles.parts[(0,0,0)]['name'])

    def test_rapid_overview_edits_do_not_publish_blocking_progress(self):
        b = Bridge(); s = Session(b); s._loaded(Document((25,64,25)))
        b.settle(s); s.toggle_preview_detail()
        self.assertTrue(s.tiles.report_progress)
        b.settle(s)
        notifications = []
        original = s.emit
        def observed(field=None):
            if field == 'preview_status':
                notifications.append(field)
            original(field)
        s.emit = observed
        s.choose_mode('place')
        for y in range(41):
            s.point_action((12,max(0,y-1),12),(0,int(y>0),0))
            b.settle(s)
            self.assertFalse(s.tiles.report_progress)
        self.assertEqual(41,len(s.editor.document.blocks))
        self.assertEqual([],notifications)

    def test_clipping_boundary_rebuilds_exposed_neighbours_and_retains_far_tiles(self):
        b = Bridge(); s = Session(b); s._loaded(Document((24,32,24)))
        s.editor.run('fill'); s.refresh_preview(); b.settle(s)
        for mode, layer in (('section', 15), ('section', 16), ('single', 8), ('full', 8)):
            s.editor.layer = layer; s.display_mode(mode); b.settle(s)
            actual = scene_cells(s)
            expected = cells(list(build_preview(s.editor.document, s.preview_hidden(),
                layer if s.solo_layer else None))[-1][0])
            self.assertEqual(expected, actual, (mode,layer))
        before = len(b.builds)
        s.camera_pose = (0,0,1); s.move_depth(1); b.settle(s)
        self.assertEqual(before,len(b.builds))
        actual = scene_cells(s)
        self.assertEqual(cells(list(build_preview(s.editor.document,plane=s.depth_plane()))[-1][0]), actual)

    def test_native_palettes_are_at_most_4096_cells_and_128_pairs(self):
        for size in ((24,16,24),(64,96,64),(64,128,64)):
            edge=tile_edge(size)
            count=((size[0]+edge-1)//edge)*((size[1]+edge-1)//edge)*((size[2]+edge-1)//edge)
            self.assertLessEqual(count,128)
            self.assertEqual(16,edge)

    def test_large_default_focus_uses_one_exact_chunk_and_undo_reuses_mesh(self):
        b = Bridge(); s = Session(b); s._loaded(Document((64,128,64)))
        self.assertTrue(s.preview_detail)
        s.editor.run('fill'); s.refresh_preview(); b.settle(s)
        self.assertEqual((16,16,16),s.scene_size)
        self.assertEqual(((0,0,0),),s.tiles.slots)
        s.focus_preview((63,127,63)); b.settle(s)
        self.assertEqual((48,112,48),s.scene_origin)
        s.choose_mode('erase');s.erase_scope='single';s.point_action((63,127,63));b.settle(s)
        builds=len(b.builds)
        s.action(s.editor.undo);b.settle(s)
        self.assertEqual(builds,len(b.builds))
        self.assertEqual(524288,len(s.editor.document.blocks))

    def test_wide_flat_draft_also_opens_in_a_full_scale_chunk(self):
        b = Bridge(); s = Session(b); s._loaded(Document((64,1,64))); b.settle(s)
        self.assertTrue(s.preview_detail)
        self.assertEqual((16,1,16),s.scene_size)
        s.toggle_preview_detail(); b.settle(s)
        self.assertEqual((64,1,64),s.scene_size)
        s.focused = (63,0,63); s.locate_selected(); b.settle(s)
        self.assertEqual((48,0,48),s.scene_origin)

    def test_return_to_overview_reuses_unchanged_surface_extraction(self):
        b = Bridge(); s = Session(b); s._loaded(Document((48,32,32)))
        s.editor.run('fill'); s.toggle_preview_detail(); b.settle(s)
        expected = scene_cells(s)
        s.focus_preview((0,0,0)); b.settle(s)
        original, calls = tiles.build_preview, []
        def counted(*args):
            calls.append(args[-2])
            return original(*args)
        try:
            tiles.build_preview = counted
            s.toggle_preview_detail(); b.settle(s)
        finally:
            tiles.build_preview = original
        self.assertEqual(1,len(calls))
        self.assertEqual(expected,scene_cells(s))

    def test_surface_budget_applies_across_tiles_and_preserves_draft(self):
        budget = tiles.MAX_SURFACE_BLOCKS
        try:
            tiles.MAX_SURFACE_BLOCKS = 100
            b = Bridge(); s = Session(b)
            s._loaded(Document((24,1,8)))
            s.editor.run('fill'); s.refresh_preview(); b.settle(s)
            self.assertEqual(192, len(s.editor.document.blocks))
            self.assertTrue(s.preview_error)
            self.assertFalse(s.preview_pending)
            self.assertLessEqual(sum(p['count'] for p in s.tiles.parts.values()),100)
        finally:
            tiles.MAX_SURFACE_BLOCKS = budget


if __name__ == '__main__': unittest.main()

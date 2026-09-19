import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import Document, Editor
from projection.session import Session
from projection.tiles import tile_edge
import projection.tiles as tiles
from projection.large_preview import build_preview


def cells(palette):
    return {(material, index) for material, values in palette.common.items() for index in values}


def scene_cells(session):
    return {(material,index) for part in session.tiles.parts.values() for material,values in part['data'].items() for index in values}


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
    def test_tile_budget_includes_maximum_dimensions(self):
        for size in ((24,16,24), (23,15,21), (256,384,256)):
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
        before = dict((k,p['name']) for k,p in s.tiles.parts.items())
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
        self.assertTrue(all(p['name']==before[k] for k,p in s.tiles.parts.items() if k!=(0,0,0)))
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

    def test_clipping_boundary_rebuilds_exposed_neighbours_and_retains_far_tiles(self):
        b = Bridge(); s = Session(b); s._loaded(Document((24,32,24)))
        s.editor.run('fill'); s.refresh_preview(); b.settle(s)
        for mode, layer in (('section', 15), ('section', 16), ('single', 8), ('full', 8)):
            s.editor.layer = layer; s.display_mode(mode); b.settle(s)
            actual = scene_cells(s)
            expected = cells(list(build_preview(s.editor.document, s.preview_hidden(),
                layer if s.solo_layer else None))[-1][0])
            self.assertEqual(expected, actual, (mode,layer))
        before = dict((key,p['name']) for key,p in s.tiles.parts.items())
        s.camera_pose = (0,0,1); s.move_depth(1); b.settle(s)
        self.assertTrue(all(p['name'] == before[key] for key,p in s.tiles.parts.items() if key[2] == 0))
        actual = scene_cells(s)
        self.assertEqual(cells(list(build_preview(s.editor.document,plane=s.depth_plane()))[-1][0]), actual)

    def test_native_declared_volume_is_bounded_as_documents_grow(self):
        for size in ((24,16,24),(64,96,64),(128,128,128),(256,384,256)):
            edge=tile_edge(size)
            count=((size[0]+edge-1)//edge)*((size[1]+edge-1)//edge)*((size[2]+edge-1)//edge)
            self.assertLessEqual(count*size[0]*size[1]*size[2],32*1024*1024)
        self.assertEqual(512,tile_edge((256,384,256)))

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

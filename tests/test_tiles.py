import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import AIR, Document, Editor
from projection.session import Session
from projection.tiles import tile_edge
import projection.tiles as tiles
from projection.large_preview import build_preview, is_opaque
from projection.camera import behind_plane
from projection.chunks import painter_order
import math
import itertools
import time
import random
from unittest.mock import patch


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
    def test_mixed_chunk_surface_matches_voxel_oracle_with_holes_and_clipping(self):
        rng = random.Random(47)
        doc = Document((19,18,17))
        materials = (('minecraft:stone',0), ('minecraft:glass',0), AIR)
        for pos in itertools.product(range(19),range(18),range(17)):
            value = materials[0 if rng.random() < .85 else rng.randrange(3)]
            if value != AIR: doc.blocks[pos] = value
        for hidden, layer, plane in (((),None,None), ((6,),None,None), ((),8,None),
                                     ((),None,((.6,.4,.3),17.2))):
            def visible(pos):
                return (doc.contains(pos) and pos[1] not in hidden and
                        (layer is None or pos[1] == layer) and behind_plane(pos,plane))
            expected = set()
            for pos, value in doc.blocks.items():
                if not visible(pos): continue
                neighbors = [tuple(pos[i]+offset[i] for i in range(3)) for offset in
                             ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))]
                if not all(visible(p) and is_opaque(doc.get(p)) for p in neighbors):
                    expected.add((value,pos[1]*19*17+pos[0]*17+pos[2]))
            actual = cells(list(build_preview(doc,hidden,layer,None,plane))[-1][0])
            self.assertEqual(expected,actual)

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

    def test_undo_branch_cannot_reuse_a_mesh_for_another_palette_material(self):
        b=Bridge(); s=Session(b); s.editor=Editor(Document((32,32,32)))
        s.refresh_preview(); b.settle(s)
        s.editor.material=('minecraft:stone',0)
        s.action(s.editor.run,'fill'); b.settle(s)
        s.action(s.editor.undo); b.settle(s)
        s.editor.material=('minecraft:gold_block',0)
        s.action(s.editor.run,'fill'); b.settle(s)
        self.assertTrue(scene_cells(s))
        self.assertEqual({('minecraft:gold_block',0)},{material for material,index in scene_cells(s)})

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
        s.subscribe(lambda: calls.append('point_edit'), ('point_edit',))
        for y in range(1,7):
            s.point_action((3,y-1,3),(0,1,0))
        self.assertEqual([], calls)
        self.assertEqual(582,len(s.editor.document.blocks))
        b.settle(s)
        self.assertEqual(builds+1,len(b.builds))
        self.assertEqual(['point_edit'], calls)
        self.assertTrue(all(p is before[k] for k,p in s.tiles.parts.items() if k!=(0,0,0)))
        self.assertEqual(cells(list(build_preview(s.editor.document))[-1][0]), scene_cells(s))
        self.assertEqual(4,len(s.tiles.slots))
        for _ in range(6): s.action(s.editor.undo)
        b.settle(s)
        self.assertEqual(576,len(s.editor.document.blocks))

    def test_live_point_edits_wait_briefly_and_share_one_upload(self):
        class LiveBridge(Bridge):
            def next_frame(self, callback):
                self.queue.append(callback)

        b = LiveBridge(); s = Session(b)
        s._loaded(Document((8, 8, 8))); b.settle(s)
        s.touch_mode = True
        s.choose_mode('place')
        with patch.object(tiles.time, 'time', return_value=100.):
            self.assertTrue(s.point_action((3, 0, 3)))
            b.queue.pop(0)()
            self.assertFalse(b.builds)
            self.assertTrue(s.point_action((3, 0, 3), (0, 1, 0)))
            self.assertFalse(b.builds)
        b.settle(s)
        self.assertEqual(2, len(s.editor.document.blocks))
        self.assertEqual(1, len(b.builds))
        self.assertFalse(s.tiles.report_progress)

    def test_reload_reuses_identical_meshes_and_updates_changed_content(self):
        b = Bridge(); s = Session(b)
        doc = Document((32, 16, 16))
        doc.blocks[(3, 0, 3)] = ('minecraft:stone', 0)
        doc.blocks[(20, 0, 3)] = ('minecraft:stone', 0)
        s._loaded(doc); b.settle(s)
        builds, extractions = len(b.builds), s.tiles.extractions
        # Deserialize into independent arrays, as a real configuration load does.
        s._loaded(Document.from_data(doc.to_data())); b.settle(s)
        self.assertEqual(builds, len(b.builds))
        self.assertEqual(extractions, s.tiles.extractions)
        self.assertEqual(cells(list(build_preview(doc))[-1][0]), scene_cells(s))
        changed = Document.from_data(doc.to_data())
        changed.blocks[(3, 0, 3)] = ('minecraft:gold_block', 0)
        s._loaded(changed); b.settle(s)
        self.assertEqual(builds+1, len(b.builds))
        self.assertEqual(cells(list(build_preview(changed))[-1][0]), scene_cells(s))
        s._loaded(Document((32, 16, 16))); b.settle(s)
        self.assertFalse(scene_cells(s))

    def test_single_undo_is_local_and_does_not_broadcast_full_workspace(self):
        b = Bridge(); s = Session(b); s._loaded(Document((48,48,48))); b.settle(s)
        s.choose_mode('place'); s.point_action((20,20,20)); b.settle(s)
        calls = []
        s.subscribe(lambda: calls.append('root'), ())
        s.subscribe(lambda: calls.append('point'), ('point_edit',))
        self.assertTrue(s.action(s.editor.undo))
        self.assertEqual({(1,1,1)}, s.tiles.dirty)
        b.settle(s)
        self.assertEqual(['point'], calls)
        self.assertFalse(s.editor.document.blocks)
        self.assertTrue(s.action(s.editor.redo)); b.settle(s)
        self.assertEqual(1, len(s.editor.document.blocks))

    def test_selection_taps_are_immediate_without_mesh_work_or_full_refresh(self):
        for mode in ('browse', 'select', 'pick', 'box'):
            b = Bridge(); s = Session(b); s._loaded(Document((8,8,8))); b.settle(s)
            s.editor.document.blocks[(3,2,3)] = ('minecraft:gold_block', 0)
            s.choose_mode(mode)
            calls = []
            s.subscribe(lambda: calls.append('root'), ())
            s.subscribe(lambda: calls.append('point'), ('point_edit',))
            s.subscribe(lambda: calls.append('materials'), ('materials',))
            before = s.editor.revision, s.tiles.extractions, len(b.builds)
            self.assertTrue(s.point_action((3,2,3)))
            self.assertEqual((3,2,3), s.focused)
            self.assertEqual({(3,2,3)}, set(s.editor.selection))
            if mode == 'pick':
                self.assertEqual(('minecraft:gold_block', 0), s.editor.material)
                self.assertIn('materials', calls)
            if mode == 'box':
                self.assertTrue(s.point_action((4,3,4)))
                self.assertEqual(8, len(s.editor.selection))
                self.assertIsNone(s.box_anchor)
            b.settle(s)
            self.assertEqual(before, (s.editor.revision, s.tiles.extractions, len(b.builds)))
            self.assertEqual(1, calls.count('point'))
            self.assertNotIn('root', calls)

    def test_held_gesture_defers_mesh_work_and_notification_without_losing_edit(self):
        b = Bridge(); s = Session(b); s._loaded(Document((8,8,8))); b.settle(s)
        s.choose_mode('place'); s.point_action((3,0,3))
        calls = []; s.subscribe(lambda: calls.append(True), ('point_edit',))
        s.camera_dragging = True
        for callback in b.queue[:]:
            b.queue.remove(callback); callback()
        self.assertFalse(b.builds)
        self.assertFalse(calls)
        self.assertEqual(1, len(s.editor.document.blocks))
        s.camera_dragging = False; b.settle(s)
        self.assertEqual(1, len(b.builds))
        self.assertEqual([True], calls)

    def test_bulk_job_after_point_edit_invalidates_all_changed_chunks(self):
        from projection.jobs import EditJob
        b = Bridge(); s = Session(b); s._loaded(Document((32,32,32))); b.settle(s)
        s.choose_mode('place'); s.point_action((3,0,3)); b.settle(s)
        s.editor.select_box((0,0,0), (31,31,31))
        job = EditJob(s.editor, 'shell')
        while not job.done: job.step()
        s.refresh_preview(); b.settle(s)
        self.assertEqual(cells(list(build_preview(s.editor.document))[-1][0]), scene_cells(s))

    def test_pending_upload_is_never_overwritten_by_next_edit(self):
        b = Bridge(); s = Session(b); s._loaded(Document((8,8,8))); b.settle(s)
        s.choose_mode('place'); s.point_action((3,0,3)); b.settle(s)
        part = s.tiles.parts[(0,0,0)]; part['pending'] = True
        s.tiles.renderer_active = True
        s.tiles.last_render = time.time()
        builds = len(b.builds)
        s.point_action((3,0,3),(0,1,0))
        s.tiles.advance()
        self.assertEqual(builds,len(b.builds))
        part['pending'] = False; b.settle(s)
        self.assertEqual(builds+1,len(b.builds))
        self.assertNotEqual(part['name'],s.tiles.parts[(0,0,0)]['name'])

    def test_hidden_renderer_does_not_hold_build_and_cancelled_work_cannot_resume(self):
        b=Bridge();s=Session(b);s._loaded(Document((64,128,64)))
        s.editor.select_box((0,0,0),(63,0,63));s.editor.run('fill');s.refresh_preview()
        # No renderer acknowledgements: library/closed workspace still builds.
        for unused in range(1000):
            if not b.queue:break
            b.queue.pop(0)()
        self.assertFalse(s.preview_pending)
        self.assertEqual(16,len(s.tiles.render_keys))
        s.editor.select_box((0,1,0),(63,1,63));s.editor.run('fill');s.refresh_preview()
        s.tiles.cancel();before=len(b.builds)
        while b.queue:b.queue.pop(0)()
        self.assertEqual(before,len(b.builds))
        self.assertFalse(s.preview_pending)
        s.tiles.retry();b.settle(s)
        self.assertFalse(s.preview_error)
        self.assertEqual(cells(list(build_preview(s.editor.document))[-1][0]),scene_cells(s))

    def test_rapid_overview_edits_do_not_publish_blocking_progress(self):
        b = Bridge(); s = Session(b); s._loaded(Document((25,64,25)))

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

    def test_full_building_uses_independent_tiles_and_undo_reuses_mesh(self):
        b=Bridge();s=Session(b);s._loaded(Document((64,128,64)))
        s.editor.run('fill');s.refresh_preview();b.settle(s)
        self.assertEqual((64,128,64),s.scene_size)
        self.assertEqual(128,len(s.tiles.slots))
        s.choose_mode('erase');s.erase_scope='single';s.point_action((63,127,63));b.settle(s)
        builds=len(b.builds);extractions=s.tiles.extractions;s.action(s.editor.undo);b.settle(s)
        self.assertEqual(builds,len(b.builds))
        self.assertEqual(extractions,s.tiles.extractions)
        self.assertEqual(524288,len(s.editor.document.blocks))

    def test_camera_focus_never_extracts_or_clips_geometry(self):
        b=Bridge();s=Session(b);s._loaded(Document((64,1,64)))
        s.editor.run('fill');s.refresh_preview();b.settle(s)
        before=scene_cells(s);builds=len(b.builds)
        s.focused=(63,0,63);s.locate_selected();b.settle(s)
        self.assertEqual((64,1,64),s.scene_size)
        self.assertEqual(before,scene_cells(s))
        self.assertEqual(builds,len(b.builds))

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

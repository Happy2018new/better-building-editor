"""Large documents must stay compact, atomic, serializable and cancellable."""
import json
import sys
import unittest
import zlib
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import AIR, Document, Editor, bounds
from projection.storage import BlockStore, Selection, FULL
from projection.jobs import EditJob
from projection.catalog import TOOLS
from projection.transfer import Receiver, packets
from projection.large_preview import build_preview
from projection.journal import Journal
from projection.archive import save_steps, load_steps
from projection.codec import encode_chunk
from array import array
from projection.world import WorldJob
from test_world import World

STONE = ('minecraft:stone', 0)
WOOD = ('minecraft:planks', 1)
SIZE = (64, 100, 64)


class LargeEditorTests(unittest.TestCase):
    def test_axis_shapes_match_cell_oracle_with_irregular_selection_and_masks(self):
        for tool in ('shell', 'walls', 'frame', 'floor'):
            for thickness in (1, 3, 12):
                e = Editor(Document((64, 128, 64)))
                e.select_box((13, 14, 13), (19, 21, 19))
                e.selection = e.selection.difference(Selection.box((15, 15, 15), (17, 17, 17)))
                e.thickness = thickness
                e.material = STONE
                e.document.blocks[(13, 14, 13)] = WOOD
                e.locked_layers.add(16)
                e.mask = 'air'
                expected = {p:v for p,v in e._shape(tool, *e.selection.bounds()).items() if e._writable(p)}
                before = dict(e.document.blocks.items())
                e.run(tool)
                before.update(expected)
                self.assertEqual(before, dict(e.document.blocks.items()), (tool,thickness))
                e.undo()
                self.assertEqual({(13, 14, 13):WOOD}, dict(e.document.blocks.items()))

    def test_thin_maximum_shell_skips_air_volume_and_preserves_cancel(self):
        e = Editor(Document((64,128,64)));e.thickness=1
        job=EditJob(e,'shell');job.step(budget=2,seconds=1)
        self.assertEqual(39944,job.total)
        self.assertFalse(e.document.blocks)
        job.cancel();job.step();self.assertFalse(e.undo_stack)
        self.assertEqual(39944,e.run('shell'))
        self.assertEqual(AIR,e.document.get((32,64,32)))
        self.assertEqual(e.material,e.document.get((63,127,63)))

    def test_mixed_archive_pages_roundtrip_and_incomplete_archive_rejected(self):
        class Pages:
            def __init__(self):
                self.pages = {}
            def save_archive_page(self, identity, part, value):
                self.pages[(identity, part)] = json.loads(json.dumps(value))
                return True
            def load_archive_page(self, identity, part):
                return self.pages.get((identity, part))
        d = Document(SIZE)
        for key in [(x, y, z) for x in range(4) for y in range(3) for z in range(4)]:
            d.blocks.fill_chunk(key, STONE)
            d.blocks[tuple(v*16 for v in key)] = WOOD
        pages = Pages()
        metadata = [v for v in save_steps(pages, d, 9) if v is not None][0]
        self.assertGreater(metadata['parts'], 1)
        self.assertLess(max(len(json.dumps(p)) for p in pages.pages.values()), 140000)
        metadata['name'] = '重命名配置'
        restored = [v for v in load_steps(pages, 9, metadata) if v is not None][0]
        self.assertEqual(d.blocks, restored.blocks)
        self.assertEqual('重命名配置', restored.name)
        del pages.pages[(9, 0)]
        with self.assertRaises(ValueError):
            list(load_steps(pages, 9, metadata))

    def test_corrupt_compressed_chunks_and_duplicate_empty_chunks_rejected(self):
        d = Document(SIZE)
        d.blocks[(0, 0, 0)] = STONE
        data = d.to_data()
        packed = base64.b64decode(data['chunks'][0][3])
        data['chunks'][0][3] = base64.b64encode(packed[:-2]).decode('ascii')
        with self.assertRaises(ValueError):
            Document.from_data(data)
        empty = encode_chunk((0, 0, 0), array('H', [0]) * 4096)
        data = Document(SIZE).to_data()
        data['chunks'] = [empty, empty]
        with self.assertRaises(ValueError):
            Document.from_data(data)

    def test_large_world_source_is_lazy_and_chunk_wait_preserves_first_cell(self):
        e = Editor(Document(SIZE)); e.material = STONE; e.run('fill')
        world = World()
        world.unloaded.add((0, 0, 0))
        world.ensure = lambda pos: None
        job = WorldJob(world, e.document, (0, 0, 0))
        self.assertEqual(0, len(job.plan))
        job.step(8)
        self.assertEqual(0, job.cursor)
        self.assertEqual(0, world.writes)
        world.unloaded.clear()
        job.step(8)
        self.assertEqual(8, len(job.plan))
        self.assertEqual((0, 0, 0), job.plan[0][0])
        job.fail('cancelled'); job.step()
        self.assertTrue(job.done)
        self.assertEqual(0, world.writes)

    def test_running_edit_keeps_original_lock_snapshot(self):
        e = Editor(Document(SIZE)); e.locked_layers.add(0)
        e.select_box((0, 0, 0), (15, 15, 15))
        job = EditJob(e, 'fill')
        e.locked_layers.clear()
        while not job.done:
            job.step()
        self.assertEqual(3840, len(e.document.blocks))
        self.assertEqual(0, e.document.layer_count(0))

    def test_full_world_height_fill_undo_redo_and_compact_config(self):
        e = Editor(Document(SIZE))
        self.assertEqual(409600, len(e.selection))
        self.assertEqual(112, len(e.selection.chunks))
        e.material = STONE
        self.assertEqual(409600, e.run('fill'))
        self.assertTrue(all(isinstance(c, int) for k,c in e.document.blocks.chunks.items() if k[1]<6))
        self.assertLess(e.document.blocks.memory_bytes(), 1024 * 1024)
        self.assertEqual([(STONE, 409600)], e.document.materials())
        self.assertEqual(4096, e.document.layer_count(99))
        payload = e.document.to_data()
        encoded = json.dumps(payload)
        self.assertLess(len(encoded), 200000)
        restored = Document.from_data(json.loads(encoded))
        self.assertEqual(e.document.blocks, restored.blocks)
        self.assertEqual(STONE, restored.get((63, 99, 63)))
        self.assertTrue(e.undo())
        self.assertEqual(0, len(e.document.blocks))
        self.assertTrue(e.redo())
        self.assertEqual(409600, len(e.document.blocks))
        e.paint_at((63, 99, 63), True)
        self.assertEqual(409599, len(e.document.blocks))
        self.assertEqual(STONE, restored.get((63, 99, 63)))
        e.undo()
        self.assertEqual(STONE, e.document.get((63, 99, 63)))

    def test_job_is_atomic_and_cancel_does_not_create_history(self):
        e = Editor(Document(SIZE))
        job = EditJob(e, 'fill')
        job.step(budget=4)
        self.assertFalse(job.done)
        self.assertEqual(0, len(e.document.blocks))
        job.cancel(); job.step()
        self.assertTrue(job.done)
        self.assertEqual([], e.undo_stack)
        self.assertEqual(0, e.revision)

    def test_select_air_invert_and_uniform_rotation(self):
        e = Editor(Document(SIZE))
        e.select_box((0, 0, 0), (31, 31, 31))
        e.material = STONE; e.run('fill')
        e.run('select_air')
        self.assertEqual(409600 - 32768, len(e.selection))
        e.run('select_invert')
        self.assertEqual(((0, 0, 0), (31, 31, 31)), bounds(e.selection))
        e.run('select_all')
        e.run('rotate_y90')
        self.assertEqual(STONE, e.document.get((63, 0, 0)))
        self.assertEqual(AIR, e.document.get((0, 0, 0)))
        self.assertEqual(32768, len(e.document.blocks))
        e.undo()
        self.assertEqual(STONE, e.document.get((0, 0, 0)))

    def test_all_tools_on_local_selection_in_large_document(self):
        for tool, group, unused, unused2 in TOOLS:
            if group == 'select' and tool != 'select_box':
                continue  # Whole-volume predicates have dedicated compact tests.
            e = Editor(Document(SIZE))
            e.select_box((3, 3, 3), (6, 6, 6))
            e.material = STONE; e.run('fill'); e.run('copy')
            e.start, e.end, e.layer = (3, 3, 3), (6, 6, 6), 4
            e.run(tool)
            self.assertTrue(all(e.document.contains(p) for p in e.document.blocks), tool)

    def test_mixed_chunk_round_trip_and_copy_on_write_statistics(self):
        d = Document((33, 33, 33), {(0, 0, 0): STONE, (32, 32, 32): WOOD})
        frozen = d.blocks.copy()
        d.blocks[(1, 0, 0)] = WOOD
        self.assertNotIn((1, 0, 0), frozen)
        other = Document.from_data(json.loads(json.dumps(d.to_data())))
        self.assertEqual(d.blocks, other.blocks)
        self.assertEqual(d.materials(), other.materials())
        self.assertEqual(2, other.layer_count(0))
        bad = d.to_data(); bad['chunks'].append(bad['chunks'][0])
        with self.assertRaises(ValueError):
            Document.from_data(bad)

    def test_selection_crosses_chunk_edges_without_extra_cells(self):
        s = Selection.box((14, 15, 13), (17, 18, 19))
        self.assertEqual(4 * 4 * 7, len(s))
        self.assertEqual(len(s), len(set(s)))
        self.assertNotIn((18, 18, 19), s)
        s._bounds = None
        self.assertEqual(((14, 15, 13), (17, 18, 19)), s.bounds())

    def test_bounded_packets_round_trip_and_reject_missing_reordered_duplicate(self):
        e = Editor(Document(SIZE))
        e.run('fill')
        data = list(packets(e.document))
        self.assertGreater(len(data), 3)
        self.assertLess(max(len(json.dumps(p)) for p in data), 20000)
        receiver = Receiver()
        for packet in data:
            receiver.feed(packet)
        self.assertEqual(e.document.blocks, receiver.result.blocks)
        for sequence in (data[1:], data[:2] + data[1:], data[:-2] + data[-1:]):
            receiver = Receiver()
            with self.assertRaises(ValueError):
                for packet in sequence:
                    receiver.feed(packet)

    def test_preview_is_bounded_and_detail_preserves_exact_coordinate(self):
        e = Editor(Document(SIZE))
        e.run('fill')
        overview = [v for v in build_preview(e.document) if v is not None][0]
        self.assertEqual(SIZE, overview[0].size)
        self.assertEqual(64*100*64 - 62*98*62, overview[0].count)
        self.assertEqual(1, overview[2])
        e.material = WOOD
        e.paint_at((63, 99, 63))
        detail = [v for v in build_preview(e.document, focus=(63, 99, 63)) if v is not None][0]
        self.assertEqual((48, 96, 48), detail[1])
        self.assertIn(1023, detail[0].common[WOOD])
        self.assertEqual(1, detail[2])

    def test_compressed_world_journal_supports_rollback_order(self):
        journal = Journal()
        for i in range(10000):
            journal.append(((i % 256, i // 256, 0), AIR, STONE))
        self.assertEqual(10000, len(journal))
        self.assertEqual(((9999 % 256, 9999 // 256, 0), AIR, STONE), journal[-1])
        self.assertEqual(((0, 0, 0), AIR, STONE), journal[0])
        self.assertLess(journal.memory_bytes(), 100000)

    def test_atomic_failure_and_mask_on_large_fill(self):
        e = Editor(Document(SIZE))
        e.select_box((0, 0, 0), (15, 15, 15))
        e.locked_layers.add(0)
        self.assertEqual(3840, e.run('fill'))
        self.assertEqual(0, e.document.layer_count(0))
        e.mask = 'air'
        self.assertEqual(0, e.run('fill'))
        e.locked_layers.clear(); e.mask = 'all'; e.run('copy')
        e.start = (63, 99, 63)
        before = e.document.to_data()
        with self.assertRaises(ValueError):
            e.run('paste')
        self.assertEqual(before, e.document.to_data())


if __name__ == '__main__':
    unittest.main()

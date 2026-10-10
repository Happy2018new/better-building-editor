"""Known F10 gap: missing-only tessellation loses occupied neighbor context.

These expected failures describe palette inputs, not native visual outcomes.
Remove the decorators when a generic context-preserving renderer is implemented.
"""
import unittest
from types import SimpleNamespace

from test_occupancy_review import Runtime, STONE
from modern_projection.projection import block_registry as registry
from modern_projection.projection.cell import make_cell
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.large_preview import SurfacePalette
from modern_projection.projection.model import Document
from modern_projection.projection.occupancy import ProjectionOccupancy
from modern_projection.projection.occupancy_initial import prepare_chunk
from modern_projection.projection.visible_actor import compose_actor


class MissingOnlyNeighborContextKnownGapTests(unittest.TestCase):
    def fixture(self):
        base, corner, chest_pos = (15, 1, 8), (16, 1, 8), (14, 1, 8)
        stair = lambda direction: registry.from_states('minecraft:oak_stairs', {
            'weirdo_direction': direction, 'upside_down_bit': False})
        water = ('minecraft:water', 0)
        chest = registry.from_states('minecraft:chest', {
            'minecraft:cardinal_direction': 'north'})
        render = {'chestIsLargeChest': False}
        nbt = {'id': {'__type__': 8, '__value__': 'Chest'}}
        document = Document((32, 16, 16), {
            base: make_cell(stair(0), water),
            corner: make_cell(stair(3), water),
            chest_pos: make_cell(chest, water, compose_actor(render, nbt)),
        })
        runtime, origin = Runtime(), (100, 64, 100)
        for pos in (corner, chest_pos):
            runtime.world[tuple(origin[i] + pos[i] for i in range(3))] = STONE
        session = SimpleNamespace(editor=SimpleNamespace(document=document, layer=None),
                                  preview_hidden=lambda: (), solo_layer=False)
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime,
                                 level='level', projection_serial=1,
                                 projection_occupancy=None)
        tracker = ProjectionOccupancy(bridge, origin)
        return document, tracker, base, corner, chest_pos, render

    def native(self, source):
        return prepare_palette(source.palette_data())

    def test_complete_context_control_preserves_stairs_water_and_actor(self):
        document, tracker, base, corner, chest, render = self.fixture()
        data = self.native(document)
        indices = {tracker.index(pos) for pos in (base, corner, chest)}
        self.assertEqual(indices, {index for group in data['common'].values()
                                   for index in group})
        self.assertEqual(indices, set(data['extra'][('minecraft:water', 0)]))
        self.assertEqual({'minecraft:chest': {tracker.index(chest): render}}, data['actor'])
        self.assertNotIn('nbt', data['actor']['minecraft:chest'][tracker.index(chest)])

    @unittest.expectedFailure
    def test_small_initial_palette_retains_full_native_context(self):
        document, tracker, unused, unused2, unused3, unused4 = self.fixture()
        # This is the same document.palette_data(visible) path used by bridge.
        actual = prepare_palette(document.palette_data(tracker.initial_visible))
        self.assertEqual(self.native(document), actual)

    @unittest.expectedFailure
    def test_chunk_initial_palette_retains_full_native_context(self):
        document, tracker, unused, unused2, unused3, unused4 = self.fixture()

        def begin(key):
            size = tuple(min(16, document.size[i] - key[i] * 16) for i in range(3))
            values = bytearray([1]) * (size[0] * size[1] * size[2])
            for pos in document.blocks:
                if tuple(axis >> 4 for axis in pos) != key:
                    continue
                world = tuple(tracker.origin[i] + pos[i] for i in range(3))
                if world in tracker.bridge.system.world:
                    local = tuple(pos[i] - key[i] * 16 for i in range(3))
                    values[(local[1] * size[0] + local[0]) * size[2] + local[2]] = 2
            tracker.bulk.initial = (key, (values, size))

        tracker.bulk.begin = begin
        output = SurfacePalette(document.size)
        for key in sorted(document.blocks.chunks):
            size = tuple(min(16, document.size[i] - key[i] * 16) for i in range(3))
            for unused in prepare_chunk(tracker, document.blocks, key, size, output):
                pass
        self.assertEqual(set(document.blocks), set(tracker.targets))
        self.assertEqual(self.native(document), self.native(output))

    @unittest.expectedFailure
    def test_dynamic_rebuild_retains_full_native_context(self):
        document, tracker, unused, unused2, unused3, unused4 = self.fixture()
        runtime = tracker.bridge.system
        occupied = dict(runtime.world)
        runtime.world.clear()
        for pos in document.blocks:
            tracker.initial_visible(pos)
        tracker.rendered = tracker.state[:]
        runtime.world.update(occupied)
        for pos in document.blocks:
            tracker.read(pos)
        tracker.snapshot = tracker.state[:]
        tracker.output = SurfacePalette(document.size)
        for unused in tracker.prepare():
            pass
        self.assertEqual(set(document.blocks), set(tracker.document.blocks))
        self.assertEqual(self.native(document), self.native(tracker.output))


if __name__ == '__main__':
    unittest.main()

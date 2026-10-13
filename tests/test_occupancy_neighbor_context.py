"""Production F10 entrypoints retain hidden native neighbors in one mesh."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_bridge
from test_occupancy_review import Runtime, STONE
from modern_projection.projection import block_registry as registry
from modern_projection.projection.cell import make_cell
from modern_projection.projection.geometry_palette import prepare_palette
from modern_projection.projection.large_preview import SurfacePalette
from modern_projection.projection.model import Document
from modern_projection.projection.occupancy import ProjectionOccupancy
from modern_projection.projection.world_projection import WorldProjection
from modern_projection.projection.visible_actor import compose_actor
from modern_projection.projection.bridge import ClientBridge
from modern_projection.projection.render_context import ContextPaletteBuilder
from modern_projection.projection.plant_position import POSITION_PLANT_PROXIES
from modern_projection.projection.render_layout import (context_center, context_position,
                                                        logical_position, native_mesh_position)
from modern_projection.projection.render_layout import (local_context_center, local_context_position,
                                                        local_context_logical)


class MissingOnlyNeighborContextTests(unittest.TestCase):
    def test_world_and_dynamic_preparation_resolve_destination_plant_cells(self):
        document, tracker, base, corner, unused, unused2 = self.fixture()
        legacy = ('minecraft:red_flower', 0)
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        document.blocks[base] = legacy
        document.blocks[corner] = make_cell(snow, legacy)
        tracker.bridge.system.world.clear()
        tracker = ProjectionOccupancy(tracker.bridge, tracker.origin)
        for pos in document.blocks:
            tracker.initial_visible(pos)
        observed = []
        def profile(position):
            observed.append(position)
            return ('modern_projection:r11_entry_%d_%d_%d' % position, .6875)
        expected = {tuple(tracker.origin[i] + pos[i] for i in range(3)) for pos in (base, corner)}
        with patch.dict(POSITION_PLANT_PROXIES, {('minecraft:poppy', 0): profile}, clear=True):
            tracker.snapshot = tracker.state[:]
            tracker.output = SurfacePalette(document.size)
            for unused in tracker.prepare():
                pass
            self.assertEqual(expected, set(observed))
            observed[:] = []
            tracker.bulk = SimpleNamespace(initial=None)
            def begin(key):
                size = tuple(min(16, document.size[i] - key[i] * 16) for i in range(3))
                tracker.bulk.initial = (key, (bytearray([1]) * (size[0] * size[1] * size[2]), size))
            tracker.bulk.begin = begin
            work = WorldProjection.__new__(WorldProjection)
            work.origin, work.document = tracker.origin, document
            work.keys = tuple(sorted(document.blocks.chunks))
            work.occupancy, work.completed, work.shader = tracker, set(), tracker.shader
            work.item_profile = tracker.item_profile
            work.hidden, work.layer, work.liquid = set(), None, None
            work.output, work.prepared = SurfacePalette(document.size), None
            for unused in work.prepare():
                pass
            self.assertEqual(expected, set(observed))

    def fixture(self):
        base, corner, chest_pos = (15, 1, 8), (16, 1, 8), (14, 1, 8)
        stair = lambda direction: registry.from_states('minecraft:oak_stairs', {
            'weirdo_direction': direction, 'upside_down_bit': False})
        water = ('minecraft:water', 0)
        chest = registry.from_states('minecraft:barrel', {'facing_direction': 2, 'open_bit': False})
        render = {'facingDirection': 2, 'x': 14, 'y': 1, 'z': 8}
        nbt = {'id': {'__type__': 8, '__value__': 'Barrel'}}
        document = Document((32, 16, 16), {
            base: make_cell(stair(0), water),
            corner: make_cell(stair(3), water),
            chest_pos: make_cell(chest, water, compose_actor(render, nbt)),
        })
        runtime, origin = Runtime(), (100, 64, 100)
        for pos in (corner, chest_pos):
            runtime.world[tuple(origin[i] + pos[i] for i in range(3))] = STONE
        session = SimpleNamespace(editor=SimpleNamespace(document=document, layer=None),
                                  preview_hidden=lambda: (), solo_layer=False,
                                  opacity=.5, projection_missing=True)
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime,
                                 level='level', projection_serial=1, models={}, model_layouts={},
                                 projection_occupancy=None, projection_mesh=None,
                                 alive=True, entity=None)
        tracker = ProjectionOccupancy(bridge, origin)
        return document, tracker, base, corner, chest_pos, render

    def native(self, source):
        return prepare_palette(source.palette_data())

    def capture_boundary(self, bridge):
        result = {}
        palette = SimpleNamespace(DeserializeBlockPalette=lambda data: result.update(data=data) or True)
        bridge.factory = SimpleNamespace(
            CreateBlock=lambda level: SimpleNamespace(GetBlankBlockPalette=lambda: palette),
            CreateBlockGeometry=lambda level: SimpleNamespace(
                CombineBlockPaletteToGeometry=lambda palette, name, mode: name))
        bridge.geometry = lambda *args, **kwargs: ClientBridge.geometry(bridge, *args, **kwargs)
        return result

    def assert_context(self, actual, document, target):
        volume = actual['volume']
        local = volume == (64, 64, 64)
        self.assertIn(volume, ((36, 64, 520), (64, 64, 64)))
        encode = local_context_position if local else context_position
        center = local_context_center if local else context_center
        decode = local_context_logical if local else logical_position
        occupied = set()
        for original, value in document.blocks.items():
            neighbor = tuple(original[axis] - target[axis] for axis in range(3))
            pos = encode(target, neighbor)
            index = (pos[1] * volume[1] + pos[0]) * volume[0] + pos[2]
            occupied.add(index)
            self.assertIn(index, actual['common'][tuple(value)])
            self.assertEqual(registry.states(tuple(value)), actual['states'][tuple(value)])
        self.assertEqual(occupied, set(actual['extra'][('minecraft:water', 0)]))
        actor = next(iter(actual['actor']['minecraft:barrel'].values()))
        self.assertNotIn('nbt', actor)
        self.assertEqual(encode(target, (-1, 0, 0)), tuple(actor[axis] for axis in ('x', 'y', 'z')))
        centers = set()
        for entries in actual['common'].values():
            for index in entries:
                pos = (index // volume[0] % volume[1], index // (volume[0] * volume[1]), index % volume[0])
                fragment = tuple(axis + .5 for axis in pos)
                if center(native_mesh_position(fragment)):
                    centers.add(decode(fragment))
        self.assertEqual({tuple(axis + .5 for axis in target)}, centers)

    def test_complete_context_control_preserves_stairs_water_and_actor(self):
        document, tracker, base, corner, chest, render = self.fixture()
        data = self.native(document)
        indices = {tracker.index(pos) for pos in (base, corner, chest)}
        self.assertEqual(indices, {index for group in data['common'].values() for index in group})
        self.assertEqual(indices, set(data['extra'][('minecraft:water', 0)]))
        self.assertEqual({'minecraft:barrel': {tracker.index(chest): render}}, data['actor'])

    def test_small_initial_geometry_submits_full_context_to_actual_native_boundary(self):
        document, tracker, base, unused, unused2, unused3 = self.fixture()
        boundary = self.capture_boundary(tracker.bridge)
        tracker.bridge.geometry(document, tracker.initial_visible, name='small', context_document=tracker.document)
        self.assert_context(boundary['data'], document, base)
        self.assertEqual((document.size, boundary['data']['volume']), tracker.bridge.model_layouts['small'])
        self.assertEqual(tracker.bridge.model_layouts['small'], tracker.bridge.model_layouts[b'small'])

    def test_chunk_initial_world_projection_submits_prepared_neighbor_context(self):
        document, tracker, base, unused, unused2, unused3 = self.fixture()
        tracker.bulk = SimpleNamespace(initial=None)
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
        work = WorldProjection.__new__(WorldProjection)
        work.origin = tracker.origin
        work.document, work.keys = tracker.document, tuple(sorted(document.blocks.chunks))
        work.occupancy, work.completed = tracker, set()
        work.item_profile = tracker.item_profile
        work.shader = tracker.shader
        work.hidden, work.layer = set(), None
        work.output, work.prepared = SurfacePalette(document.size), None
        work.liquid = None
        for unused in work.prepare():
            pass
        boundary = self.capture_boundary(tracker.bridge)
        work.bridge, work.origin, work.anchor = tracker.bridge, tracker.origin, tracker.anchor
        tracker.bridge.later = lambda delay, callback: None
        tracker.bridge.preparing_entity = None
        work.submit()
        self.assert_context(boundary['data'], document, base)

    def test_dynamic_rebuild_submits_context_and_keeps_entire_source_snapshot(self):
        document, tracker, base, unused, unused2, unused3 = self.fixture()
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
        boundary = self.capture_boundary(tracker.bridge)
        tracker.entity = 'existing'
        tracker.submit()
        self.assert_context(boundary['data'], document, base)

    def test_block_store_builder_yields_and_never_serializes_whole_source(self):
        document, tracker, base, unused, unused2, unused3 = self.fixture()
        target = document.palette_data(lambda pos: pos == base)
        builder = ContextPaletteBuilder(document, target)
        with patch.object(Document, 'palette_data', side_effect=AssertionError('whole source serialized')):
            units = sum(1 for unused in builder.prepare())
        self.assertGreater(units, 1)
        self.assert_context(builder.data, document, base)
        self.assertEqual(3, len(builder.cache))

    def test_missing_even_small_documents_route_through_incremental_world_projection(self):
        document, tracker, unused, unused2, unused3, unused4 = self.fixture()
        bridge = tracker.bridge
        bridge.session.origin = tracker.origin
        bridge.ensure_projection_distance = lambda size: None
        work = SimpleNamespace(incremental=True)
        bridge.project_large = lambda origin: work if origin == tracker.origin else None
        bridge.geometry = lambda *args, **kwargs: self.fail('Missing projection must prepare incrementally')
        self.assertLess(document.volume, 32768)
        self.assertIs(work, ClientBridge.project(bridge))

    def test_nonmissing_small_geometry_keeps_native_logical_palette(self):
        document, tracker, unused, unused2, unused3, unused4 = self.fixture()
        boundary = self.capture_boundary(tracker.bridge)
        tracker.bridge.geometry(document, name='ordinary')
        self.assertEqual((16, 32, 16), boundary['data']['volume'])
        self.assertEqual(document.palette_data()['common'], boundary['data']['common'])


if __name__ == '__main__':
    unittest.main()

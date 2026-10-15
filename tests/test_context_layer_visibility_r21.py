"""View exclusions must reach native adjacency before faces are tessellated."""
import copy
from types import SimpleNamespace
import unittest

import test_bridge
from test_occupancy_review import Runtime, STONE
from modern_projection.projection.bridge import ClientBridge
from modern_projection.projection.large_preview import SurfacePalette
from modern_projection.projection.model import Document
from modern_projection.projection.occupancy import ProjectionOccupancy
from modern_projection.projection.render_context import (ContextBatchBuilder,
    ContextPaletteBuilder, prepare_context_batches)
from modern_projection.projection.render_layout import (context_position,
                                                       local_context_position)
from modern_projection.projection.session import Session
from modern_projection.projection.world_projection import WorldProjection


CYAN = ('minecraft:cyan_concrete', 0)
YELLOW = ('minecraft:yellow_concrete', 0)
MAGENTA = ('minecraft:magenta_concrete', 0)
BASE, ABOVE, BELOW, SIDE = (1, 1, 1), (1, 2, 1), (1, 0, 1), (2, 1, 1)


class ContextLayerVisibilityTests(unittest.TestCase):
    def test_hidden_cyan_neighbor_is_absent_before_native_merge(self):
        lower, upper = (1, 0, 1), (1, 1, 1)
        document = Document((3, 3, 3), {lower: CYAN, upper: CYAN})
        targets = document.palette_data(lambda pos: pos == lower)
        complete = prepare_context_batches(document, targets)['_context_batches'][0][2]
        filtered = prepare_context_batches(document, targets,
            visible_layer=lambda y: y != 1)['_context_batches'][0][2]
        self.assertEqual([4421, 8517], complete['common'][CYAN])
        self.assertEqual([4421], filtered['common'][CYAN])

    def session(self, mode='full', hidden=()):
        document = Document((3, 4, 3), {BASE: CYAN, ABOVE: YELLOW, BELOW: MAGENTA, SIDE: STONE})
        session = Session.__new__(Session)
        session.editor = SimpleNamespace(document=document, layer=1, hidden_layers=set(hidden))
        session.solo_layer, session.section = mode == 'single', mode == 'section'
        session.opacity, session.projection_missing = .5, False
        return session

    def bridge(self, session):
        runtime, captures = Runtime(), []
        runtime.GetBlankBlockPalette = lambda: SimpleNamespace(
            DeserializeBlockPalette=lambda data: captures.append(copy.deepcopy(data)) or True)
        runtime.CreateBlockGeometry = lambda level: SimpleNamespace(
            CombineBlockPaletteToGeometry=lambda palette, name, mode: name)
        runtime.SetActorBlockGeometryVisible = lambda name, visible: True
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime, level='level',
            projection_serial=1, projection_occupancy=None, projection_shader=None,
            models={}, model_layouts={}, context_models={}, alive=True)
        bridge.geometry = lambda *args, **kwargs: ClientBridge.geometry(bridge, *args, **kwargs)
        return bridge, runtime, captures

    def material_names(self, prepared):
        return {value for unused, unused2, palette in prepared['_context_batches']
                for value in palette['common']}

    def expected_names(self, session):
        return {value for pos, value in session.editor.document.blocks.items()
                if session.visible_layer(pos[1])}

    def test_default_builders_retain_non_target_neighbors(self):
        session = self.session()
        document = session.editor.document
        targets = document.palette_data(lambda pos: pos == BASE)
        for builder_type, encode in ((ContextPaletteBuilder, context_position),
                                     (ContextBatchBuilder, local_context_position)):
            with self.subTest(builder=builder_type.__name__):
                builder = builder_type(document, targets)
                list(builder.prepare())
                palette = (builder.data['_context_batches'][0][2]
                           if builder_type is ContextBatchBuilder else builder.data)
                self.assertEqual(set(document.blocks.values()), set(palette['common']))
                for pos, value in document.blocks.items():
                    neighbor = tuple(pos[i] - BASE[i] for i in range(3))
                    x, y, z = encode(BASE, neighbor)
                    volume = palette['volume']
                    self.assertEqual([(y * volume[1] + x) * volume[0] + z], palette['common'][value])

    def test_hidden_single_and_section_exclude_neighbors_in_both_builders(self):
        for mode, hidden in (('full', (2,)), ('single', ()), ('section', ())):
            session = self.session(mode, hidden)
            document = session.editor.document
            targets = document.palette_data(lambda pos: pos == BASE)
            for builder_type in (ContextPaletteBuilder, ContextBatchBuilder):
                with self.subTest(mode=mode, builder=builder_type.__name__):
                    builder = builder_type(document, targets, visible_layer=session.visible_layer)
                    list(builder.prepare())
                    names = (self.material_names(builder.data) if builder_type is ContextBatchBuilder
                             else set(builder.data['common']))
                    self.assertEqual(self.expected_names(session), names)
                    self.assertIn(STONE, names)

    def test_builder_snapshots_layers_before_incremental_preparation(self):
        session = self.session(hidden=(2,))
        document = session.editor.document
        builder = ContextBatchBuilder(document, document.palette_data(lambda pos: pos == BASE),
                                      visible_layer=session.visible_layer)
        session.editor.hidden_layers.clear()
        list(builder.prepare())
        self.assertNotIn(YELLOW, self.material_names(builder.data))
        current = prepare_context_batches(document, document.palette_data(lambda pos: pos == BASE),
                                          visible_layer=session.visible_layer)
        self.assertIn(YELLOW, self.material_names(current))

    def test_same_document_hidden_unhidden_hidden_rebuilds_native_input(self):
        session = self.session(hidden=(2,))
        document = session.editor.document
        before = copy.deepcopy(document.to_data())
        bridge, unused, captures = self.bridge(session)
        target = SurfacePalette(document.size)
        target.add(BASE, document.blocks[BASE])
        for hidden, expected in (((2,), False), ((), True), ((2,), False)):
            session.editor.hidden_layers = set(hidden)
            bridge.geometry(target, name='same_buffer', context_document=document,
                            context_visible_layer=session.visible_layer)
            self.assertEqual(expected, YELLOW in captures[-1]['common'])
            self.assertIn(STONE, captures[-1]['common'])
        self.assertEqual(3, len(captures))
        self.assertEqual(captures[0], captures[2])
        self.assertNotEqual(captures[0], captures[1])
        self.assertEqual(before, document.to_data())

    def test_world_full_preparation_uses_all_view_modes(self):
        for mode, hidden in (('full', (2,)), ('single', ()), ('section', ())):
            with self.subTest(mode=mode):
                session = self.session(mode, hidden)
                bridge, unused, unused2 = self.bridge(session)
                work = WorldProjection(bridge, (100, 64, 100))
                list(work.prepare())
                self.assertEqual(self.expected_names(session), self.material_names(work.prepared))

    def test_missing_initial_retains_visible_occupied_non_target_neighbor(self):
        session = self.session('single')
        session.projection_missing = True
        bridge, runtime, unused = self.bridge(session)
        origin = (100, 64, 100)
        runtime.world[tuple(origin[i] + SIDE[i] for i in range(3))] = STONE
        work = WorldProjection(bridge, origin)
        list(work.prepare())
        self.assertEqual({CYAN: [13]}, work.output.palette_data()['common'])
        self.assertEqual({CYAN, STONE}, self.material_names(work.prepared))
        self.assertEqual({BASE, ABOVE, BELOW, SIDE}, set(work.document.blocks))

    def test_dynamic_missing_preparation_uses_all_view_modes(self):
        for mode, hidden in (('full', (2,)), ('single', ()), ('section', ())):
            with self.subTest(mode=mode):
                session = self.session(mode, hidden)
                bridge, runtime, unused = self.bridge(session)
                origin = (100, 64, 100)
                runtime.world[tuple(origin[i] + SIDE[i] for i in range(3))] = STONE
                tracker = ProjectionOccupancy(bridge, origin)
                for pos in session.editor.document.blocks:
                    tracker.initial_visible(pos)
                tracker.snapshot = tracker.state[:]
                tracker.output = SurfacePalette(tracker.size)
                list(tracker.prepare())
                self.assertEqual(self.expected_names(session), self.material_names(tracker.prepared))
                self.assertNotIn(STONE, tracker.output.palette_data()['common'])

    def test_spare_buffer_inherits_world_and_missing_layer_visibility(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                session = self.session('single')
                bridge, runtime, captures = self.bridge(session)
                tracker = (ProjectionOccupancy(bridge, (100, 64, 100)) if missing else
                           WorldProjection(bridge, (100, 64, 100)))
                tracker.targets = {BASE}
                target = SurfacePalette(tracker.size)
                target.add(BASE, CYAN)
                first = bridge.geometry(target, name=tracker.shader.names[0],
                    context_document=tracker.document, context_visible_layer=tracker.visible_layer)
                entity = runtime.CreateClientEntityByTypeStr('anchor', tracker.anchor, (0., 0.))
                tracker.shader.bind(entity, first, tracker.anchor)
                self.assertEqual(2, len(captures))
                for palette in captures:
                    self.assertEqual({CYAN, STONE}, set(palette['common']))


if __name__ == '__main__':
    unittest.main()

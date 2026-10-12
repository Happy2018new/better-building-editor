import unittest
from types import SimpleNamespace

import test_render_context
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.model import Document
from projection.render_context import prepare_context_batches
from projection.render_layout import (LOCAL_CONTEXT_SCHEMA_VERSION, local_context_position)
from test_occupancy_review import Runtime
from modern_projection.projection.occupancy_shader import OccupancyShader


class ContextBatchTests(unittest.TestCase):
    def overlay_shader(self):
        runtime = Runtime()
        visible = {}
        def show(name, enabled):
            visible[name] = enabled
            return True
        runtime.SetActorBlockGeometryVisible = show
        original_attach = runtime.AddActorBlockGeometry
        def attach(name, offset, rotation):
            result = original_attach(name, offset, rotation)
            if result:
                visible[name] = True
            return result
        runtime.AddActorBlockGeometry = attach
        document = Document((32, 4, 4), {(1, 1, 1): material('stone')})
        bridge = SimpleNamespace(projection_occupancy=None, factory=runtime, level='level',
                                 session=SimpleNamespace(opacity=.6), context_models={})
        tracker = SimpleNamespace(bridge=bridge, document=document, size=document.size,
                                  targets={(1, 1, 1)}, origin=(100, 64, 200))
        shader = OccupancyShader(tracker)
        first, second = shader.names
        bridge.context_models[first] = (('first_context', (0, 0, 0), True),
                                        ('first_actor', (0, 0, 0), False))
        def seed(unused, name=None, **kwargs):
            bridge.context_models[name] = (('seed_actor', (0, 0, 0), False),)
            return name
        bridge.geometry = seed
        entity = runtime.CreateClientEntityByTypeStr('anchor', (116, 66, 202), (0, 0))
        shader.bind(entity, first, (116, 66, 202))
        bridge.context_models[second] = (('second_actor', (16, 0, 0), False),)
        return shader, runtime, visible

    def test_failed_bank_publication_restores_old_overlay_and_selector(self):
        for failure in ('incoming', 'outgoing', 'selector', 'empty', 'enable', 'transparency'):
            with self.subTest(failure=failure):
                shader, runtime, visible = self.overlay_shader()
                original_show = runtime.SetActorBlockGeometryVisible
                original_write = runtime.SetEntityExtraUniforms
                before = runtime.uniforms[4]
                runtime.EnableActorBlockGeometryTransparent = lambda name, enabled: not (
                    failure == 'enable' and name == 'second_actor')
                runtime.SetActorBlockGeometryTransparency = lambda name, opacity: not (
                    failure == 'transparency' and name == 'second_actor')
                def show(name, enabled):
                    if (failure == 'incoming' and name == 'second_actor' and enabled or
                            failure in ('outgoing', 'empty') and name == 'first_actor' and not enabled):
                        return False
                    return original_show(name, enabled)
                def write(slot, values):
                    if failure == 'selector' and slot == 4 and values[2] == 2.:
                        return False
                    return original_write(slot, values)
                runtime.SetActorBlockGeometryVisible = show
                runtime.SetEntityExtraUniforms = write
                with self.assertRaisesRegex(ValueError, 'projection'):
                    shader.commit(None if failure == 'empty' else shader.names[1])
                self.assertEqual(before, runtime.uniforms[4])
                self.assertEqual(0, shader.bank)
                self.assertFalse(shader.empty)
                self.assertTrue(visible['first_actor'])
                self.assertFalse(visible.get('second_actor', False))
                self.assertFalse(visible['seed_actor'])
                self.assertFalse(runtime.removed)

    def test_failed_overlay_restore_remains_pending_and_follow_retries(self):
        import contextlib
        import io
        shader, runtime, visible = self.overlay_shader()
        shader.configure(1, shader.anchor)
        original = runtime.SetActorBlockGeometryVisible
        failed = []
        def show(name, enabled):
            if name == 'first_actor' and not enabled:
                return False
            if name == 'second_actor' and not enabled and visible.get(name) and not failed:
                failed.append(name)
                return False
            return original(name, enabled)
        runtime.SetActorBlockGeometryVisible = show
        with contextlib.redirect_stderr(io.StringIO()) as log:
            with self.assertRaisesRegex(ValueError, 'overlay visibility'):
                shader.commit(shader.names[1])
        self.assertIn('overlay visibility', log.getvalue())
        self.assertTrue(shader.overlay_restore)
        self.assertEqual(1., runtime.uniforms[4][2])
        self.assertTrue(visible['first_actor'])
        self.assertTrue(visible['second_actor'])
        runtime.SetActorBlockGeometryVisible = original
        self.assertTrue(shader.follow((120, 70, 220), None))
        self.assertFalse(shader.overlay_restore)
        self.assertFalse(visible['second_actor'])
        self.assertTrue(visible['first_actor'])
        self.assertEqual(0, shader.bank)

    def test_actor_overlays_hide_without_relying_on_material_bank_uniforms(self):
        runtime = Runtime()
        visible, calls = {}, []
        def show(name, enabled):
            visible[name] = enabled
            calls.append((name, enabled))
            return True
        runtime.SetActorBlockGeometryVisible = show
        document = Document((32, 4, 4), {(1, 1, 1): material('stone')})
        bridge = SimpleNamespace(projection_occupancy=None, factory=runtime, level='level',
                                 session=SimpleNamespace(opacity=.6), context_models={})
        tracker = SimpleNamespace(bridge=bridge, document=document, size=document.size,
                                  targets={(1, 1, 1)}, origin=(100, 64, 200))
        shader = OccupancyShader(tracker)
        first, second = shader.names
        bridge.context_models[first] = (('first_context', (0, 0, 0), True),
                                        ('first_actor', (0, 0, 0), False))
        def seed(unused, name=None, **kwargs):
            bridge.context_models[name] = (('seed_actor', (0, 0, 0), False),)
            return name
        bridge.geometry = seed
        entity = runtime.CreateClientEntityByTypeStr('anchor', (116, 66, 202), (0, 0))
        shader.bind(entity, first, (116, 66, 202))
        self.assertEqual({'first_actor': True, 'seed_actor': False}, visible)
        bridge.context_models[second] = (('second_actor', (16, 0, 0), False),)
        shader.commit(second)
        self.assertEqual({'first_actor': False, 'seed_actor': False, 'second_actor': True}, visible)
        self.assertNotIn('first_context', visible)
        shader.commit(None)
        self.assertFalse(any(visible.values()))
        bridge.context_models[first] = (('new_actor', (0, 0, 0), False),)
        shader.commit(first)
        self.assertTrue(visible['new_actor'])
        self.assertFalse(any(value for name, value in visible.items() if name != 'new_actor'))
        self.assertEqual(1, len(runtime.created))
        self.assertFalse(runtime.removed)
        self.assertIn((entity, 'first_actor'), runtime.attached)
        self.assertLess(calls.index(('second_actor', True)), calls.index(('first_actor', False)))

    def test_failed_native_overlay_visibility_is_not_cached_as_success(self):
        shader = OccupancyShader(SimpleNamespace(bridge=SimpleNamespace(projection_occupancy=None)))
        shader.render = SimpleNamespace(SetActorBlockGeometryVisible=lambda name, enabled: False)
        with self.assertRaisesRegex(ValueError, 'overlay visibility'):
            shader.show_overlay('actor', False)
        self.assertNotIn('actor', shader.overlay_visibility)

    def test_atomic_bank_replacement_retires_removed_chunks_and_tracks_offsets(self):
        runtime = Runtime()
        document = Document((32, 32, 32), {(1, 1, 1): material('stone')})
        bridge = SimpleNamespace(projection_occupancy=None, factory=runtime, level='level',
                                 session=SimpleNamespace(opacity=.6), context_models={})
        tracker = SimpleNamespace(bridge=bridge, document=document, size=document.size,
                                  targets={(1, 1, 1)}, origin=(100, 64, 200))
        shader = OccupancyShader(tracker)
        first, second = shader.names
        bridge.context_models[first] = (('first_chunk', (0, 0, 0), True),
                                        ('last_chunk', (16, 16, 16), True))
        def seed(unused, name=None, **kwargs):
            bridge.context_models[name] = (('spare_chunk', (0, 0, 0), True),)
            return name
        bridge.geometry = seed
        entity = runtime.CreateClientEntityByTypeStr('anchor', (116, 80, 216), (0, 0))
        changes = []
        runtime.SetActorBlockGeometryTransparency = lambda name, value: changes.append((name, value)) or True
        shader.bind(entity, first, (116, 80, 216))
        self.assertEqual(1, len(runtime.created))
        self.assertEqual((0., 0., 0., 19490.), runtime.uniforms[1])
        bridge.context_models[second] = (('other_chunk', (16, 16, 16), True),)
        shader.commit(second)
        self.assertIn(('spare_chunk', 1.), changes)
        self.assertEqual(2., runtime.uniforms[4][2])
        self.assertTrue(shader.follow((120, 84, 220), None))
        self.assertEqual((3.5, -4, 3.5), runtime.offsets['other_chunk'])
        self.assertEqual(1, len(runtime.created))

    def test_every_axis_stays_bounded_at_full_document_height(self):
        stone = material('stone')
        positions = ((0, 0, 0), (15, 15, 15), (16, 16, 16), (63, 127, 63))
        document = Document((64, 128, 64), dict((pos, stone) for pos in positions))
        saved = document.blocks.copy()
        result = prepare_context_batches(document, document.palette_data())
        self.assertEqual(LOCAL_CONTEXT_SCHEMA_VERSION, result['_context_schema'])
        self.assertEqual(3, len(result['_context_batches']))
        for origin, context, palette in result['_context_batches']:
            self.assertTrue(context)
            self.assertEqual((64, 64, 64), palette['volume'])
            for values in palette['common'].values():
                for index in values:
                    pos = (index // 64 % 64, index // 4096, index % 64)
                    self.assertTrue(all(0 <= axis < 64 for axis in pos))
        self.assertEqual(saved, document.blocks)

    def test_hidden_cross_chunk_neighbor_retains_both_layers(self):
        first, second = (15, 15, 15), (16, 15, 15)
        stair = material('oak_stairs', {'weirdo_direction': 0})
        water = material('water')
        document = Document((32, 32, 32), {first: make_cell(stair, water), second: make_cell(stair, water)})
        result = prepare_context_batches(document, document.palette_data(lambda pos: pos == first))
        origin, context, palette = result['_context_batches'][0]
        self.assertEqual((0, 0, 0), origin)
        expected = set()
        for neighbor in ((0, 0, 0), (1, 0, 0)):
            x, y, z = local_context_position(first, neighbor)
            expected.add((y * 64 + x) * 64 + z)
        self.assertEqual(expected, set(palette['common'][stair]))
        self.assertEqual(expected, set(palette['extra'][water]))

    def test_snow_foreground_overlay_uses_independent_low_coordinates(self):
        snow, fern = material('snow_layer'), material('fern')
        position = (17, 40, 17)
        document = Document((32, 64, 32), {position: make_cell(snow, fern)})
        result = prepare_context_batches(document, document.palette_data())
        self.assertEqual(2, len(result['_context_batches']))
        origin, context, overlay = result['_context_batches'][1]
        self.assertEqual((16, 32, 16), origin)
        self.assertFalse(context)
        self.assertEqual((16, 16, 16), overlay['volume'])
        self.assertEqual([2065], next(iter(overlay['common'].values())))


if __name__ == '__main__':
    unittest.main()

"""Captured 3.10 bodies opt into one render route without altering saved data."""
import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import make_cell
from projection.entity_render import native_actor
from projection.debug_blueprints import material
from projection.geometry_palette import prepare_palette
from projection.model import Document, Editor
from projection.native_render_profile import NativeRenderProfile, production_profile, RUNTIME_VERSION, for_preview
from projection.render_context import prepare_context_batches
from projection.visible_actor import compose_actor

CAPTURES = json.loads((ROOT / 'tests/data/native_actor_310_r15.json').read_text(encoding='utf8'))


def captured(name):
    return copy.deepcopy(CAPTURES['minecraft:' + name]['actor'])


def chest_document(actor=None):
    chest = material('chest', {'minecraft:cardinal_direction': 'south'})
    actor = captured('chest') if actor is None else actor
    nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
           'opaque': {'__type__': 8, '__value__': 'preserved'}}
    return Document((32, 4, 4), {(15, 1, 1): make_cell(chest, nbt=compose_actor(actor, nbt)),
                                (16, 1, 1): make_cell(chest, nbt=compose_actor(actor, nbt))})


class NativeRenderProfileTests(unittest.TestCase):
    def test_production_session_enables_only_qualified_bodies_with_captured_data(self):
        from projection.session import Session
        from test_session import Bridge
        bridge = Bridge()
        bridge.engine_version = RUNTIME_VERSION
        profile = Session(bridge).native_render_profile
        self.assertEqual(production_profile(RUNTIME_VERSION), profile)
        for name in ('chest', 'copper_chest', 'ender_chest'):
            self.assertEqual('model_local', profile.coordinate_mode(material(name), captured(name)))
            self.assertIsNone(profile.coordinate_mode(material(name), {}))
        self.assertEqual('context', profile.coordinate_mode(material('flower_pot'), captured('flower_pot')))
        self.assertIsNone(profile.coordinate_mode(material('bed'), captured('bed')))
        preview = for_preview(profile)
        self.assertIsNone(preview.coordinate_mode(material('chest'), captured('chest')))
        self.assertEqual('context', preview.coordinate_mode(material('flower_pot'), captured('flower_pot')))
        candidate = NativeRenderProfile(model_local=('minecraft:chest',))
        self.assertIs(candidate, for_preview(candidate))
        self.assertNotEqual(profile.identity, preview.identity)
        for version in (None, '', '3.9.0.401155', '3.10.0.999999'):
            self.assertIsNone(production_profile(version))

    def test_only_explicit_exact_names_and_complete_measured_payloads_are_admitted(self):
        names = ('chest', 'copper_chest', 'ender_chest', 'bed', 'flower_pot')
        profile = NativeRenderProfile(model_local=['minecraft:' + name for name in names])
        for name in names:
            value, payload = material(name), captured(name)
            with self.subTest(name=name):
                self.assertEqual('model_local', profile.coordinate_mode(value, payload))
                self.assertIsNone(NativeRenderProfile().coordinate_mode(value, payload))
                self.assertIsNone(profile.coordinate_mode(('custom:' + name, 0), payload))
                for field in payload:
                    missing = dict(payload)
                    del missing[field]
                    self.assertIsNone(profile.coordinate_mode(value, missing), field)
        for name in ('purple_shulker_box', 'dragon_head', 'piglin_head', 'player_head',
                     'skeleton_skull', 'oak_shelf', 'frame'):
            with self.subTest(excluded=name), self.assertRaises(ValueError):
                NativeRenderProfile(model_local=('minecraft:' + name,))
        with self.assertRaises(ValueError):
            NativeRenderProfile(model_local=('minecraft:chest',), context=('minecraft:chest',))

    def test_patterned_banner_world_route_needs_complete_item_placed_actor(self):
        captures = json.loads((ROOT / 'tests/data/native_banner_310_r15.json').read_text(encoding='utf8'))
        profile = NativeRenderProfile(model_local=captures)
        for name, record in captures.items():
            actor = record['actor']
            self.assertEqual('model_local', profile.coordinate_mode((name, 0), actor))
            self.assertEqual('model_local', profile.coordinate_mode((name, 0), CAPTURES[name]['actor']))
            production = production_profile(RUNTIME_VERSION)
            self.assertEqual('model_local', production.coordinate_mode((name, 0), actor))
            self.assertEqual('model_local', for_preview(production).coordinate_mode((name, 0), actor))
            for field in actor:
                missing = dict(actor)
                del missing[field]
                self.assertIsNone(profile.coordinate_mode((name, 0), missing), field)

    def test_banner_schema_accepts_pattern_counts_without_a_pattern_whitelist(self):
        captures = json.loads((ROOT / 'tests/data/native_banner_310_r15.json').read_text(encoding='utf8'))
        profile = NativeRenderProfile(model_local=captures)
        for name, record in captures.items():
            for count in (0, 1, 3, 6, 17):
                actor = dict((key, value) for key, value in record['actor'].items()
                             if not key.startswith(('bannerPattern', 'bannerColor')))
                actor['bannerPatternCount'] = count
                for index in range(count):
                    actor['bannerColor%d' % index] = index % 16
                    actor['bannerPattern%d' % index] = ('bo', 'cre', 'flo', 'moj')[index % 4]
                self.assertEqual('model_local', profile.coordinate_mode((name, 0), actor))
                if count:
                    missing = dict(actor)
                    del missing['bannerPattern%d' % (count - 1)]
                    self.assertIsNone(profile.coordinate_mode((name, 0), missing))
            for invalid in (-1, 1000000, True, '2'):
                actor = dict(record['actor'], bannerPatternCount=invalid)
                self.assertIsNone(profile.coordinate_mode((name, 0), actor))

    def test_banner_material_pose_refreshes_only_the_render_copy(self):
        captures = json.loads((ROOT / 'tests/data/native_banner_310_r15.json').read_text(encoding='utf8'))
        for name, record in captures.items():
            actor = compose_actor(record['actor'], {'id': {'__type__': 8, '__value__': 'Banner'},
                'opaque': {'__type__': 8, '__value__': 'preserved'}})
            saved = copy.deepcopy(actor)
            field = 'ground_sign_direction' if name.endswith('standing_banner') else 'facing_direction'
            for direction in (range(16) if field == 'ground_sign_direction' else range(2, 6)):
                value = material(name, {field: direction})
                result = native_actor(value, actor)
                self.assertEqual(direction, result['bannerDirection'])
                for key in ('bannerPattern0', 'bannerPattern1', 'bannerBaseColor'):
                    self.assertEqual(record['actor'][key], result[key])
                self.assertEqual(saved, actor)
                result['future'] = ['mutation']
                self.assertNotIn('future', record['actor'])

    def test_banner_adapter_preserves_typed_tags_and_byte_keys(self):
        actor = {b'bannerDirection': {b'__type__': 3, b'__value__': 8},
                 b'bannerPatternCount': 0, b'opaque': [b'value']}
        value = material('standing_banner', {'ground_sign_direction': 12})
        before = copy.deepcopy(actor)
        result = native_actor(value, actor)
        self.assertEqual({b'__type__': 3, b'__value__': 12}, result[b'bannerDirection'])
        self.assertEqual(before, actor)

    def test_banner_editor_transforms_refresh_world_render_pose_and_preserve_patterns(self):
        from projection.storage import Selection
        from projection.cell import foreground, actor_data
        from projection.block_registry import states
        captures = json.loads((ROOT / 'tests/data/native_banner_310_r15.json').read_text(encoding='utf8'))
        for name, record in captures.items():
            field = 'ground_sign_direction' if name.endswith('standing_banner') else 'facing_direction'
            initial = 8 if field == 'ground_sign_direction' else 2
            actor = compose_actor(record['actor'], {'id': {'__type__': 8, '__value__': 'Banner'}})
            for transform in ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_z'):
                editor = Editor(Document((4, 4, 4), {(1, 1, 1): make_cell(material(name, {field: initial}), nbt=actor)}))
                original = dict(editor.document.blocks.items())
                editor.selection = Selection(((1, 1, 1),))
                editor._transform(transform)
                value = next(iter(editor.document.blocks.values()))
                value_material, saved_actor = foreground(value), actor_data(value)
                rendered = native_actor(value_material, saved_actor)
                self.assertEqual(states(value_material)[field], rendered['bannerDirection'])
                for key in ('bannerPattern0', 'bannerPattern1', 'bannerColor0', 'bannerColor1', 'bannerBaseColor'):
                    self.assertEqual(record['actor'][key], rendered[key])
                self.assertEqual('model_local', production_profile(RUNTIME_VERSION).coordinate_mode(value_material, rendered))
                editor.undo()
                self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_malformed_or_paired_chests_keep_the_existing_proxy(self):
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        for changes in ({'chestIsLargeChest': True}, {'chestIsLargeChest': 0},
                        {'chestOpenness': float('nan')}, {'chestOldOpenness': True},
                        {'facingDirection': '3'}, {'chestIsGlobalChest': True}):
            actor = captured('chest')
            actor.update(changes)
            source = {'volume': (1, 1, 1), 'common': {material('chest'): [0]},
                      'actor': {'minecraft:chest': {0: actor}}}
            result = prepare_palette(source, native_render_profile=profile)
            self.assertNotIn(material('chest'), result['common'])
            self.assertEqual({}, result['actor'])

    def test_native_selection_preserves_actor_fields_and_typed_saved_nbt(self):
        actor = captured('chest')
        actor['futureField'] = {'opaque': [1, 2, 3]}
        document = chest_document(actor)
        saved = copy.deepcopy(document.to_data())
        source = document.palette_data()
        fallback = prepare_palette(source)
        self.assertTrue(all(value[0].startswith('modern_projection:preview_chest_')
                            for value in fallback['common']))
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        result = prepare_palette(source, native_render_profile=profile)
        self.assertEqual(source['common'], result['common'])
        self.assertEqual(profile.identity, result['_native_render_profile'])
        self.assertEqual([actor, actor], list(result['actor']['minecraft:chest'].values()))
        self.assertEqual(saved, document.to_data())

    def test_model_local_routing_emits_only_target_once_across_chunk_boundary(self):
        document = chest_document()
        saved = copy.deepcopy(document.to_data())
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        targets = document.palette_data(lambda position: position == (16, 1, 1))
        result = prepare_context_batches(document, targets, native_render_profile=profile)
        self.assertEqual(1, len(result['_context_batches']))
        origin, context, palette = result['_context_batches'][0]
        self.assertEqual((16, 0, 0), origin)
        self.assertFalse(context)
        self.assertEqual((16, 16, 16), palette['volume'])
        self.assertEqual({material('chest'): [257]}, palette['common'])
        self.assertEqual({257: captured('chest')}, palette['actor']['minecraft:chest'])
        self.assertEqual(saved, document.to_data())

    def test_explicit_context_route_retains_native_neighbor_context(self):
        document = chest_document()
        profile = NativeRenderProfile(context=('minecraft:chest',))
        targets = document.palette_data(lambda position: position == (16, 1, 1))
        result = prepare_context_batches(document, targets, native_render_profile=profile)
        self.assertEqual(1, len(result['_context_batches']))
        unused, context, palette = result['_context_batches'][0]
        self.assertTrue(context)
        self.assertEqual(2, len(palette['common'][material('chest')]))
        self.assertEqual(2, len(palette['actor']['minecraft:chest']))

    def test_profile_identity_invalidates_preview_and_geometry_without_reaching_sdk(self):
        import test_bridge
        from projection.bridge import ClientBridge
        from projection.session import Session
        from test_session import Bridge
        session = Session(Bridge())
        before = session.preview_signature()
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        session.native_render_profile = profile
        self.assertNotEqual(before, session.preview_signature())
        current = session.preview_signature()
        session.native_render_profile = NativeRenderProfile(model_local=('minecraft:chest',))
        self.assertEqual(current, session.preview_signature())
        with self.assertRaises(AttributeError):
            profile.context = frozenset(('minecraft:chest',))
        received = []
        palette = SimpleNamespace(DeserializeBlockPalette=lambda data: received.append(data) or True)
        bridge = ClientBridge.__new__(ClientBridge)
        bridge.models, bridge.model_layouts, bridge.level, bridge.session = {}, {}, 'level', session
        bridge.factory = SimpleNamespace(
            CreateBlock=lambda level: SimpleNamespace(GetBlankBlockPalette=lambda: palette),
            CreateBlockGeometry=lambda level: SimpleNamespace(
                CombineBlockPaletteToGeometry=lambda data, name, mode: name))
        document = Document((1, 1, 1), {(0, 0, 0): material('stone')})
        first = bridge.geometry(document)
        session.native_render_profile = None
        second = bridge.geometry(document)
        self.assertNotEqual(first, second)
        self.assertEqual(2, len(received))
        self.assertTrue(all('_native_render_profile' not in data for data in received))
        self.assertEqual(second, bridge.geometry(document))

    def test_production_bridge_uses_proxy_in_preview_and_native_in_prepared_world(self):
        import test_bridge
        from projection.bridge import ClientBridge
        received = []
        palette = SimpleNamespace(DeserializeBlockPalette=lambda data: received.append(data) or True)
        bridge = ClientBridge.__new__(ClientBridge)
        profile = production_profile(RUNTIME_VERSION)
        bridge.session = SimpleNamespace(native_render_profile=profile)
        bridge.models, bridge.model_layouts, bridge.context_models, bridge.level = {}, {}, {}, 'level'
        bridge.factory = SimpleNamespace(
            CreateBlock=lambda level: SimpleNamespace(GetBlankBlockPalette=lambda: palette),
            CreateBlockGeometry=lambda level: SimpleNamespace(
                CombineBlockPaletteToGeometry=lambda data, name, mode: name))
        document = chest_document()
        for context in (None, document):
            received[:] = []
            bridge.geometry(document, context_document=context)
            self.assertTrue(received)
            self.assertTrue(all(not data['actor'] for data in received))
            self.assertTrue(all(value[0].startswith('modern_projection:preview_chest_')
                                for data in received for value in data['common']))
        received[:] = []
        world = prepare_context_batches(document, document.palette_data(), native_render_profile=profile)
        bridge.geometry(document, prepared=world)
        self.assertTrue(received)
        self.assertTrue(all('minecraft:chest' in data['actor'] for data in received))
        self.assertTrue(all(value[0] == 'minecraft:chest' for data in received for value in data['common']))

    def test_full_and_missing_projection_snapshot_profile_for_later_rebuilds(self):
        from test_occupancy_review import Runtime
        from projection.occupancy import ProjectionOccupancy
        from projection.world_projection import WorldProjection
        runtime = Runtime()
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        session = SimpleNamespace(editor=Editor(chest_document()), preview_hidden=lambda: (),
                                  solo_layer=False, projection_missing=True, opacity=.5,
                                  native_render_profile=profile)
        bridge = SimpleNamespace(session=session, factory=runtime, system=runtime,
                                 level='level', projection_serial=1,
                                 projection_occupancy=None, projection_work=None)
        work = WorldProjection(bridge, (100, 64, 100))
        session.native_render_profile = None
        self.assertIs(profile, work.native_render_profile)
        self.assertIs(profile, work.occupancy.native_render_profile)
        for unused in work.prepare():
            pass
        self.assertTrue(work.prepared['_context_batches'])
        self.assertTrue(all(not context for unused, context, data in work.prepared['_context_batches']))
        tracker = work.occupancy
        tracker.snapshot = tracker.state[:]
        from projection.large_preview import SurfacePalette
        tracker.output = SurfacePalette(tracker.document.size)
        for unused in tracker.prepare():
            pass
        self.assertTrue(tracker.prepared['_context_batches'])
        self.assertTrue(all(not context for unused, context, data in tracker.prepared['_context_batches']))

    def test_tiled_editor_rebuilds_when_route_changes_and_reuses_equal_profile(self):
        from projection.session import Session
        from test_tiles import Bridge
        bridge = Bridge()
        session = Session(bridge)
        session._loaded(chest_document())
        bridge.settle(session)
        baseline = len(bridge.builds)
        profile = NativeRenderProfile(model_local=('minecraft:chest',))
        session.native_render_profile = profile
        session.refresh_preview()
        bridge.settle(session)
        rebuilt = len(bridge.builds)
        self.assertGreater(rebuilt, baseline)
        session.native_render_profile = NativeRenderProfile(model_local=('minecraft:chest',))
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(rebuilt, len(bridge.builds))
        session.native_render_profile = None
        session.refresh_preview()
        bridge.settle(session)
        self.assertEqual(rebuilt, len(bridge.builds))


if __name__ == '__main__':
    unittest.main()

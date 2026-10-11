"""Resource drift and complete-source wiring, distinct from visual acceptance."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, liquid_face_texture_data, liquid_shape_data
from projection.cell import AIR, make_cell
from projection.debug_blueprints import material
from projection.liquid_preview import LiquidPreview
from projection.liquid_profile import NativeLiquidProfile
from projection.liquid_projection import LiquidProjection
from projection.model import Document
from test_liquid_render import Runtime


def resources():
    return {'schema_version': 2, 'payload_version': 2,
            'game_version': block_registry.source_version(), 'palette_sha256': block_registry.fingerprint(),
            'shape_candidate_sha256': liquid_shape_data.CANDIDATE_SHA256,
            'face_texture_rows_sha256': liquid_face_texture_data.RESOURCE_ROWS_SHA256,
            'models': [('still_water_grey', None, 'registered_still_ui', 'registered_still_world'),
                       ('flowing_water_grey', 'test_side', 'registered_side_ui', 'registered_side_world')],
            'uv_rotations': [('still_water_grey', None, (0,)), ('flowing_water_grey', 'test_side', (0,))],
            'side_templates': {'flowing_water_grey': ('test_side', 0)},
            'world_scale': (16.,) * 3, 'world_rotation': (0.,) * 3, 'max_groups': 32}


def profile(data=None, flow_uv=None):
    return NativeLiquidProfile(resources() if data is None else data,
        lambda unit, pitch, yaw, size: (unit / min(size), pitch - 90., 0., yaw),
        lambda size: (0., min(size) / 4.), flow_uv)


class NativeLiquidProfileTests(unittest.TestCase):
    def test_resource_version_and_shape_texture_drift_cannot_be_ignored(self):
        for field, value in (('schema_version', 1), ('schema_version', 3), ('payload_version', 1), ('game_version', 'future'),
                             ('palette_sha256', '0' * 64), ('shape_candidate_sha256', '0' * 64),
                             ('face_texture_rows_sha256', '0' * 64)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'regeneration'):
                profile(dict(resources(), **{field: value}))

    def test_missing_or_shared_models_and_unregistered_side_templates_are_rejected(self):
        data = resources()
        variants = [dict(data, models=[]), dict(data, models=data['models'][:1]),
                    dict(data, models=data['models'] + data['models'][:1]),
                    dict(data, models=[('still_water_grey', None, 'shared', 'shared')]),
                    dict(data, side_templates={}),
                    dict(data, side_templates={'flowing_water_grey': ('unknown', 0)}),
                    dict(data, side_templates={'flowing_water_grey': ('test_side', True)}),
                    dict(data, max_groups=0), dict(data, world_scale=(0., 16., 16.)),
                    dict(data, world_rotation=(0., float('nan'), 0.))]
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                profile(changed)

    def test_profile_detaches_input_maps_and_keeps_document_layers_actors(self):
        data = resources()
        adapter = profile(data)
        data['models'].clear()
        data['uv_rotations'][1] = ('flowing_water_grey', 'test_side', (1,))
        data['side_templates']['flowing_water_grey'] = ('changed', 0)
        document = Document((4, 3, 4), {(1, 1, 1): make_cell(
            material('oak_fence'), material('water'), {'tag': [1, 2]})})
        before = copy.deepcopy(document.to_data())
        parts = adapter.provider_factory(document).surface(document, (1, 1, 1), 1, material('water'))
        self.assertEqual({33, 30}, {part.faces for part in parts})
        self.assertEqual({1}, {part.layer for part in parts})
        self.assertEqual(before, document.to_data())
        self.assertEqual(('test_side', 0), adapter.side_templates['flowing_water_grey'])
        self.assertEqual(frozenset((0,)), adapter.uv_rotations['flowing_water_grey', 'test_side'])

    def test_uv_capabilities_require_complete_explicit_registered_rotation_codes(self):
        data = resources()
        still, side = data['uv_rotations']
        for rows in (None, [], [still], [still, side, side],
                     [still, ('flowing_water_grey', 'unknown', (0,))],
                     [still, side[:2]], [still, side[:2] + ((),)],
                     [still, side[:2] + ((True,),)], [still, side[:2] + ((-1,),)],
                     [still, side[:2] + ((256,),)], [still, side[:2] + ((.5,),)],
                     [still, side[:2] + ((0, 0),)]):
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, 'UV capabilities|UV rotation capabilities'):
                profile(dict(data, uv_rotations=rows))

    def test_static_side_uvs_use_declared_resource_capabilities(self):
        data = resources()
        data['side_templates']['flowing_water_grey'] = ('test_side', 1)
        with self.assertRaisesRegex(ValueError, 'side UV rotation is unsupported'):
            profile(data)
        data['uv_rotations'][1] = ('flowing_water_grey', 'test_side', (0, 1))
        adapter = profile(data)
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        parts = adapter.provider_factory(document).surface(document, (1, 1, 1), 0, material('water'))
        self.assertEqual(('test_side', 1), next(part for part in parts if part.faces == 30).flow_uv)

    def test_unsupported_dynamic_top_uv_preserves_published_preview_and_world_generation(self):
        selection = [('still_water_grey', None)]
        adapter = profile(flow_uv=lambda *unused: selection[0])
        document = Document((4, 3, 4), {(1, 1, 1): material('water')})
        session = SimpleNamespace(editor=SimpleNamespace(document=document, revision=0, layer=1),
            preview_hidden=lambda: (), solo_layer=False, emit=lambda event: None, opacity=1.)
        preview = LiquidPreview(session, adapter.provider_factory, adapter.models, adapter.max_groups)
        runtime = Runtime()
        runtime.session = session
        projection = LiquidProjection(runtime, document, (10, 64, 20), adapter, 0)
        projection.renderer.SETTLE_SECONDS = 0.
        projection.request()
        for unused in range(100):
            if preview.advance() and projection.advance():
                break
        self.assertIsNone(preview.error)
        self.assertTrue(projection.ready)
        projection.publish()
        previous_preview, previous_signature = dict(preview.groups), preview.published
        previous_world = copy.deepcopy(runtime.models)
        for uv in (('test_side', 1), ('unregistered_top', 0)):
            with self.subTest(uv=uv):
                selection[0] = 'flowing_water_grey', uv
                session.editor.revision += 1
                projection.request()
                self.assertFalse(preview.advance())
                self.assertFalse(projection.advance())
                self.assertIsInstance(preview.error, ValueError)
                self.assertIsInstance(projection.error, ValueError)
                self.assertIn('top UV template or rotation is unsupported', str(preview.error))
                self.assertIn('top UV template or rotation is unsupported', str(projection.error))
                self.assertEqual(previous_preview, preview.groups)
                self.assertEqual(previous_signature, preview.published)
                self.assertEqual(previous_world, runtime.models)
                self.assertTrue(all(not runtime.hidden(model) for model in runtime.models))
                with self.assertRaisesRegex(ValueError, 'not ready'):
                    projection.publish()
        selection[0] = 'flowing_water_grey', ('test_side', 0)
        preview.retry()
        projection.request()
        for unused in range(100):
            if preview.advance() and projection.advance():
                break
        self.assertIsNone(preview.error)
        self.assertIsNone(projection.error)
        self.assertTrue(projection.ready)
        projection.publish()
        self.assertNotEqual(previous_preview, preview.groups)
        self.assertTrue(projection.close())
        preview.close()

    def test_model_names_cannot_alias_other_textures_or_render_paths(self):
        data = resources()
        first, second = data['models']
        for ui, world in ((first[2], second[3]), (second[2], first[3]),
                          (first[3], second[3]), (second[2], first[2]),
                          (first[3], first[2])):
            changed = dict(data, models=[first, second[:2] + (ui, world)])
            with self.subTest(ui=ui, world=world), self.assertRaisesRegex(ValueError, 'model name'):
                profile(changed)

    def test_actual_preview_and_world_plans_share_shapes_but_use_separate_resources(self):
        document = Document((4, 3, 4), {(1, 1, 1): material('water'),
            (2, 1, 1): make_cell(AIR, material('water', {'liquid_depth': 3}))})
        adapter = profile()
        session = SimpleNamespace(editor=SimpleNamespace(document=document, revision=0, layer=1),
            preview_hidden=lambda: (), solo_layer=False, emit=lambda event: None, opacity=1.)
        preview = LiquidPreview(session, adapter.provider_factory, adapter.models, adapter.max_groups)
        for unused in range(100):
            if preview.advance():
                break
        self.assertIsNone(preview.error)
        runtime = Runtime()
        runtime.session = session
        projection = LiquidProjection(runtime, document, (10, 64, 20), adapter, 0)
        projection.renderer.SETTLE_SECONDS = 0.
        projection.request()
        for unused in range(100):
            if projection.advance():
                break
        self.assertTrue(projection.ready)
        self.assertIsNone(projection.error)
        self.assertTrue(all(model['uniforms'][4][3] == 0. for model in runtime.models.values()))
        projection.publish()
        preview_uniforms = sorted(group.uniforms for group in preview.groups.values())
        world_uniforms = sorted(tuple(model['uniforms'][index] for index in (1, 2, 3, 4))
                                for model in runtime.models.values())
        self.assertEqual(preview_uniforms, world_uniforms)
        self.assertEqual({'registered_still_ui', 'registered_side_ui'},
                         {group.model_name for group in preview.groups.values()})
        self.assertEqual({'registered_still_world', 'registered_side_world'},
                         {model['name'] for model in runtime.models.values()})
        self.assertTrue(projection.close())
        self.assertEqual({}, runtime.models)

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
    return {'schema_version': 1, 'payload_version': 2,
            'game_version': block_registry.source_version(), 'palette_sha256': block_registry.fingerprint(),
            'shape_candidate_sha256': liquid_shape_data.CANDIDATE_SHA256,
            'face_texture_rows_sha256': liquid_face_texture_data.RESOURCE_ROWS_SHA256,
            'models': [('still_water_grey', None, 'registered_still_ui', 'registered_still_world'),
                       ('flowing_water_grey', 'test_side', 'registered_side_ui', 'registered_side_world')],
            'side_templates': {'flowing_water_grey': ('test_side', 0)},
            'world_scale': (16.,) * 3, 'world_rotation': (0.,) * 3, 'max_groups': 32}


def profile(data=None):
    return NativeLiquidProfile(resources() if data is None else data,
        lambda unit, pitch, yaw, size: (unit / min(size), pitch - 90., 0., yaw),
        lambda size: (0., min(size) / 4.))


class NativeLiquidProfileTests(unittest.TestCase):
    def test_resource_version_and_shape_texture_drift_cannot_be_ignored(self):
        for field, value in (('schema_version', 2), ('payload_version', 1), ('game_version', 'future'),
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
        data['side_templates']['flowing_water_grey'] = ('changed', 0)
        document = Document((4, 3, 4), {(1, 1, 1): make_cell(
            material('oak_fence'), material('water'), {'tag': [1, 2]})})
        before = copy.deepcopy(document.to_data())
        parts = adapter.provider_factory(document).surface(document, (1, 1, 1), 1, material('water'))
        self.assertEqual({33, 30}, {part.faces for part in parts})
        self.assertEqual({1}, {part.layer for part in parts})
        self.assertEqual(before, document.to_data())
        self.assertEqual(('test_side', 0), adapter.side_templates['flowing_water_grey'])

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

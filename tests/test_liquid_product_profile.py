"""Product deployment guards and actual owner input fidelity, without SDK access."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import biomes, liquid_product_deployment as deployment
from projection import liquid_product_qualification_data as qualification
from projection import liquid_product_shape_data as rules
from projection.debug_product_water_blueprints import FOCUS, source_document
from projection.liquid_preview import LiquidPreview
from projection.liquid_projection import LiquidProjection
from projection.liquid_transport import validate_uniforms
from tests.test_liquid_render import Runtime


def session(document):
    return SimpleNamespace(editor=SimpleNamespace(document=document, revision=0, layer=3),
        preview_hidden=lambda: (), solo_layer=False, emit=lambda unused: None, opacity=1.)


def advance(owner):
    for unused in range(1000):
        if owner.advance():
            return
        if owner.error is not None:
            raise owner.error
    raise AssertionError('Owner did not complete its finite snapshot')


class ProductLiquidProfileTests(unittest.TestCase):
    def test_unaccepted_product_and_native_profiles_remain_disabled(self):
        from projection import liquid_deployment, liquid_resource_data
        from projection.session import Session
        with patch.object(qualification, 'PRODUCT_QUALIFIED', False), \
                patch.object(liquid_resource_data, 'PRODUCTION_QUALIFIED', False):
            self.assertIsNone(deployment.production_profile(deployment.TARGET_ENGINE_VERSION))
            self.assertIsNone(liquid_deployment.production_profile(deployment.TARGET_ENGINE_VERSION))
            self.assertIsNone(Session(SimpleNamespace(engine_version=deployment.TARGET_ENGINE_VERSION)).liquid_profile)
        self.assertEqual('java_snapshot_water_v1', deployment.candidate_profile().style_version)

    def test_generated_product_gate_selects_the_session_default_profile(self):
        from projection.liquid_product_profile import ProductLiquidProfile
        from projection.session import Session
        self.assertIs(qualification.PRODUCT_QUALIFIED, True)
        self.assertEqual('product', qualification.QUALIFICATION_STAGE)
        self.assertEqual(16, len(qualification.GATES))
        self.assertEqual(deployment.REQUIRED_GATES, set(qualification.GATES))
        self.assertTrue(all(value is True for value in qualification.GATES.values()))
        selected = Session(SimpleNamespace(engine_version=deployment.TARGET_ENGINE_VERSION)).liquid_profile
        self.assertIsInstance(selected, ProductLiquidProfile)
        expected = deployment.candidate_profile()
        self.assertEqual(expected.models, selected.models)
        self.assertEqual(expected.world_models, selected.world_models)
        self.assertEqual(rules.PRODUCT_RULES_SHA256, selected.rules_sha256)
        self.assertEqual(rules.PRODUCT_STYLE_VERSION, selected.style_version)
        self.assertIs(expected.preview_factory, selected.preview_factory)
        self.assertIs(expected.projection_factory, selected.projection_factory)

    def test_session_rejects_product_water_for_unknown_or_different_engine_versions(self):
        from projection import liquid_resource_data
        from projection.session import Session
        with patch.object(liquid_resource_data, 'PRODUCTION_QUALIFIED', False):
            for version in (None, '3.9.0.401155', '3.10.0.420448', '3.11.0', '3.10'):
                with self.subTest(version=version):
                    self.assertIsNone(Session(SimpleNamespace(engine_version=version)).liquid_profile)

    def test_qualification_requires_all_routes_and_exact_rules_resources_style(self):
        from projection import liquid_product_resource_data as resources
        from projection import liquid_product_owner_data as owners
        good = {'SCHEMA_VERSION': 2, 'PRODUCT_QUALIFIED': True, 'QUALIFICATION_SHA256': '1' * 64,
                'QUALIFICATION_ENGINE_VERSION': deployment.TARGET_ENGINE_VERSION,
                'QUALIFICATION_RESOURCE_CONTRACT_SHA256': resources.PRODUCT_RESOURCE_CONTRACT_SHA256,
                'QUALIFICATION_RULES_SHA256': rules.PRODUCT_RULES_SHA256,
                'QUALIFICATION_STYLE_VERSION': rules.PRODUCT_STYLE_VERSION,
                'QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256': owners.IMPLEMENTATION_CONTRACT_SHA256,
                'GATES': dict((name, True) for name in deployment.REQUIRED_GATES)}
        for field, invalid in (('SCHEMA_VERSION', 1), ('QUALIFICATION_SHA256', None),
                               ('QUALIFICATION_ENGINE_VERSION', '3.9.0.401155'),
                               ('QUALIFICATION_RESOURCE_CONTRACT_SHA256', '0' * 64),
                               ('QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256', '0' * 64),
                               ('QUALIFICATION_RULES_SHA256', '0' * 64), ('QUALIFICATION_STYLE_VERSION', 'future')):
            with self.subTest(field=field), patch.multiple(qualification, **dict(good, **{field: invalid})):
                with self.assertRaises(ValueError):
                    deployment.production_profile(deployment.TARGET_ENGINE_VERSION)
        for gate in deployment.REQUIRED_GATES:
            with self.subTest(gate=gate), patch.multiple(qualification,
                    **dict(good, GATES=dict(good['GATES'], **{gate: False}))):
                with self.assertRaises(ValueError):
                    deployment.production_profile(deployment.TARGET_ENGINE_VERSION)
        with patch.multiple(qualification, **good):
            self.assertEqual(rules.PRODUCT_RULES_SHA256,
                             deployment.production_profile(deployment.TARGET_ENGINE_VERSION).rules_sha256)
            for version in (None, '3.9.0.401155', '3.11.0', '3.10'):
                self.assertIsNone(deployment.production_profile(version))

    def test_profile_rejects_stale_registry_and_detaches_mutable_resource_maps(self):
        from projection import liquid_product_resource_data as resources
        from projection.liquid_deployment import ui_offset, ui_pose
        from projection.liquid_product_profile import ProductLiquidProfile
        selected = copy.deepcopy(resources.PRODUCT_RESOURCES)
        for field, invalid in (('game_version', 'future'), ('palette_sha256', '0' * 64),
                               ('product_style_version', 'future'), ('top_templates', {}), ('supported_names', ())):
            with self.subTest(field=field), self.assertRaises(ValueError):
                ProductLiquidProfile(dict(selected, **{field: invalid}), ui_pose, ui_offset)
        profile = ProductLiquidProfile(selected, ui_pose, ui_offset)
        selected['side_templates'].clear()
        selected['top_templates'].clear()
        self.assertTrue(profile.side_templates)
        self.assertTrue(profile.top_templates)

    def test_preview_world_and_frozen_resources_share_exact_logical_water(self):
        adapter, frozen = deployment.candidate_profile(), deployment.candidate_profile(frozen=True)
        for identity in ('source', 'low', 'diagonal', 'drop_north', 'flow_east', 'pool', 'wet_oak_fence'):
            document = source_document(identity)
            before = copy.deepcopy(document.to_data())
            s = session(document)
            preview = adapter.preview_factory(s, adapter.provider_factory, adapter.models, adapter.max_groups)
            advance(preview)
            runtime = Runtime()
            runtime.session = s
            world = LiquidProjection(runtime, document, (10, 64, 20), adapter, 0)
            world.renderer.SETTLE_SECONDS = 0.
            world.request()
            advance(world)
            world.publish()
            world_uniforms = sorted(tuple(row['uniforms'][index] for index in (1, 2, 3, 4))
                                    for row in runtime.models.values())
            self.assertEqual(sorted(group.uniforms for group in preview.groups.values()), world_uniforms, identity)
            for group in preview.groups.values():
                validate_uniforms(group.uniforms)
                self.assertIn('_product_', group.model_name)
            frozen_preview = frozen.preview_factory(s, frozen.provider_factory, frozen.models, frozen.max_groups)
            advance(frozen_preview)
            self.assertEqual(sorted(group.uniforms for group in preview.groups.values()),
                             sorted(group.uniforms for group in frozen_preview.groups.values()), identity)
            self.assertEqual(before, document.to_data())
            self.assertTrue(world.close())
            self.assertEqual({}, runtime.models)
            preview.close()
            frozen_preview.close()

    def test_biome_presets_update_both_owners_without_altering_saved_cells(self):
        adapter = deployment.candidate_profile()
        document = source_document('wet_oak_fence')
        before = document.blocks.copy()
        s = session(document)
        preview = adapter.preview_factory(s, adapter.provider_factory, adapter.models, adapter.max_groups)
        runtime = Runtime()
        runtime.session = s
        world = LiquidProjection(runtime, document, (10, 64, 20), adapter, 0)
        world.renderer.SETTLE_SECONDS = 0.
        world.request()
        advance(world)
        world.publish()
        for biome in biomes.KEYS:
            document.biome = biome
            advance(preview)
            world.set_biome(biome)
            advance(world)
            color, unused_opacity = biomes.water_appearance(biome)
            packed = (color[0] << 16) | (color[1] << 8) | color[2]
            self.assertTrue(preview.groups)
            self.assertTrue(runtime.models)
            self.assertTrue(all(group.uniforms[3][2] == packed for group in preview.groups.values()), biome)
            self.assertTrue(all(row['uniforms'][4][2] == packed for row in runtime.models.values()), biome)
            self.assertEqual(before, document.blocks)
        self.assertTrue(world.close())
        preview.close()

    def test_body_and_rear_controls_have_identical_water_geometry(self):
        adapter = deployment.candidate_profile()
        shapes = []
        for control in ('wet', 'liquid_only', 'water_only', 'rearless'):
            document = source_document('wet_oak_fence', control)
            value = document.get_layer(FOCUS, 1)
            parts = adapter.provider_factory(document).surface(document, FOCUS, 1, value)
            shapes.append([(part.heights, part.faces, part.texture_key, part.flow_uv) for part in parts])
        self.assertTrue(all(shape == shapes[0] for shape in shapes[1:]))


if __name__ == '__main__':
    unittest.main()

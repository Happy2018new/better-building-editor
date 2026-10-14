"""Banner family admission and its public fixtures remain version-specific."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import banner_render_contract as contract
from projection.debug_banner_blueprints import METADATA, POSITIONS, observations, populate
from projection.debug_blueprints import Fixture
from projection.cell import actor_data, foreground
from projection.entity_render import native_actor
from projection.native_render_profile import for_preview, production_profile
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import entity_nbt


class BannerRenderContractTests(unittest.TestCase):
    def test_qualified_bundle_matches_its_reviewed_resources(self):
        resource = ROOT / 'tools/data/banner_render_contract_nemc310_v1.json'
        qualification = ROOT / 'docs/evidence/banner-product-r16/qualification.json'
        self.assertTrue(contract.PRODUCT_QUALIFIED)
        self.assertEqual(contract.RESOURCE_CONTRACT_SHA256, hashlib.sha256(resource.read_bytes()).hexdigest())
        self.assertEqual(contract.QUALIFICATION_SHA256, hashlib.sha256(qualification.read_bytes()).hexdigest())
        report = json.loads(qualification.read_bytes())
        self.assertEqual(set(contract.REQUIRED_GATES), set(report['gates']))
        self.assertTrue(all(report['gates'].values()))
        for path, expected in json.loads(resource.read_bytes())['source_sha256'].items():
            self.assertEqual(expected, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())

    def test_unqualified_bundle_does_not_admit_editor_banners(self):
        with patch.object(contract, 'PRODUCT_QUALIFIED', False):
            self.assertEqual((), contract.production_names(contract.ENGINE_VERSION))
            profile = for_preview(production_profile(contract.ENGINE_VERSION))
            for row in observations():
                self.assertIsNone(profile.coordinate_mode((row['name'], 0), row['actor']))

    def test_future_engine_cannot_reuse_the_measured_banner_depth(self):
        with patch.object(contract, 'PRODUCT_QUALIFIED', True):
            for version in ('3.9.0.401155', '3.10.0.420448', '3.11.0.0', None):
                self.assertEqual((), contract.production_names(version))

    def test_incomplete_qualification_fails_closed(self):
        valid = {'PRODUCT_QUALIFIED': True, 'MEASUREMENT_SHA256': 'a' * 64,
                 'RESOURCE_CONTRACT_SHA256': 'b' * 64, 'QUALIFICATION_SHA256': 'c' * 64,
                 'GATES': dict((name, True) for name in contract.REQUIRED_GATES)}
        with patch.multiple(contract, **valid):
            self.assertEqual(contract.FAMILY, contract.production_names(contract.ENGINE_VERSION))
            for gate in contract.REQUIRED_GATES:
                damaged = dict(contract.GATES, **{gate: False})
                with patch.object(contract, 'GATES', damaged), self.assertRaises(ValueError):
                    contract.production_names(contract.ENGINE_VERSION)
            with patch.object(contract, 'RESOURCE_CONTRACT_SHA256', 'invalid'), self.assertRaises(ValueError):
                contract.production_names(contract.ENGINE_VERSION)

    def test_gallery_uses_six_exact_item_placed_pattern_payloads_and_typed_nbt(self):
        from projection import banner_fixture_data as source
        captured = ROOT / 'docs/evidence/native-render-profile-r15/102-real-banner-payloads/report.json'
        self.assertEqual(source.SOURCE_SHA256, hashlib.sha256(captured.read_bytes()).hexdigest())
        doc = populate(Fixture(METADATA))
        saved = copy.deepcopy(doc.to_data())
        for index, pos in enumerate(POSITIONS):
            value = doc.blocks[pos]
            actor = native_actor(foreground(value), actor_data(value))
            self.assertEqual((0, 3, 6)[index % 3], actor['bannerPatternCount'])
            nbt = root_payload(entity_nbt(actor_data(value)))
            self.assertEqual('Banner', scalar(nbt, 'id'))
            self.assertEqual(tuple(pos), tuple(scalar(nbt, axis) for axis in ('x', 'y', 'z')))
            support = (pos[0], 0, pos[2]) if index < 3 else (pos[0], pos[1], pos[2] + 1)
            self.assertEqual('minecraft:stone', foreground(doc.blocks[support])[0])
        self.assertEqual(saved, doc.to_data())

    def test_banner_materials_do_not_override_the_generic_native_actor(self):
        materials = json.loads((ROOT / 'resource_pack/materials/entity.material').read_bytes())['materials']
        self.assertNotIn('vertexShader', materials['netease_block_as_entity_transparency'])
        for name in ('banner', 'banner_pole:banner'):
            self.assertEqual('shaders/glsl/modern_projection_native_preview_banner.vertex', materials[name]['vertexShader'])
            self.assertEqual('shaders/glsl/modern_projection_native_preview_banner.fragment', materials[name]['fragmentShader'])


if __name__ == '__main__':
    unittest.main()

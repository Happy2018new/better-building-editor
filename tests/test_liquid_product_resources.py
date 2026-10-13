"""Product style provenance and resource policy remain separate from native parity."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from generate_liquid_product_resources import (DEFAULT_OPACITY, animation_contract, digest,
    merge_registry, resource_profile, runtime_source, text_digest, verify_contract)
from projection import liquid_product_resource_data as product
from projection import liquid_resource_data as native

CONTRACT_PATH = ROOT / 'tools/data/liquid_product_resource_contract_v1.json'


class ProductWaterResourcesTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_bytes())

    def test_runtime_data_and_raw_assets_bind_the_product_contract(self):
        verify_contract(self.contract, ROOT)
        self.assertEqual(digest(CONTRACT_PATH), product.PRODUCT_RESOURCE_CONTRACT_SHA256)
        self.assertEqual(runtime_source(CONTRACT_PATH),
            (ROOT / 'behavior_pack/modern_projection/projection/liquid_product_resource_data.py').read_text('ascii'))
        self.assertFalse(native.PRODUCTION_QUALIFIED)
        self.assertFalse(product.PRODUCT_RESOURCES['native_parity_claimed'])

    def test_style_cadences_close_at_hour_reset_without_new_payload_channels(self):
        for ticks, cycles in ((1, 2250), (2, 1125)):
            animation = animation_contract(32, ticks)
            self.assertEqual(cycles, animation['cycles_per_reset'])
            self.assertEqual(0, (3600 * 20 // ticks) % 32)
            self.assertFalse(animation['engine_clock_observed'])
            self.assertEqual('TOTAL_REAL_WORLD_TIME', animation['clock_uniform'])
        for frames, ticks in ((32, 7), (True, 2), (32, 0), (0, 1)):
            with self.assertRaises(ValueError):
                animation_contract(frames, ticks)
        self.assertEqual(2, self.contract['payload_version'])

    def test_default_alpha_exposes_rear_scene_and_honors_explicit_layers_of_opacity(self):
        self.assertEqual(.45, DEFAULT_OPACITY)
        for name, options in self.contract['model_options'].items():
            material = self.contract['materials'][name + ':entity_for_skeleton_alpha']
            self.assertEqual(['Blending', 'DisableDepthWrite', 'InvertCulling'], material['+states'])
            self.assertNotIn('DisableCulling', material['+states'])
            self.assertEqual('InvertCulling', options['native_culling_state'])
            self.assertEqual('SourceAlpha', material['blendSrc'])
            self.assertEqual('OneMinusSrcAlpha', material['blendDst'])
            self.assertEqual('Point', material['+samplerStates'][0]['textureFilter'])
            fragment = (ROOT / 'resource_pack/shaders/glsl' / options['fragment_shader']).read_text('ascii')
            self.assertIn('STYLE_DEFAULT_OPACITY = 0.45', fragment)
            self.assertIn('alpha*EXTRA_VECTOR4.w', fragment)
            self.assertIn('alpha*=CURRENT_COLOR.a', fragment)
            self.assertIn('EXTRA_VECTOR4.y<0.0 ? defaultAlpha : EXTRA_VECTOR4.y', fragment)
            self.assertNotIn('float clock = TIME*20.0', fragment)
            self.assertIn('float clock = 0.0;' if options['frozen'] else
                          'float clock = TOTAL_REAL_WORLD_TIME*20.0', fragment)

    def test_freeze_keeps_same_geometry_material_policy_and_original_pngs(self):
        profile = resource_profile(self.contract)
        frozen = resource_profile(self.contract, frozen=True)
        self.assertEqual(product.FROZEN_PRODUCT_MODELS, frozen['models'])
        for animated_row, frozen_row in zip(profile['models'], frozen['models']):
            self.assertEqual(animated_row[:2], frozen_row[:2])
            for animated, freeze in zip(animated_row[2:], frozen_row[2:]):
                self.assertEqual(self.contract['models'][animated]['mesh'], self.contract['models'][freeze]['mesh'])
                self.assertEqual(self.contract['models'][animated]['texture'], self.contract['models'][freeze]['texture'])
                original = dict(self.contract['materials'][animated + ':entity_for_skeleton_alpha'])
                frozen_material = dict(self.contract['materials'][freeze + ':entity_for_skeleton_alpha'])
                original.pop('fragmentShader')
                frozen_material.pop('fragmentShader')
                self.assertEqual(original, frozen_material)
        for key, texture in self.contract['textures'].items():
            self.assertEqual(texture['sha256'], digest(ROOT /
                ('resource_pack/textures/models/modern_projection/liquid/' + key + '.png')))

    def test_invalid_style_metadata_and_drifted_registry_are_rejected(self):
        for field, value in (('native_parity_claimed', True), ('default_opacity', 1.),
                             ('product_style_version', 'future'), ('payload_version', 3),
                             ('resource_style_version', 'nemc_artwork_water_v1'),
                             ('native_culling_state', 'DisableCulling'), ('native_culling_accepted', True)):
            altered = dict(self.contract, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                resource_profile(altered)
        altered = copy.deepcopy(self.contract)
        material = next(value for key, value in altered['materials'].items() if key != 'version')
        material['blendSrc'] = 'One'
        with self.assertRaisesRegex(ValueError, 'material registry'):
            verify_contract(altered, ROOT)

    def test_culling_update_preserves_diagnostic_mesh_bytes_and_keeps_acceptance_closed(self):
        self.assertEqual(12, len(self.contract['models']))
        self.assertEqual('InvertCulling', self.contract['native_culling_state'])
        self.assertFalse(self.contract['native_culling_accepted'])
        self.assertFalse(product.PRODUCT_RESOURCES['native_culling_accepted'])
        baseline = json.loads((ROOT / 'tools/data/liquid_deployment_r12_contract.json').read_bytes())
        for relative, expected in baseline['output_sha256'].items():
            if relative.startswith('resource_pack/models/modern_projection/liquid/'):
                self.assertEqual(expected, self.contract['output_sha256'][relative], relative)
                self.assertEqual(expected, digest(ROOT / relative), relative)

    def test_installer_preserves_unrelated_source_format_and_updates_only_its_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'entity.material'
            original = '{\n  "materials": {\n    "user": {"+states": ["Blending"]}\n  }\n}\n'
            path.write_text(original, encoding='ascii')
            merge_registry(path, {'product:base': {'depthFunc': 'LessEqual'}}, nested=True)
            added = path.read_text('ascii')
            self.assertIn('"user": {"+states": ["Blending"]}', added)
            merge_registry(path, {'product:base': {'depthFunc': 'LessEqual'}}, nested=True)
            self.assertEqual(added, path.read_text('ascii'))
            merge_registry(path, {'product:base': {'depthFunc': 'Equal'}}, nested=True)
            self.assertEqual('Equal', json.loads(path.read_bytes())['materials']['product:base']['depthFunc'])
            self.assertIn('"user": {"+states": ["Blending"]}', path.read_text('ascii'))

    def test_installer_preserves_unrelated_crlf_bytes_when_changing_culling(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'entity.material'
            unrelated = b'    "diagnostic": {"+states": ["Blending"]},\r\n'
            original = (b'{\r\n  "materials": {\r\n' + unrelated +
                        b'    "product:base": {\r\n      "+states": [\r\n'
                        b'        "Blending"\r\n      ]\r\n    }\r\n  }\r\n}\r\n')
            path.write_bytes(original)
            merge_registry(path, {'product:base': {'+states': ['Blending', 'InvertCulling']}}, nested=True)
            updated = path.read_bytes()
            self.assertIn(unrelated, updated)
            self.assertNotIn(b'\n', updated.replace(b'\r\n', b''))
            self.assertIn(b'        "InvertCulling"\r\n', updated)
            merge_registry(path, {'product:base': {'+states': ['Blending', 'InvertCulling']}}, nested=True)
            self.assertEqual(updated, path.read_bytes())

    def test_frozen_host_report_binds_real_shaders_and_keeps_game_claims_false(self):
        report = json.loads((ROOT / 'tools/data/liquid_product_host_gles_v1.json').read_bytes())
        self.assertTrue(report['passed'])
        self.assertGreater(report['checks'], 20000)
        self.assertTrue(all(row['passed'] and not row.get('failures') for row in report['results']))
        self.assertEqual(digest(CONTRACT_PATH), report['contract_sha256'])
        self.assertEqual(digest(ROOT / 'tools/verify_liquid_product_resources.py'), report['verifier_sha256'])
        for name, expected in report['helper_sha256'].items():
            self.assertEqual(expected, text_digest(ROOT / 'tools' / name))
        self.assertFalse(report['game_acceptance_claimed'])
        self.assertFalse(report['native_parity_claimed'])

    def test_committed_byte_contract_survives_git_line_ending_filters(self):
        committed = lambda path: subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT)
        raw_contract = committed(CONTRACT_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(product.PRODUCT_RESOURCE_CONTRACT_SHA256, hashlib.sha256(raw_contract).hexdigest())
        contract = json.loads(raw_contract)
        for relative, expected in contract['output_sha256'].items():
            if relative in ('resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
                continue
            self.assertEqual(expected, hashlib.sha256(committed(relative)).hexdigest(), relative)
        for relative, expected in contract['project_source_sha256'].items():
            self.assertEqual(expected, hashlib.sha256(committed(relative).replace(b'\r\n', b'\n')).hexdigest(), relative)


if __name__ == '__main__':
    unittest.main()

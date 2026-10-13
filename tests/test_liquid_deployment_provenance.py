"""Version checks bind installed liquid bytes without archived machine paths."""
import ast
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_version_bundle import check_liquid_deployment


class LiquidDeploymentProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
        self.contract = json.loads((ROOT / 'tools/data/liquid_deployment_r12_contract.json').read_bytes())
        files = set(self.contract['output_sha256']) | {
            'tools/data/liquid_deployment_r12_contract.json',
            'tools/generate_liquid_skeleton_resources.py',
            'behavior_pack/modern_projection/projection/liquid_resource_data.py',
            'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'}
        if self.contract.get('flow_top_candidate'):
            files.update({self.contract['flow_top_candidate']['source_file'],
                          'tools/generate_liquid_flow_top.py',
                          'behavior_pack/modern_projection/projection/liquid_flow_top_data.py',
                          'behavior_pack/modern_projection/projection/liquid_flow_top.py'})
        for relative in files:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def rewrite_generated(self, **changes):
        path = self.root / 'behavior_pack/modern_projection/projection/liquid_resource_data.py'
        values = {}
        for node in ast.parse(path.read_text(encoding='ascii')).body:
            if isinstance(node, ast.Assign):
                values[node.targets[0].id] = ast.literal_eval(node.value)
        values.update(changes)
        path.write_text(''.join('%s = %r\n' % item for item in values.items()), encoding='ascii')

    def test_portable_resources_pass_without_original_native_install_or_runtime_bundle(self):
        checked = check_liquid_deployment(self.manifest, self.root)
        self.assertIn(Path('tools/data/liquid_deployment_r12_contract.json'), [Path(value) for value in checked])
        self.assertFalse((self.root / '.runtime').exists())

    def test_source_version_or_palette_drift_fails_before_any_qualification(self):
        for field in ('game_version', 'source_sha256'):
            with self.subTest(field=field):
                changed = dict(self.manifest, **{field: 'different'})
                with self.assertRaisesRegex(ValueError, 'observations do not match'):
                    check_liquid_deployment(changed, self.root)

    def test_contract_generator_header_or_artwork_byte_drift_is_rejected(self):
        for relative, message in (
                ('tools/data/liquid_deployment_r12_contract.json', 'resource contract'),
                ('tools/generate_liquid_skeleton_resources.py', 'resource generator'),
                ('resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h', 'preview-depth'),
                ('resource_pack/textures/models/modern_projection/liquid/still_water_grey.png', 'resource bytes')):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, message):
                    check_liquid_deployment(self.manifest, self.root)
                path.write_bytes(original)

    def test_merged_registries_allow_other_owners_but_reject_liquid_binding_drift(self):
        for relative, message in (('resource_pack/models/netease_models.json', 'model binding'),
                                  ('resource_pack/materials/entity.material', 'material binding')):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                data = json.loads(original)
                entries = data['materials'] if 'materials' in data else data
                entries['another_module'] = {'unrelated': True}
                path.write_text(json.dumps(data), encoding='ascii')
                check_liquid_deployment(self.manifest, self.root)
                entries.pop(next(key for key in entries if key.startswith('modern_projection_liquid_')))
                path.write_text(json.dumps(data), encoding='ascii')
                with self.assertRaisesRegex(ValueError, message):
                    check_liquid_deployment(self.manifest, self.root)
                path.write_bytes(original)

    def test_generated_profile_cannot_omit_shapes_or_relabel_models(self):
        self.rewrite_generated(FROZEN_MODELS=())
        with self.assertRaisesRegex(ValueError, 'shape and texture'):
            check_liquid_deployment(self.manifest, self.root)

    def test_flow_top_candidate_source_generator_and_runtime_drift_are_rejected(self):
        for relative in (self.contract['flow_top_candidate']['source_file'],
                         'tools/generate_liquid_flow_top.py',
                         'behavior_pack/modern_projection/projection/liquid_flow_top_data.py',
                         'behavior_pack/modern_projection/projection/liquid_flow_top.py'):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'flow top source'):
                    check_liquid_deployment(self.manifest, self.root)
                path.write_bytes(original)

    def test_extra_render_fields_or_changed_material_state_require_requalification(self):
        path = self.root / 'resource_pack/materials/entity.material'
        original = path.read_bytes()
        for changes in ({'+defines': ['ALPHA_TEST']}, {'depthFunc': 'Always'},
                        {'blendSrc': 'One'}, {'+states': ['DisableCulling']}):
            with self.subTest(changes=changes):
                data = json.loads(original)
                material = next(value for key, value in data['materials'].items()
                                if key.startswith('modern_projection_liquid_'))
                material.update(changes)
                path.write_text(json.dumps(data), encoding='ascii')
                with self.assertRaisesRegex(ValueError, 'material binding'):
                    check_liquid_deployment(self.manifest, self.root)

    def test_qualification_requires_explicit_flag_and_matching_resource_fingerprint(self):
        path = self.root / 'behavior_pack/modern_projection/projection/liquid_resource_data.py'
        original = path.read_bytes()
        for changes in ({'PRODUCTION_QUALIFIED': 1},
                        {'QUALIFICATION_SHA256': '1' * 64},
                        {'PRODUCTION_QUALIFIED': True},
                        {'PRODUCTION_QUALIFIED': True, 'QUALIFICATION_SHA256': '1' * 64,
                         'QUALIFICATION_RESOURCE_CONTRACT_SHA256': '2' * 64}):
            with self.subTest(changes=changes):
                path.write_bytes(original)
                self.rewrite_generated(**changes)
                with self.assertRaisesRegex(ValueError, 'qualification'):
                    check_liquid_deployment(self.manifest, self.root)


if __name__ == '__main__':
    unittest.main()

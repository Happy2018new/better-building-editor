"""Candidate resource ownership stays separate from production qualification."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import liquid_deployment as deployment, liquid_resource_data as source
from projection.cell import make_cell
from projection.debug_blueprints import material
from projection.model import Document
from generate_liquid_deployment import resource_profile, runtime_source, verify_installed_resources
from generate_liquid_payload_poc import NATIVE_KEYS, source_snapshot
from generate_liquid_skeleton_resources import digest
from projection.liquid_render_plan import iter_groups


class LiquidDeploymentTests(unittest.TestCase):
    def test_production_gate_is_closed_until_actual_native_qualification(self):
        self.assertFalse(source.PRODUCTION_QUALIFIED)
        self.assertIsNone(deployment.production_profile())
        with patch.object(source, 'PRODUCTION_QUALIFIED', True):
            with self.assertRaisesRegex(ValueError, 'qualification fingerprint'):
                deployment.production_profile()
            with patch.object(source, 'QUALIFICATION_SHA256', '1' * 64):
                with self.assertRaisesRegex(ValueError, 'different resource bundle'):
                    deployment.production_profile()

    def test_same_bundle_qualification_selects_owned_ui_and_world_resources(self):
        with patch.object(source, 'PRODUCTION_QUALIFIED', True), \
                patch.object(source, 'QUALIFICATION_SHA256', '1' * 64), \
                patch.object(source, 'QUALIFICATION_RESOURCE_CONTRACT_SHA256', source.RESOURCE_CONTRACT_SHA256):
            profile = deployment.production_profile()
        self.assertEqual((.1, -65., 0., 35.), profile.ui_pose(20., 25., 35., (200., 250.)))
        self.assertEqual((0., 50.), profile.ui_offset((200., 250.)))
        self.assertEqual((16.,) * 3, profile.world_scale)
        self.assertTrue(set(profile.models.values()).isdisjoint(profile.world_models.values()))

    def test_candidate_keeps_flow_alias_layer_and_complete_document_unchanged(self):
        water = material('flowing_water', {'liquid_depth': 3})
        cell = make_cell(material('oak_fence'), water, {'tag': [1, 2]})
        document = Document((4, 3, 4), {(1, 1, 1): cell})
        before = copy.deepcopy(document.to_data())
        profile = deployment.candidate_profile(frozen=True)
        parts = profile.provider_factory(document).surface(document, (1, 1, 1), 1, water)
        self.assertEqual({1}, {part.layer for part in parts})
        self.assertEqual({33, 30}, {part.faces for part in parts})
        self.assertEqual(before, document.to_data())
        self.assertTrue(all('_frozen' in name for name in profile.models.values()))
        self.assertFalse(source.PRODUCTION_QUALIFIED)

    def test_generator_rejects_old_same_named_models_with_wrong_native_transform(self):
        models, options = {}, {}
        for key in ('still_water_grey', 'flowing_water_grey'):
            for suffix, transform in (('', 'native_ui_neg_x_neg_z_neg_y_center1_5'),
                                      ('_world', 'native_bone_after_reverse_z')):
                name = 'modern_projection_liquid_' + key + suffix
                models[name] = {}
                options[name] = {'texture': key, 'transform': transform, 'preview_depth': not suffix,
                                 'uv_rotations': [0]}
        contract = {'world_bone_matrix': True, 'preview_depth': True, 'payload_version': 2,
                    'models': models, 'model_options': options}
        self.assertEqual((16.,) * 3, resource_profile(contract)['world_scale'])
        options['modern_projection_liquid_flowing_water_grey']['transform'] = 'different_axes'
        with self.assertRaisesRegex(ValueError, 'transform/depth/rotation'):
            resource_profile(contract)

    def test_flow_alias_uses_occupied_neighbors_from_complete_source_for_selected_targets(self):
        water = material('flowing_water')
        document = Document((4, 3, 4), {(1, 1, 1): make_cell(material('oak_fence'), water),
                                       (2, 1, 1): material('stone')})
        before = copy.deepcopy(document.to_data())
        profile = deployment.candidate_profile()
        full = list(iter_groups(document, profile.provider_factory(document)))
        targets = document.palette_data(lambda pos: pos == (1, 1, 1))
        selected = list(iter_groups(document, profile.provider_factory(document), targets))
        surfaces = lambda groups: [(shape.position, shape.layer, shape.heights, shape.faces,
                                   shape.texture_key, shape.flow_uv)
                                  for group in groups for shape in group.surfaces]
        self.assertEqual(surfaces(full), surfaces(selected))
        self.assertTrue(all(not shape.faces & 16 for group in selected for shape in group.surfaces))
        self.assertEqual(before, document.to_data())

    def bundle(self, directory):
        native, bundle, project = (directory / name for name in ('native', 'bundle', 'project'))
        textures = native / 'resource_packs/vanilla/textures'
        textures.mkdir(parents=True)
        atlas = {'texture_data': {key: {'textures': 'textures/' + key} for key in NATIVE_KEYS}}
        flipbook = [{'atlas_tile': key, 'flipbook_texture': 'textures/' + key, 'ticks_per_frame': 2}
                    for key in NATIVE_KEYS]
        (textures / 'terrain_texture.json').write_text(json.dumps(atlas), encoding='ascii')
        (textures / 'flipbook_textures.json').write_text(json.dumps(flipbook), encoding='ascii')
        contract = dict(source_snapshot(native), world_bone_matrix=True, preview_depth=True,
                        payload_version=2, models={}, model_options={}, textures={}, output_sha256={},
                        generator_sha256=digest(ROOT / 'tools/generate_liquid_skeleton_resources.py'))
        reference = native / 'reference.h'
        reference.write_text('reference shader bytes', encoding='ascii')
        contract['source_sha256'] = {str(reference): digest(reference)}
        for key in ('still_water_grey', 'flowing_water_grey'):
            artwork = textures / 'blocks' / (key + '.png')
            artwork.parent.mkdir(exist_ok=True)
            artwork.write_bytes(key.encode('ascii'))
            contract['textures'][key] = {'source': str(artwork), 'sha256': digest(artwork), 'flipbook': {
                'flipbook_texture': 'textures/blocks/' + key}}
            for frozen in ('', '_frozen'):
                for suffix, transform in (('', 'native_ui_neg_x_neg_z_neg_y_center1_5'),
                                          ('_world', 'native_bone_after_reverse_z')):
                    name = 'modern_projection_liquid_' + key + frozen + suffix
                    contract['models'][name] = {'material': name}
                    contract['model_options'][name] = {'texture': key, 'transform': transform,
                        'preview_depth': not suffix, 'uv_rotations': [0]}
        outputs = {'resource_pack/shaders/liquid.fragment': b'liquid shader bytes',
                   'resource_pack/models/netease_models.json': json.dumps(contract['models']).encode('ascii'),
                   'resource_pack/materials/entity.material': json.dumps({'materials': {
                       'version': '1.0.0', 'liquid': {'states': ['Blending']}}}).encode('ascii')}
        for relative, value in outputs.items():
            for root in (bundle, project):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(value)
            contract['output_sha256'][relative] = digest(bundle / relative)
        path = bundle / 'contract.json'
        path.write_text(json.dumps(contract), encoding='ascii')
        return path, native, project, reference

    def test_concrete_bundle_rejects_native_source_output_and_installed_resource_drift(self):
        for target, message in (('reference', 'resource source'), ('bundle', 'resource bytes'),
                                ('installed', 'Installed liquid resource'), ('native', 'liquid artwork')):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                path, native, project, reference = self.bundle(Path(temporary))
                self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, native, project))
                changed = {'reference': reference,
                    'bundle': path.parent / 'resource_pack/shaders/liquid.fragment',
                    'installed': project / 'resource_pack/shaders/liquid.fragment',
                    'native': native / 'resource_packs/vanilla/textures/blocks/still_water_grey.png'}[target]
                changed.write_bytes(changed.read_bytes() + b'drift')
                with self.assertRaisesRegex(ValueError, message):
                    runtime_source(path, native, project)

    def test_native_references_follow_selected_installation_when_old_installation_remains(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            path, native, project, unused_reference = self.bundle(directory)
            current_native = directory / 'other_native'
            shutil.copytree(native, current_native)
            self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, current_native, project))
            (current_native / 'reference.h').write_bytes(b'changed header in current installation')
            with self.assertRaisesRegex(ValueError, 'resource source'):
                runtime_source(path, current_native, project)

    def test_historical_windows_sources_work_with_posix_native_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, native, project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            original = str(native)
            archived_root = 'Z:/old-client/version/data'
            contract['source_sha256'] = {name.replace(original, archived_root).replace('/', '\\'): fingerprint
                                         for name, fingerprint in contract['source_sha256'].items()}
            contract['native_source_sha256'] = {name.replace('\\', '/'): fingerprint
                                                for name, fingerprint in contract['native_source_sha256'].items()}
            for artwork in contract['textures'].values():
                artwork['source'] = artwork['source'].replace(original, archived_root).replace('/', '\\')
            path.write_text(json.dumps(contract), encoding='ascii')
            self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, native, project))
            (native / 'reference.h').write_bytes(b'changed selected native source')
            with self.assertRaisesRegex(ValueError, 'resource source'):
                runtime_source(path, native, project)

    def test_artwork_root_is_derived_from_metadata_not_fixed_directory_depth(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, native, project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            key = 'still_water_grey'
            original = native / 'resource_packs/vanilla/textures/blocks' / (key + '.png')
            nested = native / 'resource_packs/vanilla/textures/blocks/new-layout/liquids' / (key + '.png')
            nested.parent.mkdir(parents=True)
            shutil.copyfile(original, nested)
            artwork = contract['textures'][key]
            artwork['source'] = str(nested)
            artwork['flipbook']['flipbook_texture'] = 'textures/blocks/new-layout/liquids/' + key
            path.write_text(json.dumps(contract), encoding='ascii')
            self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, native, project))
            artwork['source'] = str(original)
            path.write_text(json.dumps(contract), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'metadata path'):
                runtime_source(path, native, project)

    def test_source_outside_archived_native_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, native, project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            contract['source_sha256'] = {'Z:/unrelated/reference.h': '0' * 64}
            path.write_text(json.dumps(contract), encoding='ascii')
            with self.assertRaises(ValueError):
                runtime_source(path, native, project)

    def test_traversal_and_rooted_resource_metadata_cannot_select_other_sources(self):
        for changed in ('reference', 'artwork', 'fingerprint'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                path, native, project, unused_reference = self.bundle(Path(temporary))
                contract = json.loads(path.read_bytes())
                if changed == 'reference':
                    outside = native.parent / 'outside.h'
                    outside.write_bytes(b'outside selected installation')
                    contract['source_sha256'] = {str(native / '..' / 'outside.h'): digest(outside)}
                elif changed == 'artwork':
                    contract['textures']['still_water_grey']['flipbook']['flipbook_texture'] = '/rooted/texture'
                else:
                    contract['native_source_sha256'] = {'/rooted/header': '0' * 64}
                path.write_text(json.dumps(contract), encoding='ascii')
                with self.assertRaises(ValueError):
                    runtime_source(path, native, project)

    def test_historical_posix_source_labels_rebind_to_selected_windows_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, native, project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            original = str(native)
            archived_root = '/archive/linux-native'
            contract['source_sha256'] = {name.replace(original, archived_root).replace('\\', '/'): fingerprint
                                         for name, fingerprint in contract['source_sha256'].items()}
            for artwork in contract['textures'].values():
                artwork['source'] = artwork['source'].replace(original, archived_root).replace('\\', '/')
            path.write_text(json.dumps(contract), encoding='ascii')
            self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, native, project))

    def test_backslash_flipbook_names_rebind_to_selected_native_artwork(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, native, project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            for artwork in contract['textures'].values():
                artwork['flipbook']['flipbook_texture'] = artwork['flipbook']['flipbook_texture'].replace('/', '\\')
            path.write_text(json.dumps(contract), encoding='ascii')
            self.assertIn('PRODUCTION_QUALIFIED = False', runtime_source(path, native, project))

    def test_flowing_artwork_cannot_escape_or_mislabel_its_native_source(self):
        for metadata in ('/rooted/texture', '../outside', 'Z:/foreign/texture', 'wrong/source'):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as temporary:
                path, native, project, unused_reference = self.bundle(Path(temporary))
                contract = json.loads(path.read_bytes())
                contract['textures']['flowing_water_grey']['flipbook']['flipbook_texture'] = metadata
                path.write_text(json.dumps(contract), encoding='ascii')
                with self.assertRaises(ValueError):
                    runtime_source(path, native, project)

    def test_installed_material_merges_preserve_existing_entries_and_reject_candidate_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, unused_native, project, unused_reference = self.bundle(Path(temporary))
            material_path = project / 'resource_pack/materials/entity.material'
            material_data = json.loads(material_path.read_bytes())
            material_data['materials']['existing'] = {'states': ['DisableDepthWrite']}
            material_path.write_text(json.dumps(material_data), encoding='ascii')
            verify_installed_resources(path, project)
            material_data['materials']['liquid']['states'] = []
            material_path.write_text(json.dumps(material_data), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'model/material'):
                verify_installed_resources(path, project)

    def test_resource_capabilities_reject_nonzero_shader_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, unused_native, unused_project, unused_reference = self.bundle(Path(temporary))
            contract = json.loads(path.read_bytes())
            contract['model_options']['modern_projection_liquid_flowing_water_grey']['uv_rotations'] = [0, 1]
            with self.assertRaisesRegex(ValueError, 'transform/depth/rotation'):
                resource_profile(contract)

    def test_committed_provenance_matches_contract_after_git_filters(self):
        committed = lambda relative: subprocess.check_output(['git', 'show', 'HEAD:' + relative], cwd=ROOT)
        contract_path = 'tools/data/liquid_deployment_r12_contract.json'
        contract_bytes = committed(contract_path)
        contract = json.loads(contract_bytes)
        self.assertEqual(source.RESOURCE_CONTRACT_SHA256, hashlib.sha256(contract_bytes).hexdigest())
        self.assertEqual(contract['generator_sha256'], hashlib.sha256(
            committed('tools/generate_liquid_skeleton_resources.py')).hexdigest())
        for relative, expected in contract['output_sha256'].items():
            value = committed(relative)
            if relative == 'resource_pack/materials/entity.material':
                actual = json.loads(value)['materials']
                self.assertEqual(len(contract['models']), sum(name.startswith('modern_projection_liquid_') for name in actual))
            elif relative == 'resource_pack/models/netease_models.json':
                actual = json.loads(value)
                self.assertTrue(all(actual.get(name) == row for name, row in contract['models'].items()))
            else:
                self.assertEqual(expected, hashlib.sha256(value).hexdigest(), relative)


if __name__ == '__main__':
    unittest.main()

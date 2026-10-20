"""The kelp generator rejects source drift and owns every render resource."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'behavior_pack/modern_projection')]
import generate_kelp_proxies as generator
from projection.kelp_render import PROXIES
from projection import block_registry as registry


class KelpResourceTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(generator.PROFILE.read_bytes())

    def test_generated_resources_match_and_ids_are_hidden_from_registry(self):
        files = generator.outputs(self.profile)
        self.assertEqual(5, len(files))
        for path, expected in files.items():
            self.assertEqual(expected, json.loads(path.read_bytes()))
        for identifier in PROXIES.values():
            self.assertIsNone(registry.states((identifier, 0)))

    def test_version_part_atlas_and_frame_drift_rejected(self):
        changes = ['resource', 'registry', 'registry_sha', 'part', 'atlas', 'texture_path',
                   'frame_order', 'speed', 'size', 'template', 'native_mesh', 'native_cycle', 'snow']
        for change in changes:
            profile = deepcopy(self.profile)
            if change == 'resource': profile['resource_version'] = 'NEMC future'
            elif change == 'registry': profile['registry_version'] = 'NEMC future'
            elif change == 'registry_sha': profile['registry_sha256'] = '0'*64
            elif change == 'part': profile['parts']['stem']['identifier'] = PROXIES['top']
            elif change == 'atlas': profile['parts']['top']['atlas_tile'] = 'kelp_a'
            elif change == 'texture_path': profile['parts']['stem']['texture_path'] = 'textures/blocks/kelp_top.tga'
            elif change == 'frame_order': profile['parts']['stem']['flipbook']['frames'].reverse()
            elif change == 'speed': profile['parts']['stem']['flipbook']['ticks_per_frame'] = 1
            elif change == 'size': profile['parts']['top']['texture_size'] = [16, 16]
            elif change == 'template': profile['template_sha256'] = '0'*64
            elif change == 'native_mesh': profile['native_mesh_authority'] = True
            elif change == 'native_cycle': profile['native_cycle_qualified'] = True
            else: profile['snow_qualified'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                generator.validate(profile)

    def test_changed_tga_hash_rejected_against_supplied_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            native = Path(temporary)
            for row in self.profile['parts'].values():
                path = native/row['texture_path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'this is a deliberately altered native source')
            with self.assertRaisesRegex(ValueError, 'Installed kelp texture differs'):
                generator.validate(self.profile, native)

    def test_native_source_hash_match_then_atlas_mismatch_rejected(self):
        profile = deepcopy(self.profile)
        with tempfile.TemporaryDirectory() as temporary:
            native = Path(temporary)
            for part,row in profile['parts'].items():
                raw = (part+' negative control source').encode('ascii')
                path = native/row['texture_path']
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                row['texture_sha256'] = hashlib.sha256(raw).hexdigest()
            (native/'textures/terrain_texture.json').write_text(json.dumps({'texture_data':{}}))
            (native/'textures/flipbook_textures.json').write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Installed native kelp atlas binding differs'):
                generator.validate(profile, native)

    def test_version_bundle_commands_include_kelp_generator(self):
        source = (ROOT/'tools/check_version_bundle.py').read_text(encoding='utf-8')
        self.assertIn("['tools/generate_kelp_proxies.py', '--check']", source)


if __name__ == '__main__':
    unittest.main()

"""Keep runtime upgrades separate from registry provenance and fluid policy."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import configure_development_runtime as runtime


class DevelopmentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.target = runtime.load_target()
        self.registry = json.loads((ROOT / self.target['block_registry_manifest']).read_bytes())

    def test_runtime_migration_retains_the_original_dump(self):
        self.assertEqual('3.10.0.420447', self.target['engine_version'])
        self.assertEqual('NEMC 3.9.0.401155', self.target['registry_version'])
        raw = (ROOT / self.registry['source_file']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.target['registry_sha256'])
        self.assertTrue(self.target['transforms_update_deferred'])

    def test_config_upgrade_preserves_user_options_and_pack_scope(self):
        config = {'game_executable_path': 'old.exe', 'included_mod_dirs': ['./', 'other-addon'],
                  'auto_hot_reload_mods': True, 'world_seed': 73, 'custom_setting': [1, 2]}
        original = copy.deepcopy(config)
        upgraded = runtime.configure(config, self.target)
        self.assertEqual(config, original)
        for key in ('included_mod_dirs', 'auto_hot_reload_mods', 'world_seed', 'custom_setting'):
            self.assertEqual(config[key], upgraded[key])
        self.assertIn('/3.10.0.420447/', upgraded['game_executable_path'])
        self.assertFalse(upgraded['auto_hot_reload_shaders'])

    def test_mislabeled_resources_or_rewritten_registry_are_rejected(self):
        for key, value in (('schema_version', True), ('resource_version', 'NEMC 3.9.0.401155'),
                           ('registry_version', 'NEMC 3.10.0.420447'),
                           ('registry_sha256', '0' * 64), ('minecraft_version', '1.21'),
                           ('game_executable_sha256', 'not-a-hash'),
                           ('block_registry_update_deferred', False),
                           ('transforms_update_deferred', False)):
            with self.subTest(key=key):
                target = dict(self.target, **{key: value})
                with self.assertRaises(ValueError):
                    runtime.validate(target, self.registry)

    def test_official_water_or_cauldron_fallback_cannot_be_enabled(self):
        self.assertEqual('native', self.target['rendering']['world_lava'])
        for key in ('world_water', 'cauldron_contents'):
            target = copy.deepcopy(self.target)
            target['rendering'][key] = 'native'
            with self.assertRaisesRegex(ValueError, 'custom fluid'):
                runtime.validate(target, self.registry)

    def test_changed_installation_fails_before_local_config_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'Minecraft.Windows.exe'
            binary.write_bytes(b'a different native engine')
            with self.assertRaisesRegex(ValueError, 'record and review'):
                runtime.verify_binary(binary, self.target)


if __name__ == '__main__':
    unittest.main()

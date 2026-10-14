"""Keep liquid render target provenance separate from the retained registry."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, liquid_face_texture_data, liquid_render_target_data as target
from projection.liquid_face_textures import LiquidFaceTextures
from projection.liquid_profile import NativeLiquidProfile
from projection.liquid_product_profile import ProductLiquidProfile


class LiquidRenderTargetTests(unittest.TestCase):
    def test_manifest_explicitly_separates_target_and_registry(self):
        manifest = json.loads((ROOT / 'tools/data/runtime_target_manifest.json').read_bytes())
        self.assertEqual(target.TARGET_ENGINE_VERSION, manifest['engine_version'])
        self.assertEqual(target.TARGET_MINECRAFT_VERSION, manifest['minecraft_version'])
        self.assertEqual(target.TARGET_RESOURCE_VERSION, manifest['resource_version'])
        self.assertEqual(target.SOURCE_VERSION, manifest['registry_version'])
        self.assertEqual(target.PALETTE_SHA256.lower(), manifest['registry_sha256'])
        self.assertEqual(target.TARGET_MANIFEST_SHA256,
                         hashlib.sha256((ROOT / 'tools/data/runtime_target_manifest.json').read_bytes()).hexdigest())
        self.assertNotEqual(target.TARGET_RESOURCE_VERSION, target.SOURCE_VERSION)
        self.assertEqual(target.CAPABILITIES, manifest['rendering'])

    def test_current_registry_is_the_only_accepted_source(self):
        target.check_version(block_registry.source_version(), block_registry.fingerprint())
        for version, fingerprint in (('NEMC 3.10.0.420447', block_registry.fingerprint()),
                                     (block_registry.source_version(), '0' * 64)):
            with self.subTest(version=version, fingerprint=fingerprint), self.assertRaises(ValueError):
                target.check_version(version, fingerprint)

    def test_profile_and_face_entrypoints_use_target_gate(self):
        with patch.object(target, 'check_version', side_effect=ValueError('target gate')):
            with self.assertRaisesRegex(ValueError, 'target gate'):
                LiquidFaceTextures(object(), {})
            with self.assertRaisesRegex(ValueError, 'target gate'):
                NativeLiquidProfile({}, lambda *args: (), lambda *args: ())
            with self.assertRaisesRegex(ValueError, 'target gate'):
                ProductLiquidProfile({}, lambda *args: (), lambda *args: ())

    def test_face_source_remains_registry_bound_after_target_migration(self):
        self.assertEqual(liquid_face_texture_data.SOURCE_VERSION, target.SOURCE_VERSION)
        self.assertEqual(liquid_face_texture_data.PALETTE_SHA256.lower(), target.PALETTE_SHA256.lower())


if __name__ == '__main__':
    unittest.main()

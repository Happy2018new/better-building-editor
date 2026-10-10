import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, block_traits


class NativeTraitTests(unittest.TestCase):
    def test_static_export_and_runtime_traits_match_the_native_palette_version(self):
        source = ROOT / 'tools/data/native_block_metadata_nemc_3.9.0.401155.json'
        data = json.loads(source.read_text(encoding='utf8'))
        self.assertEqual(block_registry.fingerprint(), data['palette_sha256'])
        self.assertEqual(block_registry.fingerprint(), block_traits.SOURCE_SHA256)
        self.assertEqual(block_registry.source_version(), block_traits.SOURCE_VERSION)
        self.assertEqual(set(block_registry.BLOCKS), set(data['blocks']))

    def test_partial_and_transparent_native_models_are_not_assumed_to_be_full_solid(self):
        self.assertTrue(block_traits.is_solid(('minecraft:stone', 0)))
        for name in ('oak_stairs', 'cobblestone_wall', 'oak_fence', 'chest',
                     'glass', 'glass_pane', 'water', 'snow_layer', 'ice'):
            self.assertFalse(block_traits.is_solid(('minecraft:' + name, 0)), name)
        self.assertFalse(block_traits.is_solid(('custom:unknown', 0)))

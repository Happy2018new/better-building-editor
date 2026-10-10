import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry, block_traits
from projection import block_traits_data


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

    def provisional(self):
        fields = {'WATERLOGGABLE_BLOCKS': frozenset(('minecraft:oak_fence',)),
                  'WATERLOGGABLE_AUX': {'minecraft:oak_stairs': frozenset((0,))},
                  'WATERLOGGABLE_COMPLETE': False,
                  'WATERLOGGABLE_VERIFIED_BLOCKS': frozenset(('minecraft:stone',)),
                  'WATERLOGGABLE_VERIFIED_AUX': {'minecraft:oak_stairs': frozenset((0, 1))}}
        for name, value in fields.items():
            handle = patch.object(block_traits_data, name, value, create=True)
            handle.start()
            self.addCleanup(handle.stop)

    def test_unavailable_water_metadata_is_explicit_and_custom_extensions_remain_optional(self):
        with patch.object(block_traits_data, 'WATERLOGGABLE_BLOCKS', None, create=True):
            self.assertEqual('unavailable', block_traits.water_capabilities_status())
            with self.assertRaisesRegex(ValueError, 'have not been measured'):
                block_traits.is_waterloggable(('minecraft:oak_fence', 0))
            self.assertFalse(block_traits.is_waterloggable(('custom:unknown', 0)))

    def test_partial_metadata_distinguishes_true_false_and_unverified_states(self):
        self.provisional()
        self.assertEqual('provisional', block_traits.water_capabilities_status())
        self.assertTrue(block_traits.is_waterloggable(('minecraft:oak_fence', 0)))
        self.assertTrue(block_traits.is_waterloggable(('minecraft:oak_stairs', 0)))
        self.assertFalse(block_traits.is_waterloggable(('minecraft:oak_stairs', 1)))
        self.assertFalse(block_traits.is_waterloggable(('minecraft:stone', 0)))
        with self.assertRaisesRegex(ValueError, 'not verified'):
            block_traits.is_waterloggable(('minecraft:oak_stairs', 2))
        with self.assertRaisesRegex(ValueError, 'not verified'):
            block_traits.is_waterloggable(('minecraft:glass', 0))

    def test_legacy_aliases_resolve_before_native_water_queries(self):
        self.provisional()
        with patch.object(block_traits_data, 'WATERLOGGABLE_AUX',
                          {'minecraft:oak_slab': frozenset((1,))}):
            self.assertEqual(('minecraft:oak_slab', 1),
                             block_registry.canonical(('minecraft:wooden_slab', 8)))
            self.assertTrue(block_traits.is_waterloggable(('minecraft:wooden_slab', 8)))

    def test_complete_verified_table_has_definitive_negative_results(self):
        self.provisional()
        with patch.object(block_traits_data, 'WATERLOGGABLE_COMPLETE', True):
            self.assertEqual('complete', block_traits.water_capabilities_status())
            self.assertFalse(block_traits.is_waterloggable(('minecraft:glass', 0)))
            self.assertFalse(block_traits.is_waterloggable(('minecraft:oak_stairs', 2)))

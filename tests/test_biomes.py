import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.model import Document, Editor
from projection.session import Session
from projection import biomes, codec, archive
from projection.transfer import packets, Receiver
from projection.sharing_codec import encode_steps, decode_steps
from test_sharing import Bridge


class BiomeTests(unittest.TestCase):
    def test_building_tint_survives_every_archive_and_sharing_path(self):
        for size, biome in ((size, biome) for size in ((8, 8, 8), (64, 128, 64))
                            for biome in biomes.KEYS):
            doc = Document(size, {(1, 2, 3): ('minecraft:leaves', 0)}, biome=biome)
            restored = [Document.from_data(doc.to_data()),
                        list(codec.load_steps(codec.to_data(doc)))[-1]]
            receiver = Receiver()
            for packet in packets(doc):
                receiver.feed(packet)
            restored.append(receiver.result)
            bridge = Bridge()
            index = list(archive.save_steps(bridge, doc, 1))[-1]
            restored.append(list(archive.load_steps(bridge, 1, index))[-1])
            text = list(encode_steps(doc))[-1]['text']
            restored.append(list(decode_steps(text))[-1]['document'])
            for result in restored:
                self.assertEqual(biome, result.biome)
                self.assertEqual(doc.blocks, result.blocks)
                self.assertEqual(doc.size, result.size)

    def test_old_buildings_default_to_plains_and_invalid_tints_are_rejected(self):
        data = Document((2, 2, 2)).to_data()
        del data['biome']
        self.assertEqual('plains', Document.from_data(data).biome)
        for value in (None, 1, [], 'unknown', 'minecraft:forest'):
            with self.assertRaises(ValueError):
                Document.from_data(dict(data, biome=value))
            receiver = Receiver()
            packet = next(packets(Document()))
            packet['biome'] = value
            with self.assertRaises(ValueError):
                receiver.feed(packet)

    def test_changing_tint_preserves_geometry_and_marks_only_appearance_dirty(self):
        bridge = Bridge()
        calls = []
        bridge.update_biome_tint = calls.append
        s = Session(bridge)
        before = (s.preview_signature(), dict(s.editor.document.blocks.items()), s.tiles.builds)
        notifications = []
        s.subscribe(lambda: notifications.append(True), ('biome',))
        for biome in ('jungle', 'jungle', 'desert'):
            s.set_biome(biome)
        self.assertEqual(['jungle', 'desert'], calls)
        self.assertEqual(2, len(notifications))
        self.assertEqual(before, (s.preview_signature(), dict(s.editor.document.blocks.items()), s.tiles.builds))
        self.assertNotEqual(s.editor.saved_biome, s.editor.document.biome)
        s.save()
        self.assertEqual('desert', bridge.index['buildings'][0]['data']['biome'])
        self.assertEqual('desert', s.editor.saved_biome)

    def test_large_session_save_and_export_snapshot_keep_tint(self):
        s = Session(Bridge())
        s.editor = Editor(Document((64, 128, 64), biome='taiga'))
        s.save()
        s.bridge.settle()
        self.assertEqual('taiga', s.library[0]['data']['biome'])
        self.assertEqual('taiga', s.editor.saved_biome)
        s.sharing.open_export()
        s.bridge.settle()
        self.assertEqual('taiga', s.sharing.document.biome)

    def test_current_biome_uses_nearest_known_color_without_guessing_custom_biomes(self):
        self.assertEqual('forest', biomes.from_native(b'minecraft:forest_hills'))
        self.assertEqual('jungle', biomes.from_native('minecraft:bamboo_jungle'))
        self.assertEqual('taiga', biomes.from_native('redwood_taiga_mutated'))
        self.assertEqual('forest', biomes.from_native('birch_forest_hills_mutated'))
        self.assertEqual('jungle', biomes.from_native('jungle_edge_mutated'))
        self.assertEqual('pale_garden', biomes.from_native('pale_garden'))
        self.assertEqual('mesa', biomes.from_native('minecraft:mesa'))
        self.assertEqual('birch_forest', biomes.from_native('ocean'))
        self.assertEqual('taiga', biomes.from_native('meadow'))
        self.assertIsNone(biomes.from_native('custom:red_forest'))
        self.assertIsNone(biomes.from_native('custom:forest'))
        self.assertIsNone(biomes.from_native(None))

    def test_exact_names_and_equal_color_ties_are_stable(self):
        for key in biomes.KEYS:
            self.assertEqual(key, biomes.from_native('minecraft:' + key))
        self.assertEqual('savanna', biomes.from_native('savanna_mutated'))
        self.assertEqual('savanna', biomes.from_native('savanna_plateau'))
        # This variant has different climate colors: do not force its parent.
        self.assertEqual('forest', biomes.from_native('savanna_plateau_mutated'))
        self.assertEqual('desert', biomes.nearest('BEB654', 'AEA42A'))
        self.assertEqual('savanna', biomes.nearest('BEB654', 'AEA42A', 'savanna'))

    def test_matching_accounts_for_foliage_as_well_as_grass(self):
        self.assertEqual('swampland', biomes.nearest('4C763C', '6A7039'))
        self.assertEqual('mangrove_swamp', biomes.nearest('4C763C', '8DB127'))

    def test_native_shaded_grass_is_matched_as_a_biome_color(self):
        # Vanilla roofed_forest enables grass_is_shaded and the native
        # grass-side atlas supplies its 507A32 shaded swatch. The installed
        # mutated client biome does not enable that appearance override.
        self.assertEqual(('507A32', '59AE30'), biomes.NATIVE_COLORS['roofed_forest'])
        self.assertEqual('roofed_forest', biomes.from_native('roofed_forest'))
        self.assertEqual('forest', biomes.from_native('roofed_forest_mutated'))

    def test_distinct_native_appearance_colors_are_preserved_exactly(self):
        for name in ('pale_garden', 'cherry_grove', 'mesa', 'roofed_forest'):
            self.assertEqual(name, biomes.from_native('minecraft:' + name))
            row = biomes.PRESETS[biomes.shader_index(name) - 1]
            self.assertEqual(biomes.NATIVE_COLORS[name], row[2:])
        self.assertEqual('mesa', biomes.from_native('mesa_bryce'))
        # Bedrock's mesa_plateau has climate colors, unlike other badlands.
        self.assertEqual('desert', biomes.from_native('mesa_plateau'))

    def test_palette_has_no_duplicate_choices_and_retains_legacy_indices(self):
        legacy = ('plains', 'forest', 'birch_forest', 'taiga', 'swampland',
                  'mangrove_swamp', 'jungle', 'desert', 'savanna', 'ice_plains')
        self.assertEqual(legacy, biomes.KEYS[:len(legacy)])
        self.assertEqual(13, len(biomes.CHOICES))
        self.assertEqual(len(biomes.CHOICES), len(set(row[2:] for row in biomes.CHOICES)))
        self.assertEqual(set(row[2:] for row in biomes.PRESETS),
                         set(row[2:] for row in biomes.CHOICES))

    def test_every_bundled_vanilla_biome_has_a_nearest_preset(self):
        self.assertEqual(87, len(biomes.NATIVE_COLORS))
        for name in biomes.NATIVE_COLORS:
            with self.subTest(biome=name):
                self.assertIn(biomes.from_native(name), biomes.KEYS)
                preset = biomes.PRESETS[biomes.shader_index(biomes.from_native(name)) - 1]
                # A compact palette may approximate climate variants, but
                # must not lose the clearly different gray/yellow/dark hues.
                native = biomes.NATIVE_COLORS[name]
                for actual, expected in zip(preset[2:], native):
                    difference = [abs(int(actual[i:i+2], 16) - int(expected[i:i+2], 16))
                                  for i in (0, 2, 4)]
                    self.assertLessEqual(max(difference), 26)


if __name__ == '__main__':
    unittest.main()

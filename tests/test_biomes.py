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
        for size in ((8, 8, 8), (64, 128, 64)):
            doc = Document(size, {(1, 2, 3): ('minecraft:leaves', 0)}, biome='swampland')
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
                self.assertEqual('swampland', result.biome)
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

    def test_current_biome_mapping_does_not_silently_guess_unknown_biomes(self):
        self.assertEqual('forest', biomes.from_native(b'minecraft:forest_hills'))
        self.assertEqual('jungle', biomes.from_native('minecraft:bamboo_jungle'))
        self.assertEqual('taiga', biomes.from_native('redwood_taiga_mutated'))
        self.assertEqual('forest', biomes.from_native('birch_forest_hills_mutated'))
        self.assertIsNone(biomes.from_native('jungle_edge_mutated'))
        self.assertIsNone(biomes.from_native('pale_garden'))
        self.assertIsNone(biomes.from_native('custom:red_forest'))
        self.assertIsNone(biomes.from_native('custom:forest'))
        self.assertIsNone(biomes.from_native(None))


if __name__ == '__main__':
    unittest.main()

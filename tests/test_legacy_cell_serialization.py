"""Foreground-only writers must ignore obsolete complete-cell palette rows."""
import base64
import json
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import make_cell
from projection.codec import encode_chunk, to_data
from projection.model import AIR, Document
from projection.sharing_codec import checksum, decode_steps
from projection.transfer import packets, Receiver

STONE = ('minecraft:stone', 0)
DIRT = ('minecraft:dirt', 0)
GOLD = ('minecraft:gold_block', 0)
WATER = ('minecraft:water', 0)
ALIAS = ('minecraft:log', 5)


class LegacyCellSerializationTests(unittest.TestCase):
    def test_obsolete_rich_rows_remap_mixed_and_uniform_chunks_without_mutating_source(self):
        for back, actor in ((WATER, None), (AIR, {'Items': [{'Name': 'apple'}]}),
                            (WATER, {'unknown': {'nested': (b'\x00\xff', 1 << 40)}})):
            with self.subTest(background=back, actor=actor):
                doc = Document((32, 16, 16), {(0, 0, 0): make_cell(STONE, back, actor)})
                doc.set_cell((1, 0, 0), DIRT)
                doc.set_cell((0, 0, 0), GOLD)
                doc.set_cell((2, 0, 0), ALIAS)
                doc.blocks.fill_chunk((1, 0, 0), STONE)
                current_config = to_data(doc)
                current_packets = list(packets(doc))
                rich_config = to_data(doc, 4)
                rich_packets = list(packets(doc, 3))
                original_palette = list(doc.blocks.palette)
                original_chunks = {key: chunk if isinstance(chunk, int) else chunk.tobytes()
                                   for key, chunk in doc.blocks.chunks.items()}

                data = json.loads(json.dumps(to_data(doc, 2)))
                self.assertEqual([list(AIR), list(DIRT), list(GOLD), list(ALIAS), list(STONE)],
                                 data['palette'])
                self.assertEqual(4, next(row for row in data['chunks'] if row[:3] == [1, 0, 0])[3])
                restored = Document.from_data(data)
                self.assertEqual(doc.blocks, restored.blocks)
                self.assertEqual(doc.blocks.counts, restored.blocks.counts)
                self.assertEqual(ALIAS, restored.get((2, 0, 0)))

                stream = list(packets(doc, 2))
                self.assertEqual(5, stream[0]['paletteCount'])
                receiver = Receiver()
                for packet in stream:
                    receiver.feed(json.loads(json.dumps(packet)))
                self.assertEqual(doc.blocks, receiver.result.blocks)
                raw = ''.join(json.dumps(packet, separators=(',', ':')) + '\n'
                              for packet in stream).encode('ascii')
                shared = 'MP2:' + base64.b64encode(zlib.compress(raw)).decode('ascii') + ':' + checksum(raw)
                self.assertEqual(doc.blocks, list(decode_steps(shared))[-1]['document'].blocks)

                self.assertEqual(original_palette, doc.blocks.palette)
                self.assertEqual(original_chunks, {key: chunk if isinstance(chunk, int) else chunk.tobytes()
                                                  for key, chunk in doc.blocks.chunks.items()})
                self.assertEqual(current_config, to_data(doc))
                self.assertEqual(current_packets, list(packets(doc)))
                self.assertEqual(rich_config, to_data(doc, 4))
                self.assertEqual(rich_packets, list(packets(doc, 3)))

    def test_erasing_last_rich_cell_leaves_a_readable_empty_legacy_document(self):
        doc = Document((1, 1, 1), {(0, 0, 0): make_cell(STONE, WATER, {'Items': []})})
        doc.set_cell((0, 0, 0), AIR)
        data = to_data(doc, 2)
        self.assertEqual([list(AIR)], data['palette'])
        self.assertEqual(doc.blocks, Document.from_data(data).blocks)
        receiver = Receiver()
        for packet in packets(doc, 2):
            receiver.feed(packet)
        self.assertEqual(doc.blocks, receiver.result.blocks)

    def test_occupied_rich_cells_cannot_be_discarded_by_legacy_export(self):
        for cell in (make_cell(STONE, WATER), make_cell(STONE, AIR, {'Items': []})):
            doc = Document((1, 1, 1), {(0, 0, 0): cell})
            with self.assertRaises(ValueError):
                to_data(doc, 2)
            with self.assertRaises(ValueError):
                list(packets(doc, 2))
            self.assertEqual(cell, doc.get((0, 0, 0)))

    def test_plain_legacy_chunk_payloads_keep_original_palette_ids(self):
        doc = Document((32, 16, 16), {(0, 0, 0): ALIAS, (1, 0, 0): STONE})
        doc.blocks.fill_chunk((1, 0, 0), DIRT)
        expected = [encode_chunk(key, doc.blocks.chunks[key]) for key in sorted(doc.blocks.chunks)]
        self.assertEqual(expected, to_data(doc, 2)['chunks'])
        actual = [row for packet in packets(doc, 2) if packet['kind'] == 'chunks' for row in packet['rows']]
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()

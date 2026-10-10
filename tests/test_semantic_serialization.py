"""Cross-registry states, legacy readers, compact payload limits and migrations."""
import base64
import copy
import json
import random
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import compact_chunk, semantic_wire
from projection.codec import encode_chunk, to_data
from projection.cell import make_cell, actor_data
from projection.model import AIR, Document
from projection.transfer import packets, Receiver
from projection.sharing_codec import encode_steps, decode_steps
from projection.storage import position
from projection.session import Session

STONE = ('minecraft:stone', 0)


def envelope(mode, raw):
    return '1%s:' % mode + base64.b64encode(zlib.compress(raw)).decode('ascii')


class SemanticSerializationTests(unittest.TestCase):
    def test_every_exported_material_semantically_round_trips(self):
        source = semantic_wire.provenance()
        for name in registry.BLOCKS:
            for aux in registry.aux_values(name):
                value = (name, aux)
                row = semantic_wire.encode_material(value)
                restored = semantic_wire.decode_material(json.loads(json.dumps(row)), source)
                self.assertEqual(name, restored[0])
                self.assertEqual(registry.states(value), registry.states(restored))

    def test_aux_reordering_uses_states_for_both_layers(self):
        name = 'minecraft:oak_stairs'
        doc = Document((1, 1, 1), {(0, 0, 0): make_cell((name, 0), (name, 4), {'note': 'visible'})})
        data = to_data(doc)
        data['registry'] = {'version': 'NEMC previous test export', 'sha256': '0' * 64}
        records = dict(registry._decode(name, registry.BLOCKS, registry._records))
        records[0], records[4] = records[4], records[0]
        with patch.dict(registry._records, {name: records}):
            reverse = {registry._state_key(registry.states((name, aux))): aux for aux in records}
            with patch.dict(registry._reverse, {name: reverse}):
                restored = Document.from_data(data).get((0, 0, 0))
                self.assertEqual((name, 4), tuple(restored))
                self.assertEqual((name, 0), restored.background)
                self.assertEqual({'note': 'visible'}, actor_data(restored))

    def test_missing_semantic_state_reports_name_and_source(self):
        data = to_data(Document((1, 1, 1), {(0, 0, 0): STONE}))
        data['materials'][1][1] = {'future_shape': 'unavailable'}
        with self.assertRaisesRegex(ValueError, 'minecraft:stone.*NEMC'):
            Document.from_data(data)
        for field, bad in (('cellVersion', True), ('chunkEncoding', 9), ('registry', {})):
            invalid = to_data(Document((1, 1, 1)))
            invalid[field] = bad
            with self.assertRaises(ValueError):
                Document.from_data(invalid)

    def test_alias_hint_is_verified_and_custom_aux_remains_opaque(self):
        source = semantic_wire.provenance()
        alias = ('minecraft:log', 5)
        row = semantic_wire.encode_material(alias)
        self.assertEqual(alias, semantic_wire.decode_material(row, source))
        row[2] = ['minecraft:log', 1]
        self.assertEqual(registry.canonical(alias), semantic_wire.decode_material(row, source))
        custom = ('example:own_block', 17)
        self.assertEqual(custom, semantic_wire.decode_material(semantic_wire.encode_material(custom), source))
        with self.assertRaises(ValueError):
            semantic_wire.decode_material(['minecraft:stone', 0], source)

    def test_duplicate_resolved_cells_remap_source_chunk_ids(self):
        doc = Document((16, 16, 16))
        doc.blocks.fill_chunk((0, 0, 0), STONE)
        data = to_data(doc)
        data['palette'].append(data['palette'][1])
        data['chunks'][0][3] = 2
        restored = Document.from_data(data)
        self.assertEqual(doc.blocks, restored.blocks)
        self.assertEqual(2, len(restored.blocks.palette))
        stream = list(packets(doc))
        stream[0]['paletteCount'] = 3
        next(packet for packet in stream if packet['kind'] == 'palette')['rows'].append(1)
        next(packet for packet in stream if packet['kind'] == 'chunks')['rows'][0][3] = 2
        receiver = Receiver()
        for packet in stream:
            receiver.feed(packet)
        self.assertEqual(doc.blocks, receiver.result.blocks)

    def test_shared_material_table_is_small_for_unique_actors(self):
        doc = Document((16, 1, 1), {(x, 0, 0): make_cell(('minecraft:chest', 0), AIR, {'x': x})
                                   for x in range(16)})
        data = to_data(doc)
        self.assertEqual(2, len(data['materials']))
        self.assertEqual(17, len(data['palette']))
        self.assertEqual(doc.blocks, Document.from_data(json.loads(json.dumps(data))).blocks)
        shared = list(encode_steps(doc))[-1]['text']
        self.assertTrue(shared.startswith('MP4:'))
        self.assertEqual(doc.blocks, list(decode_steps(shared))[-1]['document'].blocks)

    def test_new_material_packets_cannot_be_used_without_version(self):
        stream = list(packets(Document((1, 1, 1))))
        stream[0].pop('version')
        receiver = Receiver()
        with self.assertRaises(ValueError):
            for packet in stream:
                receiver.feed(packet)

    def test_fragmented_inventory_preserves_empty_render_and_typed_nbt(self):
        items = [{'__type__': 'TAG_Compound', '__value__': {
            'Slot': {'__type__': 'TAG_Byte', '__value__': slot},
            'Name': {'__type__': 'TAG_String', '__value__': 'minecraft:written_book'},
            'tag': {'pages': ['book page ' + str(slot) + ':' + 'snow ' * 512]},
        }} for slot in range(27)]
        actor = {'__modern_projection_actor__': 1, 'render': {},
                 'nbt': {'__type__': 'TAG_Compound', '__value__': {'Items': items}}}
        doc = Document((1, 1, 1), {(0, 0, 0): make_cell(('minecraft:chest', 0), AIR, actor)})
        stream = list(packets(doc))
        self.assertGreater(sum(packet['kind'] == 'palette_part' for packet in stream), 1)
        receiver = Receiver()
        for packet in stream:
            receiver.feed(json.loads(json.dumps(packet)))
        self.assertEqual(actor, actor_data(receiver.result.get((0, 0, 0))))
        shared = list(encode_steps(doc))[-1]['text']
        restored = list(decode_steps(shared))[-1]['document']
        self.assertEqual(actor, actor_data(restored.get((0, 0, 0))))

    def test_mp4_accepts_more_than_legacy_record_count_without_partial_result(self):
        doc = Document((64, 1, 64), {
            (index % 64, 0, index // 64): make_cell(('minecraft:chest', 0), AIR,
                                                     {'index': index, 'text': 'x' * 6000})
            for index in range(2050)})
        self.assertGreater(len(list(packets(doc))), 2048)
        shared = list(encode_steps(doc))[-1]['text']
        steps = list(decode_steps(shared))
        self.assertTrue(all('document' not in step for step in steps[:-1]))
        self.assertEqual(doc.blocks, steps[-1]['document'].blocks)

    def test_partial_cell_cannot_precede_material_table(self):
        stream = list(packets(Document((1, 1, 1))))
        receiver = Receiver()
        receiver.feed(stream[0])
        with self.assertRaises(ValueError):
            receiver.feed({'seq': 1, 'kind': 'palette_part', 'text': '[0,0]', 'last': True})
        self.assertIsNone(receiver.result)

    def test_unknown_states_do_not_publish_partially_decoded_document(self):
        stream = list(packets(Document((1, 1, 1), {(0, 0, 0): STONE})))
        next(packet for packet in stream if packet['kind'] == 'materials')['rows'][1][1] = {'future': True}
        receiver = Receiver()
        with self.assertRaisesRegex(ValueError, 'minecraft:stone'):
            for packet in stream:
                receiver.feed(packet)
        self.assertIsNone(receiver.result)


class CompactChunkTests(unittest.TestCase):
    def test_each_layout_round_trips_all_bit_widths_and_extreme_ids(self):
        randomizer = random.Random(729)
        for count in (1, 2, 3, 8, 16, 17, 32, 64, 129, 256, 1024, 4096):
            palette = randomizer.sample(range(65536), count)
            values = [palette[index % count] for index in range(4096)]
            randomizer.shuffle(values)
            for mode, raw in compact_chunk.candidates(values).items():
                self.assertEqual(values, list(compact_chunk.decode(envelope(mode, raw))))
            chosen = compact_chunk.encode(values)
            minimum = min(len(zlib.compress(raw, 6)) for raw in compact_chunk.candidates(values).values())
            self.assertEqual(minimum, len(base64.b64decode(chosen[3:])))

    def test_uniform_chunks_keep_integer_representation(self):
        self.assertEqual([0, 0, 0, 65535], encode_chunk((0, 0, 0), 65535, 1))

    def test_malformed_lengths_ids_and_decompression_are_bounded(self):
        invalid = [envelope('u', b'x'), envelope('r', struct.pack('<HH', 4097, 1)),
                   envelope('r', struct.pack('<HH', 0, 1)),
                   envelope('s', struct.pack('<HHH', 1, 4096, 1)),
                   envelope('s', struct.pack('<HHHHH', 2, 1, 1, 1, 2)),
                   envelope('p', struct.pack('<HB', 0, 1)),
                   envelope('p', struct.pack('<HBHH', 2, 1, 7, 7) + b'\0' * 512),
                   envelope('u', b'x' * (compact_chunk.MAX_RAW + 1)), '2u:AAAA']
        valid = compact_chunk.encode([0] * 4096)
        packed = base64.b64decode(valid[3:])
        invalid += [valid[:3] + base64.b64encode(packed[:-1]).decode('ascii'),
                    valid[:3] + base64.b64encode(packed + b'junk').decode('ascii')]
        for payload in invalid:
            with self.assertRaises(ValueError, msg=payload[:16]):
                compact_chunk.decode(payload)


class PreferenceMigrationTests(unittest.TestCase):
    class Bridge(object):
        def __init__(self, preferences):
            self.preferences = copy.deepcopy(preferences)
        def load_preferences(self):
            return copy.deepcopy(self.preferences)
        def save_preferences(self, value):
            self.preferences = copy.deepcopy(value)
        def load_library(self):
            return None
        def player_origin(self):
            return (0, 64, 0)

    def initialize(self, bridge):
        session = Session(bridge)
        session.refresh_preview = lambda: None
        session.initialize()
        return session

    def test_legacy_preferences_upgrade_without_losing_palette(self):
        bridge = self.Bridge({'palette': [list(STONE), ['example:own_block', 4]], 'spectrum_speed': 2.})
        session = self.initialize(bridge)
        expected = list(session.palette)
        session.save_preferences()
        self.assertEqual(2, bridge.preferences['version'])
        self.assertEqual(expected, self.initialize(bridge).palette)

    def test_unresolved_preferences_are_preserved_when_other_settings_change(self):
        data = {'version': 2, 'cellVersion': 1, 'registry': semantic_wire.provenance(),
                'palette': [['minecraft:stone', {'missing_state': True}]]}
        bridge = self.Bridge(data)
        session = self.initialize(bridge)
        session.spectrum_speed = 4.
        session.save_preferences()
        self.assertEqual(data['palette'], bridge.preferences['palette'])
        self.assertEqual(4., bridge.preferences['spectrum_speed'])

    def test_unknown_legacy_aux_is_not_discarded_during_preferences_or_library_restart(self):
        old = ('minecraft:stone', 12345)
        bridge = self.Bridge({'palette': [list(old)]})
        entry = {'id': 7, 'data': {'version': 1, 'name': 'legacy', 'size': [1, 1, 1],
                                  'blocks': [[0, 0, 0, old[0], old[1]]]}}
        bridge.load_library = lambda: {'serial': 7, 'buildings': [copy.deepcopy(entry)]}
        session = self.initialize(bridge)
        session.spectrum_speed = 4.
        session.save_preferences()
        self.assertEqual([list(old)], bridge.preferences['palette'])
        self.assertEqual([entry], session.library)
        session.load(7)
        self.assertEqual(old, session.editor.document.get((0, 0, 0)))

    def test_unresolved_inline_archive_survives_initialization_and_rename(self):
        data = to_data(Document((1, 1, 1), {(0, 0, 0): STONE}, name='future'))
        data['materials'][1][1] = {'future': True}
        entries = [{'id': 7, 'data': data}]
        bridge = self.Bridge({})
        bridge.load_library = lambda: {'serial': 7, 'buildings': copy.deepcopy(entries)}
        saved = []
        bridge.save_library = lambda value: saved.append(copy.deepcopy(value)) or True
        session = self.initialize(bridge)
        self.assertEqual(entries, session.library)
        session.rename(7, 'preserved')
        self.assertEqual(data['materials'], saved[-1]['buildings'][0]['data']['materials'])
        self.assertEqual('preserved', saved[-1]['buildings'][0]['data']['name'])


class ArchiveLimitTests(unittest.TestCase):
    def test_oversized_archive_does_not_publish_an_unloadable_index(self):
        from projection import archive
        writes, published = [], []
        bridge = type('Bridge', (), {'save_archive_page':
                                    lambda self, identity, page, value: writes.append(page) or True})()
        doc = Document((1, 1, 1), {(0, 0, 0): make_cell(('minecraft:chest', 0), AIR,
                                                      {'text': 'x' * 100000})})
        with patch.object(archive, 'MAX_PAGES', 1), self.assertRaises(ValueError):
            for step in archive.save_steps(bridge, doc, 7):
                if isinstance(step, dict):
                    published.append(step)
        self.assertEqual([], published)
        self.assertEqual([0], writes)


if __name__ == '__main__':
    unittest.main()

import copy
import base64
import json
import importlib.util
import sys
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.archive import load_steps, save_steps
from projection.cell import (Cell, actor_data, background, decode, encode, foreground,
                             has_complete_cells, layer, make_cell, replace_layer)
from projection.model import AIR, Document, Editor, close_group_selection
from projection.sharing_codec import encode_steps, decode_steps, split_text, Inbox
from projection.transfer import packets, Receiver

STONE = ('minecraft:stone', 0)
GLASS = ('minecraft:glass', 0)
DIRT = ('minecraft:dirt', 0)
GOLD = ('minecraft:gold_block', 0)


class ArchiveBridge(object):
    def __init__(self):
        self.pages = {}

    def save_archive_page(self, identity, page, value):
        self.pages[(identity, page)] = copy.deepcopy(value)
        return True

    def load_archive_page(self, identity, page):
        return copy.deepcopy(self.pages.get((identity, page)))


def finish(generator):
    return list(generator)[-1]


def legacy_share_without_packet_versions(document):
    records = []
    for packet in packets(document):
        packet = dict(packet)
        packet.pop('version', None)
        records.append(json.dumps(packet, ensure_ascii=True, separators=(',', ':')) + '\n')
    raw = ''.join(records).encode('ascii')
    return 'MP2:' + base64.b64encode(zlib.compress(raw)).decode('ascii') + ':%08x' % (zlib.crc32(raw) & 0xffffffff)


class CompleteCellTests(unittest.TestCase):
    def payload(self):
        return {
            'wrapped': {'__type__': 'TAG_Int', '__value__': 7},
            'bool': True,
            'int': 7,
            'large': 1 << 40,
            'float': 1.25,
            'bytes': b'\x00\xff',
            'text': 'snow 雪',
            'list': [False, 3, 'x'],
            'tuple': (1, 'x'),
            'nested': {'inner': [2.5, None]},
        }

    def test_cell_keeps_pair_view_and_compares_complete_contents(self):
        nbt = self.payload()
        cell = make_cell(STONE, GLASS, nbt)
        self.assertIsInstance(cell, Cell)
        self.assertEqual(2, len(cell))
        self.assertEqual(STONE, tuple(cell))
        self.assertEqual(STONE, foreground(cell))
        self.assertEqual(GLASS, background(cell))
        self.assertEqual(nbt, actor_data(cell))
        self.assertNotEqual(make_cell(STONE, DIRT, nbt), cell)
        changed = make_cell(STONE, GLASS, dict(nbt, bool=False))
        self.assertNotEqual(changed, cell)
        self.assertEqual(2, len(set((cell, changed))))

    def test_nbt_copy_and_deepcopy_are_isolated(self):
        original = self.payload()
        cell = make_cell(STONE, GLASS, original)
        original['nested']['inner'].append('changed')
        first = actor_data(cell)
        self.assertNotIn('changed', first['nested']['inner'])
        first['nested']['inner'].append('also changed')
        self.assertNotIn('also changed', actor_data(cell)['nested']['inner'])
        self.assertIs(copy.copy(cell), cell)
        self.assertIs(copy.deepcopy(cell), cell)
        doc = Document((2, 1, 1), {(0, 0, 0): cell})
        cloned = copy.deepcopy(doc)
        cloned_actor = actor_data(cloned.get((0, 0, 0)))
        cloned_actor['wrapped']['__value__'] = 99
        self.assertEqual(7, actor_data(doc.get((0, 0, 0)))['wrapped']['__value__'])

    def test_cell_wire_encoding_preserves_scalar_and_container_types(self):
        expected = self.payload()
        encoded = encode(make_cell(STONE, GLASS, expected))
        self.assertEqual(3, len(encoded))
        restored = decode(json.loads(json.dumps(encoded)))
        self.assertEqual(expected, actor_data(restored))
        self.assertIs(type(actor_data(restored)['bool']), bool)
        self.assertIs(type(actor_data(restored)['list']), list)
        self.assertIs(type(actor_data(restored)['tuple']), tuple)
        self.assertIs(type(actor_data(restored)['bytes']), bytes)
        self.assertEqual(STONE, decode(list(STONE)))
        older_rich = {'foreground': list(STONE), 'background': list(GLASS),
                      'nbt': encode(make_cell(STONE, GLASS, expected))[2]}
        self.assertEqual(expected, actor_data(decode(json.loads(json.dumps(older_rich)))))

    def test_invalid_layer_indexes_and_malformed_nbt_are_rejected(self):
        for index in (-1, 2, True, 1.0):
            with self.assertRaises(ValueError):
                layer(make_cell(STONE), index)
            with self.assertRaises(ValueError):
                replace_layer(make_cell(STONE), GLASS, index)
        with self.assertRaises(ValueError):
            decode({'foreground': list(STONE), 'background': list(AIR), 'nbt': ['unknown', 1]})
        with self.assertRaises(ValueError):
            decode({'foreground': ['minecraft:stone', 40000], 'background': list(AIR), 'nbt': ['null']})
        deep = ['null']
        for unused in range(66):
            deep = ['list', [deep]]
        with self.assertRaises(ValueError):
            decode({'foreground': list(STONE), 'background': list(AIR), 'nbt': deep})
        with self.assertRaises(ValueError):
            make_cell(STONE, AIR, {'large': 'x' * (512 * 1024 + 1)})
        duplicate = ['dict', [[['bool', True], ['int', '1']], [['int', '1'], ['int', '2']]]]
        with self.assertRaises(ValueError):
            decode({'foreground': list(STONE), 'background': list(AIR), 'nbt': duplicate})

    def test_background_only_cells_count_as_occupied_and_keep_the_actor(self):
        nbt = {'id': 'Chest', 'x': 10, 'Items': [{'Slot': 0, 'Name': 'minecraft:apple'}]}
        value = make_cell(STONE, GLASS, nbt)
        value = replace_layer(value, DIRT, 1)
        doc = Document((2, 1, 1), {(0, 0, 0): value})
        self.assertEqual(1, len(doc.blocks))
        self.assertEqual(STONE, doc.get_layer((0, 0, 0), 0))
        self.assertEqual(DIRT, doc.get_layer((0, 0, 0), 1))
        self.assertEqual(nbt, actor_data(doc.get((0, 0, 0))))
        self.assertEqual([(STONE, 1), (DIRT, 1)], doc.materials())
        self.assertEqual(1, doc.layer_count(0))

        background_only = Document((1, 1, 1), {(0, 0, 0): make_cell(AIR, GLASS)})
        self.assertEqual(1, len(background_only.blocks))
        self.assertEqual([(GLASS, 1)], background_only.materials())

    def test_legacy_and_complete_document_round_trips_use_gated_versions(self):
        legacy = Document((2, 2, 2), {(1, 1, 1): STONE})
        self.assertEqual(1, legacy.to_data()['version'])
        self.assertEqual(legacy.blocks, Document.from_data(legacy.to_data()).blocks)
        rich = Document((2, 2, 2), {(1, 1, 1): make_cell(STONE, GLASS, self.payload())})
        data = json.loads(json.dumps(rich.to_data()))
        self.assertEqual(4, data['version'])
        self.assertEqual(rich.blocks, Document.from_data(data).blocks)
        self.assertEqual(3, next(iter(packets(rich)))['version'])
        receiver = Receiver()
        for packet in packets(rich):
            receiver.feed(copy.deepcopy(packet))
        self.assertEqual(rich.blocks, receiver.result.blocks)
        rich.blocks[(1, 1, 1)] = AIR
        self.assertFalse(has_complete_cells(rich.blocks))
        self.assertEqual(1, rich.to_data()['version'])

    def test_unversioned_sparse_json_and_legacy_packets_read_as_v1_and_v2(self):
        legacy = Document((2, 2, 2), {(1, 1, 1): STONE})
        old_json = legacy.to_data()
        old_json.pop('version')
        restored = Document.from_data(old_json)
        self.assertEqual(legacy.blocks, restored.blocks)
        self.assertEqual(1, restored.to_data()['version'])

        packets_without_version = [dict(packet) for packet in packets(legacy)]
        for packet in packets_without_version:
            packet.pop('version', None)
        receiver = Receiver()
        for packet in packets_without_version:
            receiver.feed(packet)
        self.assertEqual(legacy.blocks, receiver.result.blocks)
        self.assertEqual(2, receiver.version)

        imported = finish(decode_steps(legacy_share_without_packet_versions(legacy)))['document']
        self.assertEqual(legacy.blocks, imported.blocks)
        upgraded = Document.from_data(imported.to_data())
        self.assertEqual(legacy.blocks, upgraded.blocks)

    def test_missing_versions_never_guess_chunked_or_complete_cell_formats(self):
        rich = Document((1, 1, 1), {(0, 0, 0): make_cell(STONE, GLASS, {'id': 'Chest'})})
        unversioned_rich = rich.to_data()
        unversioned_rich.pop('version')
        with self.assertRaises(ValueError):
            Document.from_data(unversioned_rich)

        legacy = Document((2, 2, 2), {(1, 1, 1): STONE})
        legacy = Document((33, 32, 32), {(1, 1, 1): STONE})
        versionless_chunks = legacy.to_data()
        versionless_chunks.pop('version')
        with self.assertRaises(ValueError):
            Document.from_data(versionless_chunks)

        with self.assertRaises(ValueError):
            Document.from_data(dict(legacy.to_data(), version=True))

        rich_packets = [dict(packet) for packet in packets(rich)]
        rich_packets[0].pop('version')
        receiver = Receiver()
        with self.assertRaises(ValueError):
            for packet in rich_packets:
                receiver.feed(packet)

    def test_rich_cells_round_trip_through_archive_and_share_formats(self):
        doc = Document((3, 1, 1), {(0, 0, 0): make_cell(STONE, GLASS, self.payload())}, name='完整方块')
        bridge = ArchiveBridge()
        metadata = finish(save_steps(bridge, doc, 'rich'))
        self.assertEqual(5, metadata['version'])
        restored = finish(load_steps(bridge, 'rich', metadata))
        self.assertEqual(doc.blocks, restored.blocks)
        shared = finish(encode_steps(doc))['text']
        self.assertTrue(shared.startswith('MP3:'))
        imported = finish(decode_steps(shared))['document']
        self.assertEqual(doc.blocks, imported.blocks)
        segmented = split_text(shared, 256)
        self.assertTrue(all(part.startswith('MPS3:') for part in segmented))
        inbox = Inbox()
        complete = None
        for part in segmented:
            complete = inbox.add(part)
        self.assertEqual(shared, complete)
        self.assertEqual(doc.blocks, finish(decode_steps(complete))['document'].blocks)

        legacy = Document((3, 1, 1), {(0, 0, 0): STONE})
        legacy_meta = finish(save_steps(bridge, legacy, 'legacy'))
        self.assertEqual(3, legacy_meta['version'])
        self.assertEqual(legacy.blocks, finish(load_steps(bridge, 'legacy', legacy_meta)).blocks)

        bad_archive_meta = dict(metadata, version=3)
        with self.assertRaises(ValueError):
            finish(load_steps(bridge, 'rich', bad_archive_meta))
        with self.assertRaises(ValueError):
            finish(load_steps(bridge, 'rich', dict(metadata, version=True)))

    def test_legacy_share_keeps_mp2_and_mps2_envelopes(self):
        shared = finish(encode_steps(Document((2, 1, 1), {(0, 0, 0): STONE})))['text']
        self.assertTrue(shared.startswith('MP2:'))
        segments = split_text(shared, 256)
        self.assertTrue(all(part.startswith('MPS2:') for part in segments))
        inbox = Inbox()
        complete = None
        for part in segments:
            complete = inbox.add(part)
        self.assertEqual(shared, complete)

    def test_palette_data_emits_front_background_and_actor_maps_by_native_index(self):
        actor = {'id': 'Chest', 'Items': [{'Slot': 0, 'Name': 'minecraft:apple'}]}
        doc = Document((2, 3, 4), {
            (1, 0, 0): STONE,
            (0, 1, 2): make_cell(AIR, DIRT),
            (1, 2, 3): make_cell(STONE, GLASS, actor),
        })
        data = doc.palette_data()
        self.assertEqual({STONE: [4, 23]}, data['common'])
        self.assertEqual({DIRT: [10], GLASS: [23]}, data['extra'])
        self.assertEqual({'minecraft:stone': {23: actor}}, data['actor'])
        self.assertEqual((4, 2, 3), data['volume'])

        visible = doc.palette_data(lambda pos: pos != (1, 0, 0))
        self.assertEqual({STONE: [23]}, visible['common'])
        self.assertEqual({DIRT: [10], GLASS: [23]}, visible['extra'])
        self.assertEqual({'minecraft:stone': {23: actor}}, visible['actor'])

    def test_layer_selection_pick_and_edit_state_is_reachable_through_session(self):
        from projection.session import Session
        session = Session(object())
        session.editor = Editor(Document((1, 1, 1), {(0, 0, 0): make_cell(STONE, GLASS)}))
        session.set_editor('edit_layer', 1)
        self.assertEqual(1, session.editor.edit_layer)
        session.editor.source = GLASS
        session.editor.run('select_material')
        self.assertIn((0, 0, 0), session.editor.selection)
        session.editor.material = DIRT
        session.editor.paint_at((0, 0, 0), respect_selection=False)
        self.assertEqual(STONE, foreground(session.editor.document.get((0, 0, 0))))
        self.assertEqual(DIRT, background(session.editor.document.get((0, 0, 0))))

    def test_waterlogged_fence_placement_and_erasure_follow_selected_layer(self):
        fence = ('minecraft:oak_fence', 0)
        water = ('minecraft:water', 0)
        editor = Editor(Document((1, 1, 1)))
        editor.edit_layer = 0
        editor.material = fence
        editor.paint_at((0, 0, 0), respect_selection=False)
        editor.edit_layer = 1
        editor.material = water
        editor.paint_at((0, 0, 0), respect_selection=False)
        self.assertEqual(fence, foreground(editor.document.get((0, 0, 0))))
        self.assertEqual(water, background(editor.document.get((0, 0, 0))))

        editor.edit_layer = 0
        editor.paint_at((0, 0, 0), erase=True, respect_selection=False)
        self.assertEqual(AIR, foreground(editor.document.get((0, 0, 0))))
        self.assertEqual(water, background(editor.document.get((0, 0, 0))))

        editor.edit_layer = 1
        editor.paint_at((0, 0, 0), erase=True, respect_selection=False)
        self.assertEqual(AIR, editor.document.get((0, 0, 0)))

    def test_grouped_placement_erase_selection_copy_and_move_keep_pairs(self):
        from projection.block_groups import group_partner, paired_position

        cases = (
            ((2, 2, 1), (0, 0, 0), ('minecraft:wooden_door', 0)),
            ((1, 1, 2), (0, 0, 0), ('minecraft:bed', 0)),
            ((1, 2, 1), (0, 0, 0), ('minecraft:tall_grass', 0)),
        )
        for size, pos, base in cases:
            with self.subTest(base=base):
                editor = Editor(Document(size))
                editor.material = base
                self.assertEqual(2, editor.paint_at(pos, respect_selection=False))
                offset, reciprocal = group_partner(base)
                partner = tuple(pos[i] + offset[i] for i in range(3))
                self.assertEqual(reciprocal, editor.document.get(partner))
                self.assertEqual(partner, paired_position(
                    lambda target: foreground(editor.document.get(target)) if editor.document.contains(target) else None,
                    pos))
                closed = close_group_selection(editor.document, [pos])
                self.assertEqual({pos, partner}, set(closed))
                editor.select_box(pos, pos)
                editor.run('copy')
                self.assertEqual({pos, partner}, set(editor.clipboard['blocks']))
                editor.paint_at(pos, erase=True, respect_selection=False)
                self.assertEqual(AIR, editor.document.get(pos))
                self.assertEqual(AIR, editor.document.get(partner))

    @unittest.skipUnless(importlib.util.find_spec('projection.state_transform'),
                         'state transform dependency is integrated on the transform branch')
    def test_group_move_preserves_pair(self):
        from projection.block_groups import group_partner, paired_position
        lower = ('minecraft:wooden_door', 0)
        upper = group_partner(lower)[1]
        editor = Editor(Document((3, 2, 1), {(0, 0, 0): lower, (0, 1, 0): upper}))
        editor.select_box((0, 0, 0), (0, 0, 0))
        editor.step = 1
        editor.run('move_xp')
        self.assertEqual(lower, editor.document.get((1, 0, 0)))
        self.assertEqual(upper, editor.document.get((1, 1, 0)))
        self.assertEqual((1, 1, 0), paired_position(
            lambda target: foreground(editor.document.get(target)) if editor.document.contains(target) else None,
            (1, 0, 0)))

    def test_group_batch_fill_replace_and_malformed_pair_validation(self):
        from projection.block_groups import group_partner

        lower = ('minecraft:wooden_door', 0)
        upper = group_partner(lower)[1]
        editor = Editor(Document((2, 2, 1)))
        editor.select_box((0, 0, 0), (0, 1, 0))
        editor.material = lower
        self.assertEqual(2, editor.run('fill'))
        self.assertEqual(lower, editor.document.get((0, 0, 0)))
        self.assertEqual(upper, editor.document.get((0, 1, 0)))
        editor.source = lower
        editor.material = STONE
        editor.run('replace')
        self.assertEqual(STONE, editor.document.get((0, 0, 0)))
        self.assertEqual(STONE, editor.document.get((0, 1, 0)))

        malformed = Document((1, 2, 1), {(0, 1, 0): upper})
        with self.assertRaises(ValueError):
            close_group_selection(malformed, [(0, 1, 0)], strict=True)

    def test_pale_moss_carpet_upper_bit_is_not_a_multiblock_pair(self):
        from projection.block_groups import group_is_upper, group_partner, preserve_group_part

        carpet = ('minecraft:pale_moss_carpet', 1)
        self.assertIsNone(group_partner(carpet))
        self.assertFalse(group_is_upper(carpet))
        self.assertEqual(carpet, preserve_group_part(
            carpet, ('minecraft:wooden_door', 0)))
        editor = Editor(Document((3, 1, 1), {(1, 0, 0): carpet}))
        self.assertEqual({(1, 0, 0)}, set(close_group_selection(
            editor.document, [(1, 0, 0)])))
        editor.select_box((1, 0, 0), (1, 0, 0))
        editor.run('copy')
        self.assertEqual({(0, 0, 0)}, set(editor.clipboard['blocks']))
        editor.run('erase')
        self.assertEqual(AIR, editor.document.get((1, 0, 0)))

    def test_every_dumped_multiblock_half_has_a_reciprocal_state(self):
        from projection import block_registry as registry
        from projection.block_groups import group_partner

        checked = 0
        for name in registry.BLOCKS:
            for aux in registry.aux_values(name):
                value = (name, aux)
                properties = registry.states(value)
                paired = ('upper_block_bit' in properties and
                          name != 'minecraft:pale_moss_carpet')
                paired = paired or properties.get('sea_grass_type') in (
                    'double_bot', 'double_top')
                paired = paired or 'head_piece_bit' in properties
                relation = group_partner(value)
                if not paired:
                    self.assertIsNone(relation, value)
                    continue
                self.assertIsNotNone(relation, value)
                offset, partner = relation
                reverse = group_partner(partner)
                self.assertEqual(tuple(-v for v in offset), reverse[0], value)
                self.assertEqual(value, reverse[1], value)
                checked += 1
        self.assertGreater(checked, 700)

    def test_replacing_pale_moss_carpet_with_door_builds_lower_and_upper_halves(self):
        from projection.block_groups import group_partner

        carpet = ('minecraft:pale_moss_carpet', 1)
        lower = ('minecraft:wooden_door', 0)
        upper = group_partner(lower)[1]
        editor = Editor(Document((1, 2, 1), {
            (0, 0, 0): carpet, (0, 1, 0): carpet}))
        editor.select_box((0, 0, 0), (0, 1, 0))
        editor.source = carpet
        editor.material = lower
        self.assertEqual(2, editor.run('replace'))
        self.assertEqual(lower, editor.document.get((0, 0, 0)))
        self.assertEqual(upper, editor.document.get((0, 1, 0)))

    def test_replacing_door_with_pale_moss_carpet_preserves_requested_variant(self):
        from projection.block_groups import group_partner

        lower = ('minecraft:wooden_door', 0)
        upper = group_partner(lower)[1]
        carpet = ('minecraft:pale_moss_carpet', 1)
        editor = Editor(Document((1, 2, 1), {
            (0, 0, 0): lower, (0, 1, 0): upper}))
        editor.select_box((0, 0, 0), (0, 1, 0))
        editor.source = lower
        editor.material = carpet
        self.assertEqual(2, editor.run('replace'))
        self.assertEqual(carpet, editor.document.get((0, 0, 0)))
        self.assertEqual(carpet, editor.document.get((0, 1, 0)))

    def test_double_chest_nbt_links_close_copy_move_rotate_and_erase_as_a_group(self):
        from projection.nbt_spatial import scalar
        left, right = (1, 0, 1), (2, 0, 1)
        left_actor = {'id': 'Chest', 'x': 1, 'y': 0, 'z': 1,
                      'pairx': 2, 'pairz': 1, 'Items': []}
        right_actor = {'id': 'Chest', 'x': 2, 'y': 0, 'z': 1,
                       'pairx': 1, 'pairz': 1, 'Items': []}
        editor = Editor(Document((5, 1, 4), {
            left: make_cell(('minecraft:chest', 0), AIR, left_actor),
            right: make_cell(('minecraft:chest', 0), AIR, right_actor),
        }))

        editor.select_box(left, left)
        self.assertEqual({left, right}, set(editor.selection))
        editor.run('copy')
        self.assertEqual({(0, 0, 0), (1, 0, 0)}, set(editor.clipboard['blocks']))
        editor.step = 1
        editor.run('move_xp')
        moved_left, moved_right = (2, 0, 1), (3, 0, 1)
        self.assertEqual(3, scalar(actor_data(editor.document.get(moved_left)), 'pairx'))
        self.assertEqual(2, scalar(actor_data(editor.document.get(moved_right)), 'pairx'))

        editor.select_box(moved_left, moved_left)
        editor.run('rotate_y90')
        rotated = set(editor.selection)
        self.assertEqual({(2, 0, 1), (2, 0, 2)}, rotated)
        for pos in rotated:
            pair_x = scalar(actor_data(editor.document.get(pos)), 'pairx')
            pair_z = scalar(actor_data(editor.document.get(pos)), 'pairz')
            self.assertIn((pair_x, 0, pair_z), rotated)
        editor.selection = {next(iter(rotated))}
        editor.run('erase')
        self.assertTrue(all(editor.document.get(pos) == AIR for pos in rotated))

        adjacent = Editor(Document((4, 1, 2), {
            (1, 0, 0): ('minecraft:chest', 0),
            (2, 0, 0): ('minecraft:chest', 0),
        }))
        adjacent.select_box((1, 0, 0), (1, 0, 0))
        self.assertEqual({(1, 0, 0), (2, 0, 0)}, set(adjacent.selection))
        adjacent.run('erase')
        self.assertEqual(0, len(adjacent.document.blocks))

    def test_large_job_fill_and_replace_keep_door_and_plant_pairs(self):
        from projection.block_groups import group_partner

        for base in (('minecraft:wooden_door', 0),
                     ('minecraft:tall_grass', 0)):
            with self.subTest(base=base):
                editor = Editor(Document((64, 128, 64)))
                offset, reciprocal = group_partner(base)
                pos = (4, 4, 4)
                partner = tuple(pos[i] + offset[i] for i in range(3))
                editor.select_box(pos, partner)
                editor.material = base
                self.assertEqual(2, editor.run('fill'))
                self.assertEqual(base, editor.document.get(pos))
                self.assertEqual(reciprocal, editor.document.get(partner))
                editor.source = base
                editor.material = STONE
                self.assertEqual(2, editor.run('replace'))
                self.assertEqual(STONE, editor.document.get(pos))
                self.assertEqual(STONE, editor.document.get(partner))

    def test_rich_and_legacy_share_versions_cannot_be_mislabeled(self):
        rich = finish(encode_steps(Document((1, 1, 1), {
            (0, 0, 0): make_cell(STONE, GLASS, {'id': 'Chest'})})))['text']
        rich_segment = split_text(rich, 256)[0].replace('MPS3:', 'MPS2:', 1)
        inbox = Inbox()
        self.assertIsNone(inbox.add(split_text(rich, 256)[0]))
        with self.assertRaises(ValueError):
            inbox.add(rich_segment)
        legacy = finish(encode_steps(Document((1, 1, 1))) )['text']
        legacy_as_rich = split_text(legacy, 256)[0].replace('MPS2:', 'MPS3:', 1)
        with self.assertRaises(ValueError):
            Inbox().add(legacy_as_rich)

    def test_layer_edit_and_undo_preserve_the_other_layer_and_nbt(self):
        actor = {'id': 'Chest', 'x': 1, 'Items': [{'Slot': 0, 'tag': {'Name': 'apple'}}]}
        cell = make_cell(STONE, GLASS, actor)
        editor = Editor(Document((3, 1, 1), {(1, 0, 0): cell}))
        editor.select_box((1, 0, 0), (1, 0, 0))
        editor.edit_layer = 1
        editor.material = DIRT
        self.assertEqual(1, editor.run('fill'))
        changed = editor.document.get((1, 0, 0))
        self.assertEqual(STONE, foreground(changed))
        self.assertEqual(DIRT, background(changed))
        self.assertEqual(actor, actor_data(changed))
        self.assertTrue(editor.undo())
        self.assertEqual(cell, editor.document.get((1, 0, 0)))
        self.assertTrue(editor.redo())
        self.assertEqual(changed, editor.document.get((1, 0, 0)))

    def test_job_paste_undo_and_cancel_do_not_publish_partial_cells(self):
        cell = make_cell(STONE, GLASS, self.payload())
        editor = Editor(Document((33, 1, 1), {(0, 0, 0): cell}))
        editor.select_box((0, 0, 0), (0, 0, 0))
        editor.run('copy')
        editor.start = (5, 0, 0)
        self.assertEqual(1, editor.run('paste'))
        self.assertEqual(cell, editor.document.get((5, 0, 0)))
        self.assertTrue(editor.undo())
        self.assertEqual(AIR, editor.document.get((5, 0, 0)))
        self.assertTrue(editor.redo())
        self.assertEqual(cell, editor.document.get((5, 0, 0)))

        large = Editor(Document((64, 128, 64), {(0, 0, 0): cell}))
        before, revision = large.document.blocks.copy(), large.revision
        from projection.jobs import EditJob
        job = EditJob(large, 'fill')
        job.step(budget=1, seconds=10)
        job.cancel()
        job.step()
        self.assertTrue(job.cancelled)
        self.assertEqual(before, large.document.blocks)
        self.assertEqual(revision, large.revision)
        self.assertFalse(large.undo_stack)

    def test_copy_transform_and_paste_rebase_only_block_entity_root_coordinates(self):
        from projection.nbt_spatial import root_payload, scalar
        actor = {'__type__': 'TAG_Compound', '__value__': {
            'x': {'__type__': 'TAG_Int', '__value__': 1},
            'y': {'__type__': 'TAG_Int', '__value__': 0},
            'z': {'__type__': 'TAG_Int', '__value__': 0},
            'pairx': {'__type__': 'TAG_Int', '__value__': 2},
            'pairz': {'__type__': 'TAG_Int', '__value__': 0},
            'Items': [{'tag': {'x': 900, 'y': 901, 'z': 902}}],
        }}
        cell = make_cell(STONE, AIR, actor)
        editor = Editor(Document((5, 1, 1), {(1, 0, 0): cell}))
        editor.select_box((1, 0, 0), (1, 0, 0))
        editor.run('copy')
        editor.start = (4, 0, 0)
        editor.run('paste')
        pasted = root_payload(actor_data(editor.document.get((4, 0, 0))))
        self.assertEqual((4, 0, 0), tuple(scalar(pasted, key) for key in ('x', 'y', 'z')))
        self.assertEqual((5, 0), (scalar(pasted, 'pairx'), scalar(pasted, 'pairz')))
        self.assertEqual({'x': 900, 'y': 901, 'z': 902}, pasted['Items'][0]['tag'])

    def test_transform_rotates_typed_chest_pair_coordinates(self):
        from projection.nbt_spatial import root_payload, scalar
        actor = {'__type__': 'TAG_Compound', '__value__': {
            'x': {'__type__': 'TAG_Int', '__value__': 1},
            'y': {'__type__': 'TAG_Int', '__value__': 0},
            'z': {'__type__': 'TAG_Int', '__value__': 1},
            'pairx': {'__type__': 'TAG_Int', '__value__': 2},
            'pairz': {'__type__': 'TAG_Int', '__value__': 1},
        }}
        editor = Editor(Document((3, 1, 3), {
            (1, 0, 1): make_cell(STONE, AIR, actor)}))
        editor.select_box((0, 0, 0), (2, 0, 2))
        editor.run('mirror_x')
        transformed = root_payload(actor_data(editor.document.get((1, 0, 1))))
        self.assertEqual((0, 1), (scalar(transformed, 'pairx'),
                                 scalar(transformed, 'pairz')))
        self.assertEqual('TAG_Int', transformed['pairx']['__type__'])
        self.assertEqual('TAG_Int', transformed['pairz']['__type__'])

    def test_cell_and_history_memory_estimates_include_large_nbt(self):
        from projection import model
        payload = 'x' * 4096
        first = make_cell(STONE, AIR, {'id': 'Chest', 'payload': payload})
        second = make_cell(STONE, AIR, {'id': 'Chest', 'payload': payload + 'y'})
        doc = Document((2, 1, 1), {(0, 0, 0): first})
        self.assertGreater(doc.blocks.memory_bytes(), 4096)
        self.assertGreater(first.memory_bytes(), 4096)

        editor = Editor(doc)
        previous_limit = model.MAX_HISTORY_BYTES
        model.MAX_HISTORY_BYTES = 1024
        try:
            editor._remember('first', {(0, 0, 0): (AIR, first)})
            editor._remember('second', {(1, 0, 0): (AIR, second)})
        finally:
            model.MAX_HISTORY_BYTES = previous_limit
        self.assertEqual(1, len(editor.undo_stack))
        self.assertEqual('second', editor.undo_stack[0][0])


if __name__ == '__main__':
    unittest.main()

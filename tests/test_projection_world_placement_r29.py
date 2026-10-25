"""Prepared projection snapshots cross the real semantic upload/world writer.

The SDK adapter is the existing server fixture: these are CPU integration
checks, not evidence of native game placement or visual acceptance.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack'))
import test_server_stream as server_fixture
from modern_projection import server_system as server
from modern_projection.projection.block_groups import hydrate_chest_actor
from modern_projection.projection.block_registry import from_states, states
from modern_projection.projection.cell import AIR, actor_data, make_cell
from modern_projection.projection.model import Document
from modern_projection.projection.nbt_spatial import root_payload, scalar
from modern_projection.projection.projection_transform import snapshot
from modern_projection.projection.transfer import packets
from modern_projection.projection.visible_actor import entity_nbt


CHEST = ('minecraft:chest', 2)
WATER = ('minecraft:water', 0)
ORIGIN = (13, 70, -11)
SOURCE_POSITIONS = ((0, 1, 0), (1, 1, 0), (3, 0, 2), (2, 2, 1))
CASES = (
    ('rotate_y90', (3, 3, 4), ((2, 1, 0), (2, 1, 1), (0, 0, 3), (1, 2, 2)), 'east', 2, False, 'z'),
    ('rotate_y180', (4, 3, 3), ((3, 1, 2), (2, 1, 2), (0, 0, 0), (1, 2, 1)), 'south', 1, False, 'x'),
    ('rotate_y270', (3, 3, 4), ((0, 1, 3), (0, 1, 2), (2, 0, 0), (1, 2, 1)), 'west', 3, False, 'z'),
    ('mirror_x', (4, 3, 3), ((3, 1, 0), (2, 1, 0), (0, 0, 2), (1, 2, 1)), 'north', 1, False, 'x'),
    ('mirror_y', (4, 3, 3), ((0, 1, 0), (1, 1, 0), (3, 2, 2), (2, 0, 1)), 'north', 0, True, 'x'),
    ('mirror_z', (4, 3, 3), ((0, 1, 2), (1, 1, 2), (3, 0, 0), (2, 2, 1)), 'south', 0, False, 'x'),
)


def tag(kind, value):
    return {'__type__': kind, '__value__': value}


def source_document():
    document = Document((4, 3, 3), name='Projection world R29', biome='swampland')
    for index, pos in enumerate(SOURCE_POSITIONS[:2]):
        partner = SOURCE_POSITIONS[1 - index]
        actor = {
            'id': tag(8, 'Chest'),
            'x': tag(3, pos[0]), 'y': tag(3, pos[1]), 'z': tag(3, pos[2]),
            'pairx': tag(3, partner[0]), 'pairz': tag(3, partner[2]),
            'pairlead': tag(1, 1 - index),
            'Items': tag(9, [{'Slot': tag(1, index), 'Name': tag(8, 'minecraft:stone'),
                              'tag': {'x': 913, 'z': -57, 'Command': 'tp @p 913 70 -57'}}]),
        }
        document.set_cell(pos, hydrate_chest_actor(make_cell(CHEST, nbt=actor), pos))
    document.set_cell(SOURCE_POSITIONS[2], make_cell(('minecraft:oak_stairs', 0), WATER))
    document.set_cell(SOURCE_POSITIONS[3], ('minecraft:spruce_log', 1))
    return document


def world_position(local, origin=ORIGIN):
    return tuple(local[axis] + origin[axis] for axis in range(3))


def text_tree(value):
    if isinstance(value, bytes):
        return value.decode('utf8')
    if isinstance(value, dict):
        return dict((text_tree(key), text_tree(item)) for key, item in value.items())
    return value


class ProjectionWorldPlacementTests(unittest.TestCase):
    # Share the established SDK fixture without inheriting/rerunning its tests.
    setUp = server_fixture.ServerStreamTests.setUp
    read_entity = server_fixture.ServerStreamTests.read_entity
    read_palette = server_fixture.ServerStreamTests.read_palette
    write = server_fixture.ServerStreamTests.write
    set_actor = server_fixture.ServerStreamTests.set_actor
    set_liquid = server_fixture.ServerStreamTests.set_liquid
    finish = server_fixture.ServerStreamTests.finish

    def write_palette(self, palette, dimension, pos, rotation, conflict):
        result = server_fixture.ServerStreamTests.write_palette(
            self, palette, dimension, pos, rotation, conflict)
        for key, positions in palette.data['common'].items():
            self.blocks[pos] = self.palette_value(key, palette.data.get('states', {}))
        for key, positions in palette.data.get('extra', {}).items():
            material = self.palette_value(key, palette.data.get('extraStates', {}))
            if material == AIR:
                self.liquids.pop(pos, None)
            else:
                self.liquids[pos] = dict(zip(('name', 'aux'), material))
        return result

    @staticmethod
    def palette_value(key, records):
        name, aux = text_tree(key[0]), key[1]
        properties = records.get(key)
        return (from_states(name, text_tree(properties)) if properties is not None else
                (name, aux))

    def upload(self, document, request=1, action='apply', origin=ORIGIN, include_air=False):
        for packet in packets(document):
            self.host.request({
                '__id__': 'player', 'request': request,
                'action': action if packet['seq'] == 0 else 'upload',
                'origin': origin, 'includeAir': include_air, 'stream': packet,
            })

    def clear_records(self):
        for collection in (self.blocks, self.liquids, self.actors, self.writes,
                           self.palette_writes, self.actor_writes, self.replies):
            collection.clear()

    def test_six_prepared_transforms_preserve_world_states_layers_and_typed_chest_pairs(self):
        source = source_document()
        saved = source.to_data()
        for index, case in enumerate(CASES, 1):
            operation, size, positions, facing, stair_direction, upper, log_axis = case
            with self.subTest(operation=operation):
                self.clear_records()
                document = snapshot(source, (operation,))
                frozen = document.to_data()
                self.upload(document, request=index)
                self.finish()
                self.assertEqual(size, document.size)
                self.assertEqual(set(map(world_position, positions)), set(self.blocks))
                self.assertEqual({'total': 4, 'processed': 4, 'written': 4, 'failed': 0},
                                 self.replies[-1][2]['progress'])
                self.assertTrue(all(rotation == 0 for data, dim, pos, rotation, conflict
                                    in self.palette_writes), 'states already transformed; native rotation must stay zero')
                for pos in positions[:2]:
                    self.assertEqual({'minecraft:cardinal_direction': facing},
                                     states(self.blocks[world_position(pos)]))
                stair = world_position(positions[2])
                self.assertEqual({'weirdo_direction': stair_direction, 'upside_down_bit': upper},
                                 states(self.blocks[stair]))
                self.assertEqual({'name': WATER[0], 'aux': WATER[1]}, self.liquids[stair])
                self.assertEqual({'pillar_axis': log_axis}, states(self.blocks[world_position(positions[3])]))
                native_actors = dict((pos, root_payload(actor)) for dim, pos, actor in self.actor_writes)
                self.assertEqual(set(map(world_position, positions[:2])), set(native_actors))
                for chest_index, pos in enumerate(positions[:2]):
                    root = native_actors[world_position(pos)]
                    partner = world_position(positions[1 - chest_index])
                    self.assertEqual(world_position(pos), tuple(scalar(root, axis) for axis in ('x', 'y', 'z')))
                    self.assertEqual((partner[0], partner[2]), (scalar(root, 'pairx'), scalar(root, 'pairz')))
                    self.assertEqual(3, root[b'x'][b'__type__'])
                    self.assertEqual(1, root[b'pairlead'][b'__type__'])
                    mirrored = operation in ('mirror_x', 'mirror_z')
                    self.assertEqual(chest_index if mirrored else 1 - chest_index, scalar(root, 'pairlead'))
                    original_nbt = entity_nbt(actor_data(source.get(SOURCE_POSITIONS[chest_index])))
                    self.assertEqual(server.WorldAdapter._native_tree(original_nbt['Items']), root[b'Items'])
                    self.assertNotIn(b'chestIsLargeChest', root)
                    self.assertNotIn(b'facingDirection', root)
                self.assertEqual(saved, source.to_data())
                self.assertEqual(frozen, document.to_data())

    def test_progress_checks_the_transformed_target_after_streamed_apply(self):
        document = snapshot(source_document(), ('rotate_y90', 'mirror_x'))
        self.upload(document, request=11)
        self.finish()
        self.upload(document, request=12, action='check')
        self.finish()
        self.assertEqual({'total': 4, 'correct': 4, 'missing': 0, 'wrong': 0},
                         self.replies[-1][2]['progress'])
        self.upload(source_document(), request=13, action='check')
        self.finish()
        self.assertLess(self.replies[-1][2]['progress']['correct'], 4)
        self.assertEqual(4, len(self.writes))

    def test_server_request_pins_original_origin_through_later_upload_packets(self):
        document = snapshot(source_document(), ('mirror_z',))
        stream = list(packets(document))
        self.host.request({'__id__': 'player', 'request': 15, 'action': 'apply',
                           'origin': ORIGIN, 'stream': stream[0]})
        for packet in stream[1:]:
            self.host.request({'__id__': 'player', 'request': 15, 'action': 'upload',
                               'origin': (100, 64, 100), 'stream': packet})
        self.finish()
        expected = set(world_position(local) for local in document.blocks)
        self.assertEqual(expected, set(self.blocks))
        self.assertFalse(any(pos[0] >= 100 for pos in self.blocks))

    def test_cancelled_transformed_write_stops_future_cells_and_reports_prefix(self):
        document = snapshot(source_document(), ('rotate_y270',))
        self.upload(document, request=17)
        job = self.host.jobs['player'][2]
        original_step = job.step
        job.step = lambda budget=2048: original_step(1)
        self.host.tick()
        self.assertEqual(1, len(self.writes))
        first = self.writes[0]
        self.host.request({'__id__': 'player', 'request': 17, 'action': 'cancel'})
        self.host.tick()
        self.assertEqual([first], self.writes)
        self.assertNotIn('player', self.host.jobs)
        self.assertEqual({'total': 4, 'processed': 1, 'written': 1, 'failed': 0},
                         self.replies[-1][2]['progress'])

    def test_include_air_uses_transformed_bounds_and_keeps_external_cells(self):
        document = snapshot(Document((2, 1, 3), {(0, 0, 0): ('minecraft:stone', 0)}),
                            ('rotate_y90',))
        self.assertEqual((3, 1, 2), document.size)
        external = world_position((3, 0, 0))
        self.blocks[external] = ('minecraft:gold_block', 0)
        self.upload(document, request=19, include_air=True)
        self.finish()
        self.assertEqual(6, len(self.writes))
        self.assertEqual(set(world_position(pos) for pos in document.points()), set(self.writes))
        self.assertEqual(('minecraft:gold_block', 0), self.blocks[external])
        self.assertEqual(('minecraft:stone', 0), self.blocks[world_position((2, 0, 0))])
        self.assertEqual(5, sum(self.blocks[pos] == AIR for pos in self.writes))


if __name__ == '__main__':
    unittest.main()

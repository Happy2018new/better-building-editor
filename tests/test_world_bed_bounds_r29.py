"""Keep native bed pair creation inside the frozen world-write document.

The established fake SDK records explicit setters. These are CPU contract
checks and do not assert native visual acceptance or simulate bed physics.
"""
import unittest

import test_server_stream as fixture
from modern_projection.projection.block_groups import group_partner
from modern_projection.projection.block_registry import from_states
from modern_projection.projection.cell import AIR, make_cell
from modern_projection.projection.model import Document
from modern_projection.projection.nbt_spatial import root_payload, scalar
from modern_projection.projection.projection_transform import snapshot, transform_position
from modern_projection.projection.transfer import packets


ORIGIN = (11, 70, -13)
STONE = ('minecraft:stone', 0)
GOLD = ('minecraft:gold_block', 0)
WATER = ('minecraft:water', 0)
OPERATIONS = ((), ('rotate_y90',), ('rotate_y180',), ('rotate_y270',),
              ('mirror_x',), ('mirror_y',), ('mirror_z',))
NEIGHBORS = ((-1, 0, 0), (1, 0, 0), (0, -1, 0),
             (0, 1, 0), (0, 0, -1), (0, 0, 1))


def world(local):
    return tuple(ORIGIN[axis] + local[axis] for axis in range(3))


def bed_value(head=False, direction=0, occupied=False):
    return from_states('minecraft:bed', {
        'direction': direction, 'head_piece_bit': head, 'occupied_bit': occupied})


def bed_cell(value, mode='front', local=(0, 0, 0)):
    actor = {'id': {'__type__': 8, '__value__': 'Bed'},
             'color': {'__type__': 1, '__value__': 7}}
    actor.update((axis, {'__type__': 3, '__value__': local[index]})
                 for index, axis in enumerate(('x', 'y', 'z')))
    if mode == 'background':
        return make_cell(AIR, value)
    if mode == 'water_front':
        return make_cell(WATER, value, actor)
    return make_cell(value, WATER if mode == 'wet' else AIR, actor)


class WorldBedBoundsTests(unittest.TestCase):
    setUp = fixture.ServerStreamTests.setUp
    read_entity = fixture.ServerStreamTests.read_entity
    read_palette = fixture.ServerStreamTests.read_palette
    write = fixture.ServerStreamTests.write
    write_palette = fixture.ServerStreamTests.write_palette
    set_actor = fixture.ServerStreamTests.set_actor
    set_liquid = fixture.ServerStreamTests.set_liquid
    finish = fixture.ServerStreamTests.finish

    def reset_records(self):
        for record in (self.blocks, self.writes, self.palette_writes, self.actor_writes,
                       self.state_writes, self.liquids, self.replies,
                       self.entity_reads, self.palette_reads):
            record.clear()

    def upload(self, target, include_air=False):
        for packet in packets(target):
            self.host.request({
                '__id__': 'player', 'request': 1,
                'action': 'apply' if packet['seq'] == 0 else 'upload',
                'origin': ORIGIN, 'includeAir': include_air, 'stream': packet})

    def assert_no_setters(self):
        self.assertEqual([], self.writes)
        self.assertEqual([], self.palette_writes)
        self.assertEqual([], self.state_writes)
        self.assertEqual([], self.actor_writes)
        self.assertEqual({}, self.liquids)

    def assert_incomplete_rejected(self, operations, include_air, head=False, mode='front'):
        self.reset_records()
        source = Document((1, 1, 1), {(0, 0, 0): bed_cell(bed_value(head), mode)})
        target = snapshot(source, operations)
        sentinels = dict((world(local), GOLD) for local in NEIGHBORS + ((0, 0, 0),))
        self.blocks.update(sentinels)
        self.upload(target, include_air)
        job = self.host.jobs['player'][2]
        self.finish()
        self.assert_no_setters()
        self.assertEqual(sentinels, self.blocks)
        self.assertEqual({'total': 1, 'processed': 1, 'written': 0, 'failed': 1},
                         self.replies[-1][2]['progress'])
        self.assertTrue(self.replies[-1][2]['error'])
        self.assertIn('首处失败 (11, 70, -13)', self.replies[-1][2]['error'])
        self.assertIn('对应部件', self.replies[-1][2]['error'])
        self.assertEqual(ORIGIN, job.failures[0][0])
        self.assertIn('对应部件', job.failures[0][1])
        self.assertEqual([], self.entity_reads)
        self.assertEqual([], self.palette_reads)

    def test_fourteen_original_incomplete_foot_cases_preserve_outside_sentinels(self):
        for operations in OPERATIONS:
            for include_air in (False, True):
                with self.subTest(operations=operations, include_air=include_air):
                    self.assert_incomplete_rejected(operations, include_air)

    def test_incomplete_heads_and_promoted_background_parts_never_call_native_setters(self):
        for operations in OPERATIONS:
            for include_air in (False, True):
                for head, mode in ((True, 'front'), (False, 'background'),
                                   (True, 'background'), (False, 'water_front'),
                                   (True, 'water_front')):
                    with self.subTest(operations=operations, include_air=include_air,
                                      head=head, mode=mode):
                        self.assert_incomplete_rejected(operations, include_air, head, mode)

    def test_bad_partner_state_fails_only_bed_cells_and_continues_normal_cells(self):
        for operations in OPERATIONS:
            for include_air in (False, True):
                for partner in (AIR, STONE, bed_value(False), bed_value(True, direction=1)):
                    with self.subTest(operations=operations, include_air=include_air, partner=partner):
                        self.reset_records()
                        source = Document((2, 1, 2), {
                            (0, 0, 0): bed_cell(bed_value()),
                            (0, 0, 1): partner, (1, 0, 0): STONE})
                        target = snapshot(source, operations)
                        self.upload(target, include_air)
                        job = self.host.jobs['player'][2]
                        self.finish()
                        normal = world(transform_position((1, 0, 0), source.size, operations))
                        self.assertEqual(STONE, self.blocks[normal])
                        self.assertEqual([], self.state_writes)
                        self.assertEqual([], self.actor_writes)
                        failures = 2 if partner[0] == 'minecraft:bed' else 1
                        self.assertEqual(failures, job.failed)
                        self.assertEqual(job.total - failures, job.written)
                        self.assertTrue(all(target.contains(tuple(pos[axis] - ORIGIN[axis]
                                                                 for axis in range(3)))
                                            for pos in self.writes))
                        self.assertTrue(all('对应部件' in detail for pos, detail in job.failures))

    def test_complete_transformed_beds_keep_wet_layers_occupied_states_and_typed_nbt(self):
        for operations in OPERATIONS:
            for include_air in (False, True):
                for occupied in (False, True):
                    for mode in ('front', 'wet', 'background', 'water_front'):
                        with self.subTest(operations=operations, include_air=include_air,
                                          occupied=occupied, mode=mode):
                            self.reset_records()
                            foot_pos, head_pos = (0, 0, 1), (0, 0, 2)
                            foot = bed_value(occupied=occupied)
                            unused_offset, head = group_partner(foot)
                            source = Document((2, 1, 3), {
                                foot_pos: bed_cell(foot, mode, foot_pos),
                                head_pos: bed_cell(head, mode, head_pos),
                                (1, 0, 0): STONE})
                            target = snapshot(source, operations)
                            self.upload(target, include_air)
                            self.finish()
                            expected_total = target.volume if include_air else 3
                            self.assertEqual({'total': expected_total, 'processed': expected_total,
                                              'written': expected_total, 'failed': 0},
                                             self.replies[-1][2]['progress'])
                            self.assertFalse(self.replies[-1][2].get('error'))
                            transformed_head = world(transform_position(head_pos, source.size, operations))
                            transformed_foot = world(transform_position(foot_pos, source.size, operations))
                            self.assertEqual(2, len(self.state_writes))
                            for pos, properties, dimension in self.state_writes:
                                self.assertEqual(transformed_head, pos)
                                self.assertTrue(properties['head_piece_bit'])
                                self.assertEqual(occupied, properties['occupied_bit'])
                            bed_positions = {transformed_head, transformed_foot}
                            self.assertEqual(set() if mode == 'background' else bed_positions,
                                             {pos for dim, pos, actor in self.actor_writes})
                            for dim, pos, actor in self.actor_writes:
                                root = root_payload(actor)
                                self.assertEqual(pos, tuple(scalar(root, axis) for axis in ('x', 'y', 'z')))
                                self.assertEqual(7, scalar(root, 'color'))
                            if mode in ('wet', 'water_front'):
                                for pos in bed_positions:
                                    self.assertEqual({'name': WATER[0], 'aux': WATER[1]}, self.liquids[pos])
                            self.assertTrue(all(target.contains(tuple(pos[axis] - ORIGIN[axis]
                                                                     for axis in range(3)))
                                                for pos in self.writes))
                            self.assertEqual([], self.entity_reads)
                            self.assertEqual([], self.palette_reads)

    def test_cancel_after_rejected_bed_keeps_failure_reason_and_written_prefix(self):
        target = Document((3, 1, 1), {
            (0, 0, 0): bed_cell(bed_value()), (1, 0, 0): STONE, (2, 0, 0): STONE})
        self.upload(target)
        job = self.host.jobs['player'][2]
        original_step = job.step
        job.step = lambda budget=2048: original_step(2)
        self.host.tick()
        self.assertEqual([world((1, 0, 0))], self.writes)
        self.host.request({'__id__': 'player', 'request': 1, 'action': 'cancel'})
        self.host.tick()
        self.assertEqual([world((1, 0, 0))], self.writes)
        self.assertNotIn('player', self.host.jobs)
        self.assertEqual([], self.state_writes)
        self.assertEqual([], self.actor_writes)
        response = self.replies[-1][2]
        self.assertEqual({'total': 3, 'processed': 2, 'written': 1, 'failed': 1},
                         response['progress'])
        self.assertIn('取消', response['error'])
        self.assertIn('首处失败 (11, 70, -13)', response['error'])
        self.assertIn('对应部件', response['error'])


if __name__ == '__main__':
    unittest.main()

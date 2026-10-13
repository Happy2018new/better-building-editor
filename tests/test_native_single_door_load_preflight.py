"""Offline fault checks for the prospective read-only world/player load gate."""
import copy
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_single_door_load_preflight as gate
import probe_native_single_door as probe


def raw_anchor(**changes):
    return dict({'runtime': gate.RUNTIME, 'level': 'test-level', 'players': ['test-player'],
                 'player': 'test-player', 'dimension': 0, 'foot': [.5, -60., .5],
                 'marker_present': False}, **changes)


def loaded_chunks(anchor, loaded=True):
    positions = {}
    for pos in anchor['reserved']:
        positions.setdefault((pos[0] >> 4, pos[2] >> 4), pos)
    return {'same_anchor': True, 'foot_after_chunks': anchor['foot'],
            'chunks': [{'chunk': chunk, 'pos': pos, 'loaded': loaded}
                       for chunk, pos in sorted(positions.items())]}


class Clock:
    def __init__(self):
        self.now = 0
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.now += seconds


class NativeSingleDoorLoadPreflightTests(unittest.TestCase):
    def wait(self, anchors, chunks=None, limit=1, late=None):
        clock, receipt, calls, snapshots = Clock(), {}, [], []
        index = 0
        current = None
        def read(code, deadline):
            nonlocal index, current
            calls.append((code, deadline))
            if 'expected=' not in code:
                current = copy.deepcopy(anchors[min(index, len(anchors) - 1)])
                index += 1
                if late == 'anchor':
                    clock.now = deadline
                return current
            status, anchor = gate.anchor_status(current, probe.single_pair)
            result = loaded_chunks(anchor) if chunks is None else chunks(index, anchor)
            if late == 'chunks':
                clock.now = deadline
            return result
        with mock.patch.object(gate.time, 'monotonic', clock.monotonic), \
             mock.patch.object(gate.time, 'sleep', clock.sleep):
            try:
                result = gate.wait_for_load(read, probe.single_pair, probe.MARKER, receipt, limit,
                                           lambda: snapshots.append(copy.deepcopy(receipt)))
            except gate.LoadPreflightError:
                result = None
        return result, receipt, calls, snapshots

    def test_v12_raw_y32768_is_retained_and_never_used_for_chunk_or_fixture_calls(self):
        bad = raw_anchor(foot=[.5, 32768., .5])
        result, receipt, calls, snapshots = self.wait([bad])
        self.assertIsNone(result)
        self.assertFalse(receipt['ready'])
        self.assertFalse(receipt['mutation_attempted'])
        self.assertEqual('world_player_not_loaded', receipt['classification'])
        self.assertEqual(4, len(receipt['attempts']))
        self.assertTrue(all(row['raw_anchor']['foot'] == bad['foot'] for row in receipt['attempts']))
        self.assertTrue(all(row['status'] == 'foot_outside_fixed_scope' for row in receipt['attempts']))
        self.assertTrue(all('expected=' not in code for code, deadline in calls))
        self.assertTrue(snapshots)
        self.assertEqual(bad, raw_anchor(foot=[.5, 32768., .5]))

    def test_natural_loading_can_settle_only_after_two_loaded_stable_observations(self):
        result, receipt, calls, snapshots = self.wait([raw_anchor(foot=[.5, 32768., .5]), raw_anchor()])
        self.assertEqual((4, -48, 4), result['origin'])
        self.assertEqual([.5, -60., .5], result['foot'])
        self.assertEqual(17, len(result['reserved']))
        self.assertTrue(receipt['ready'])
        self.assertEqual('loaded_stable_anchor', receipt['classification'])
        self.assertEqual(['foot_outside_fixed_scope', 'chunks_loaded', 'chunks_loaded'],
                         [row['status'] for row in receipt['attempts']])
        self.assertEqual(5, len(calls))
        self.assertTrue(all(deadline == 1 for code, deadline in calls))

    def test_nonfinite_feet_and_out_of_bounds_full_reserve_fail_before_chunk_queries(self):
        for foot in (None, [.5, float('nan'), .5], [.5, float('inf'), .5],
                     [.5, 307., .5], [124., -60., .5], [True, -60., .5]):
            with self.subTest(foot=foot):
                result, receipt, calls, snapshots = self.wait([raw_anchor(foot=foot)])
                self.assertIsNone(result)
                self.assertTrue(all('expected=' not in code for code, deadline in calls))
                self.assertFalse(receipt['mutation_attempted'])

    def test_wrong_dimension_runtime_or_unresolved_fixture_stops_immediately(self):
        for changes, status in (({'dimension': 1}, 'unsupported_dimension'),
                ({'runtime': 'future-runtime'}, 'unsupported_runtime'),
                ({'marker_present': True}, 'prior_fixture_unresolved'),
                ({'players': ['first', 'second']}, 'single_player_binding_invalid')):
            with self.subTest(status=status):
                result, receipt, calls, snapshots = self.wait([raw_anchor(**changes)])
                self.assertIsNone(result)
                self.assertEqual(status, receipt['classification'])
                self.assertEqual(1, len(calls))

    def test_absent_player_waits_and_replaced_player_is_never_rebound(self):
        result, receipt, calls, snapshots = self.wait([
            raw_anchor(players=[], player=None, foot=None), raw_anchor()])
        self.assertTrue(receipt['ready'])
        result, receipt, calls, snapshots = self.wait([
            raw_anchor(), raw_anchor(players=['other'], player='other')])
        self.assertIsNone(result)
        self.assertEqual('player_binding_changed', receipt['classification'])
        self.assertEqual(3, len(calls))
        result, receipt, calls, snapshots = self.wait([raw_anchor(), raw_anchor(level='different-level')])
        self.assertIsNone(result)
        self.assertEqual('world_binding_changed', receipt['classification'])
        self.assertEqual(3, len(calls))

    def test_unloaded_chunk_and_moving_anchor_reset_stable_sample_requirement(self):
        result, receipt, calls, snapshots = self.wait([raw_anchor()],
            chunks=lambda index, anchor: loaded_chunks(anchor, loaded=index != 2), limit=2)
        self.assertTrue(receipt['ready'])
        self.assertEqual(['chunks_loaded', 'chunks_not_loaded', 'chunks_loaded', 'chunks_loaded'],
                         [row['status'] for row in receipt['attempts']])
        result, receipt, calls, snapshots = self.wait([
            raw_anchor(), raw_anchor(foot=[.5, -59.5, .5]), raw_anchor()], limit=2)
        self.assertEqual(4, len(receipt['attempts']))
        self.assertTrue(receipt['ready'])

    def test_incomplete_or_ambiguous_chunks_and_during_read_movement_cannot_pass(self):
        for fault in ('missing', 'duplicate', 'nonboolean', 'moving', 'missing_return'):
            def chunks(index, anchor):
                result = loaded_chunks(anchor)
                if fault == 'missing':
                    result['chunks'] = []
                elif fault == 'duplicate':
                    result['chunks'] *= 2
                elif fault == 'nonboolean':
                    result['chunks'][0]['loaded'] = 1
                elif fault == 'moving':
                    result['foot_after_chunks'] = [.5, -59., .5]
                else:
                    del result['chunks'][0]['loaded']
                return result
            with self.subTest(fault=fault):
                result, receipt, calls, snapshots = self.wait([raw_anchor()], chunks=chunks)
                self.assertIsNone(result)
                self.assertFalse(receipt['ready'])

    def test_reserve_crossing_negative_chunk_boundaries_checks_every_chunk(self):
        raw = raw_anchor(foot=[-4., -60., -4.])
        status, anchor = gate.anchor_status(raw, probe.single_pair)
        observation = loaded_chunks(anchor)
        self.assertEqual({(-1, 0), (0, -1), (0, 0)}, {row['chunk'] for row in observation['chunks']})
        self.assertEqual('chunks_loaded', gate.chunks_status(observation, anchor))
        observation['chunks'].pop()
        self.assertEqual('chunk_read_incomplete', gate.chunks_status(observation, anchor))
        result, receipt, calls, snapshots = self.wait([raw])
        self.assertTrue(receipt['ready'])
        self.assertTrue(all(len(row['raw_chunks']['chunks']) == 3 for row in receipt['attempts']))

    def test_response_at_or_after_deadline_cannot_establish_readiness(self):
        for late in ('anchor', 'chunks'):
            result, receipt, calls, snapshots = self.wait([raw_anchor()], late=late)
            self.assertIsNone(result)
            self.assertFalse(receipt['ready'])
            self.assertEqual(1 if late == 'anchor' else 2, len(calls))

    def test_read_error_retains_native_error_and_does_not_retry_or_mutate(self):
        receipt = {}
        error = RuntimeError('read transport failed')
        error.error = {'code': -32603, 'message': 'original native failure'}
        read = mock.Mock(side_effect=error)
        with self.assertRaisesRegex(RuntimeError, 'read transport failed'):
            gate.wait_for_load(read, probe.single_pair, probe.MARKER, receipt, gate.time.monotonic()+1)
        self.assertEqual(1, read.call_count)
        self.assertEqual(error.error, receipt['native_error'])
        self.assertFalse(receipt['mutation_attempted'])

    def test_native_read_code_checks_loaded_chunks_without_any_setter(self):
        calls, foot = [], [.5, -60., .5]
        factory = SimpleNamespace(
            CreateDimension=lambda player: SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda player: SimpleNamespace(GetFootPos=lambda: foot),
            CreateChunkSource=lambda level: SimpleNamespace(
                CheckChunkState=lambda dimension, pos: calls.append((dimension, pos)) or True))
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId = lambda: 'test-level'
        api.GetPlayerList = lambda: ['test-player']
        api.GetMinecraftVersion = lambda: gate.RUNTIME
        modules = {'mod': ModuleType('mod'), 'mod.server': ModuleType('mod.server'),
                   'mod.server.extraServerApi': api}
        status, anchor = gate.anchor_status(raw_anchor(), probe.single_pair)
        with mock.patch.dict(sys.modules, modules):
            namespace = {}
            exec(gate.READ_CHUNKS % (probe.MARKER, anchor, anchor['reserved']), namespace)
            self.assertEqual('chunks_loaded', gate.chunks_status(json.loads(namespace['_result']), anchor))
            self.assertEqual([(0, anchor['reserved'][0])], calls)
            calls.clear()
            foot = [.5, 32768., .5]
            exec(gate.READ_CHUNKS % (probe.MARKER, anchor, anchor['reserved']), namespace)
            self.assertFalse(json.loads(namespace['_result'])['same_anchor'])
            self.assertEqual([], calls)
        self.assertNotIn('SetBlock', gate.READ_ANCHOR + gate.READ_CHUNKS)
        self.assertNotIn('SetFootPos', gate.READ_ANCHOR + gate.READ_CHUNKS)


if __name__ == '__main__':
    unittest.main()

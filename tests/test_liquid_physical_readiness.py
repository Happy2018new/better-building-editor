"""World fixture readiness rejects sentinel, nonfinite, divergent and unreadable state."""
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import check_liquid_physical_readiness as physical
from check_liquid_physical_readiness import valid_snapshot
from mcdk import Client, MCDKError
from probe_liquid_workspace import QUALIFICATION_PREPARE, QUALIFICATION_CLEAN_WORLD, guarded_cleanup
from context_test_environment import SETUP, RESTORE


class FakeResponse:
    headers = {'Mcp-Session-Id': 'test-session'}

    def __init__(self, value, on_read=lambda: None):
        self.raw, self.on_read = json.dumps(value).encode('utf-8'), on_read

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        pass

    def read(self):
        self.on_read()
        return self.raw


class FakeRPC:
    def __init__(self, states, fail=None, on_read=lambda request: None):
        self.states, self.fail, self.on_read, self.requests, self.timeouts = states, fail, on_read, [], []

    def open(self, request, timeout):
        self.timeouts.append(timeout)
        value = json.loads(request.data) if request.data else {'method': request.get_method()}
        self.requests.append(value)
        result = {}
        if value['method'] == 'tools/call':
            arguments = value['params']['arguments']
            if '_pyreact_mcdk_session' in arguments['code']:
                result = {'structuredContent': {'return_value': 'bound-token'}}
            elif self.fail:
                if isinstance(self.fail, Exception):
                    raise self.fail
                result = self.fail
            else:
                state = self.states[0 if arguments['is_client'] else 1]
                result = {'structuredContent': {'return_value': json.dumps(state)}}
        return FakeResponse({'jsonrpc': '2.0', 'id': value.get('id'), 'result': result},
                            lambda: self.on_read(value))


class LiquidPhysicalReadinessTests(unittest.TestCase):
    def snapshots(self, y=64.):
        reserve = [11, int(y) + 24, 11]
        cells = [{'pos': [reserve[0] + x, reserve[1] + dy, reserve[2] + z],
                  'front': {'name': 'minecraft:air'}, 'back': None}
                 for x in range(-2, 4) for dy in range(-2, 4) for z in range(-2, 4)]
        return {'foot': [5.5, y, 5.5]}, {'foot': [5.5, y, 5.5], 'dimension': 0,
            'reserve': reserve, 'front': {'name': 'minecraft:air'}, 'back': None, 'reserve_cells': cells}

    def collect(self, rpc, clock=None, single=False, actual=False, budget=1.):
        client = Client(bind_session=False)
        client.binding = {'token': 'bound-token'}
        client.opener = rpc
        report = {'passed': False, 'budget_seconds': budget, 'rpc_journal': [], 'snapshots': [],
                  'single_snapshot': single, 'actual_world_ready': actual}
        self.report = report
        now = [100.] if clock is None else clock
        with patch.object(physical, 'Client', return_value=client), patch('mcdk.load_session'), \
                patch.object(physical.time, 'monotonic', side_effect=lambda: now[0]), \
                patch.object(physical.time, 'time', side_effect=lambda: now[0]), \
                patch.object(physical.time, 'sleep', side_effect=lambda seconds: now.__setitem__(0, now[0] + seconds)):
            physical.collect(report, 100. + budget, lambda: None)
        return report

    def actual_snapshots(self, y=64., ready=True):
        client, server = self.snapshots(y)
        client.update(player='player', business={key: ready for key in ('owner_present', 'session_present',
            'bridge_present', 'session_ready', 'bridge_session_matches', 'hud_present')})
        server['players'] = ['player']
        return client, server

    def test_actual_world_gate_waits_for_real_uiinit_and_stable_feet_before_full_reserve(self):
        states = [self.actual_snapshots(32768.), self.actual_snapshots(ready=False),
                  self.actual_snapshots(64.3), self.actual_snapshots(), self.actual_snapshots(), self.actual_snapshots()]
        rpc = FakeRPC(states[0])
        original = rpc.open
        seen = []
        def open_scripted(request, timeout):
            value = json.loads(request.data) if request.data else {}
            arguments = value.get('params', {}).get('arguments', {})
            code = arguments.get('code', '')
            if "owner=api.GetSystem('ModernProjection'" in code:
                seen.append(code)
                rpc.states = states[min(len(seen) - 1, len(states) - 1)]
            return original(request, timeout)
        rpc.open = open_scripted
        report = self.collect(rpc, actual=True, budget=10.)
        self.assertTrue(report['passed'])
        self.assertEqual(6, len(report['snapshots']))
        self.assertEqual([0, 0, 1, 1, 2, 3], [row['stable_samples'] for row in report['snapshots']])
        server_calls = [row['params']['arguments']['code'] for row in rpc.requests if row['method'] == 'tools/call'
                        and not row['params']['arguments']['is_client']]
        self.assertEqual(1, sum('GetBlockNew' in code for code in server_calls))
        self.assertEqual(7, len(server_calls))
        self.assertTrue(report['snapshots'][-1]['reservation_check_passed'])
        self.assertTrue(all(0 < timeout <= 3. for timeout in rpc.timeouts))

    def test_actual_world_gate_missing_business_or_occupied_reserve_never_passes(self):
        for states in (self.actual_snapshots(ready=False), self.actual_snapshots()):
            if states[0]['business']['session_ready']:
                states[1]['reserve_cells'][0]['front'] = {'name': 'minecraft:stone'}
            report = self.collect(FakeRPC(states), actual=True, budget=3.)
            self.assertFalse(report['passed'])
            self.assertTrue('fixed startup deadline' in report['error'] or 'one full reserved-area snapshot' in report['error'])

    def test_actual_world_cheap_server_reads_no_blocks_and_never_writes(self):
        api, writes = self.world((5.5, -60., 5.5))
        server = json.loads(self.execute_world(physical.FEET_SERVER, api))
        self.assertTrue(physical.valid_feet({'foot': [5.5, -60., 5.5]}, server))
        self.assertEqual([], api.read_positions)
        self.assertEqual([], writes)

    def test_actual_rpc_layer_routes_client_and_server_with_direct_return_and_raw_journal(self):
        rpc = FakeRPC(self.snapshots())
        report = self.collect(rpc)
        self.assertTrue(report['passed'])
        calls = [row['params']['arguments'] for row in rpc.requests
                 if row['method'] == 'tools/call' and '_pyreact_mcdk_session' not in row['params']['arguments']['code']]
        self.assertEqual([True, False], [row['is_client'] for row in calls])
        self.assertTrue(all(row['direct_return'] and 'is_server' not in row for row in calls))
        self.assertEqual(3, sum('_pyreact_mcdk_session' in row['params']['arguments']['code']
            for row in rpc.requests if row['method'] == 'tools/call'))
        journal = report['rpc_journal']
        self.assertEqual('initialize', json.loads(journal[0]['request_utf8'])['method'])
        self.assertEqual('DELETE', journal[-1]['http_method'])
        self.assertTrue(all('response_utf8' in row and 'response_sha256' in row for row in journal
                            if row['http_method'] == 'POST' and
                            json.loads(row['request_utf8'])['method'] != 'notifications/initialized'))
        self.assertTrue(all(0 < timeout <= 1. for timeout in rpc.timeouts))

    def test_sdk_error_and_missing_direct_return_never_pass(self):
        for result in ({'isError': True, 'content': [{'type': 'text', 'text': 'SDK refused'}]},
                       {'structuredContent': {'ok': False, 'error': 'SDK refused'}}, {'content': []}):
            with self.assertRaises(MCDKError):
                self.collect(FakeRPC(self.snapshots(), fail=result))
            self.assertFalse(self.report['passed'])
            self.assertEqual([], self.report['snapshots'])
            self.assertTrue(any('response_utf8' in row and 'SDK refused' in row['response_utf8']
                for row in self.report['rpc_journal']) or result == {'content': []})

    def test_rpc_timeout_and_late_handshake_or_state_response_cannot_pass(self):
        with self.assertRaises(TimeoutError):
            self.collect(FakeRPC(self.snapshots(), fail=TimeoutError('read timed out')))
        self.assertFalse(self.report['passed'])
        self.assertTrue(any('read timed out' in row.get('error', '') for row in self.report['rpc_journal']))
        for late_method in ('initialize', 'tools/call'):
            clock = [100.]
            def late(request):
                if request['method'] == late_method:
                    clock[0] = 102.
            with self.assertRaises(TimeoutError):
                self.collect(FakeRPC(self.snapshots(), on_read=late), clock)
            self.assertFalse(self.report['passed'])
            self.assertTrue(any('response arrived after' in row.get('error', '')
                                for row in self.report['rpc_journal']))

    def test_single_terminal_snapshot_rejects_without_another_poll(self):
        client, server = self.snapshots()
        client['foot'][1] = server['foot'][1] = 32768.
        report = self.collect(FakeRPC((client, server)), single=True)
        self.assertFalse(report['passed'])
        self.assertEqual(1, len(report['snapshots']))
        self.assertIn('one physical readiness snapshot', report['error'])

    def test_loaded_matching_feet_and_exact_readable_empty_reserve_are_required(self):
        self.assertTrue(valid_snapshot(*self.snapshots()))
        for change in ({'reserve': [11, 89, 11]}, {'front': None}, {'dimension': 1},
                       {'front': {'name': 'minecraft:stone'}}, {'back': {'name': 'minecraft:water'}}):
            client, server = self.snapshots()
            server.update(change)
            self.assertFalse(valid_snapshot(client, server))

    def test_sentinel_nonfinite_or_out_of_range_feet_fail_before_coordinate_normalization(self):
        for value in (32768., float('nan'), float('inf'), -65., 320., True):
            client, server = self.snapshots()
            for state in (client, server):
                state['foot'][1] = value
            self.assertFalse(valid_snapshot(client, server))

    def test_client_server_position_disagreement_cannot_qualify_a_loaded_session(self):
        client, server = self.snapshots()
        client['foot'][0] += 3.
        self.assertFalse(valid_snapshot(client, server))

    def test_legitimate_low_superflat_requires_all_216_readable_air_cells_without_clamping(self):
        self.assertTrue(valid_snapshot(*self.snapshots(-60.)))
        for index in (0, 86, 215):
            for change in ({'front': None}, {'front': {'name': 'minecraft:stone'}},
                           {'back': {'name': 'minecraft:water'}}, {'pos': [0, 0, 0]}):
                client, server = self.snapshots(-60.)
                server['reserve_cells'][index].update(change)
                self.assertFalse(valid_snapshot(client, server))
        client, server = self.snapshots(-60.)
        server['reserve_cells'].pop()
        self.assertFalse(valid_snapshot(client, server))
        self.assertFalse(valid_snapshot(*self.snapshots(300.)))
        api, writes = self.world((5.5, -60., 5.5))
        try:
            self.execute_world(QUALIFICATION_PREPARE, api)
            self.assertEqual((11, -36, 11), writes[0][0])
            self.execute_world(QUALIFICATION_CLEAN_WORLD, api)
        finally:
            if hasattr(sys, '_liquid_pose_world'):
                del sys._liquid_pose_world

    def world(self, foot, native_write=True, mutate_failure=None):
        blocks, writes, reads = {}, [], []
        def get_block(position, dimension):
            reads.append(tuple(position))
            return blocks.get(tuple(position), {'name': 'minecraft:air'})
        def set_block(position, value, *unused):
            writes.append((position, value['name']))
            if native_write or mutate_failure:
                blocks[position] = value
            if value['name'] == 'minecraft:stone' and mutate_failure:
                if isinstance(mutate_failure, Exception):
                    raise mutate_failure
                return False
            return native_write
        factory = SimpleNamespace(
            CreateDimension=lambda player: SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda player: SimpleNamespace(GetFootPos=lambda: foot),
            CreateBlockInfo=lambda player: SimpleNamespace(GetBlockNew=get_block,
                GetLiquidBlock=lambda position, dimension: None, SetBlockNew=set_block))
        api = ModuleType('mod.server.extraServerApi')
        api.GetPlayerList = lambda: ['player']
        api.GetEngineCompFactory = lambda: factory
        api.read_positions, api.blocks = reads, blocks
        return api, writes

    def execute_world(self, code, api):
        modules = {'mod': ModuleType('mod'), 'mod.server': ModuleType('mod.server'),
                   'mod.server.extraServerApi': api}
        modules['mod'].server = modules['mod.server']
        modules['mod.server'].extraServerApi = api
        with patch.dict(sys.modules, modules):
            namespace = {'long': int}
            exec(code, namespace)
            return namespace['_result']

    def test_reserved_native_write_readback_and_cleanup_never_set_player_position(self):
        api, writes = self.world((5.5, 64., 5.5))
        self.assertFalse(hasattr(sys, '_liquid_pose_world'))
        try:
            self.execute_world(QUALIFICATION_PREPARE, api)
            self.assertEqual([((11, 88, 11), 'minecraft:stone')], writes)
            self.execute_world(QUALIFICATION_CLEAN_WORLD, api)
            self.assertFalse(hasattr(sys, '_liquid_pose_world'))
            self.assertEqual('minecraft:air', writes[-1][1])
        finally:
            if hasattr(sys, '_liquid_pose_world'):
                del sys._liquid_pose_world

    def test_actual_server_snapshot_reads_whole_bounded_reserve_before_any_write(self):
        api, writes = self.world((5.5, -60., 5.5))
        server = json.loads(self.execute_world(physical.SERVER, api))
        self.assertTrue(valid_snapshot({'foot': [5.5, -60., 5.5]}, server))
        self.assertEqual(216, len(api.read_positions))
        self.assertEqual(216, len(set(api.read_positions)))
        self.assertEqual([], writes)
        api.blocks[(9, -38, 9)] = None
        server = json.loads(self.execute_world(physical.SERVER, api))
        self.assertFalse(valid_snapshot({'foot': [5.5, -60., 5.5]}, server))
        api, writes = self.world((5.5, 300., 5.5))
        self.execute_world(physical.SERVER, api)
        self.assertEqual([], api.read_positions)
        with self.assertRaises(AssertionError):
            self.execute_world(QUALIFICATION_PREPARE, api)
        self.assertEqual([], writes)

    def test_invalid_feet_or_refused_native_write_abort_before_any_capture(self):
        for foot, writable in (((5.5, 32768., 5.5), True), ((5.5, 64., 5.5), False)):
            api, writes = self.world(foot, writable)
            try:
                with self.assertRaises(AssertionError):
                    self.execute_world(QUALIFICATION_PREPARE, api)
                if foot[1] == 32768.:
                    self.assertEqual([], writes)
            finally:
                if hasattr(sys, '_liquid_pose_world'):
                    del sys._liquid_pose_world

    def test_failed_mutating_stone_setter_retains_cleanup_journal_and_restores(self):
        for failure in (True, RuntimeError('SDK write failed after mutation')):
            api, writes = self.world((5.5, 64., 5.5), mutate_failure=failure)
            try:
                with self.assertRaises((AssertionError, RuntimeError)):
                    self.execute_world(QUALIFICATION_PREPARE, api)
                self.assertEqual([], sys._liquid_pose_world['workspace_cells'])
                self.execute_world(QUALIFICATION_CLEAN_WORLD, api)
                self.assertEqual('minecraft:air', writes[-1][1])
                self.assertFalse(hasattr(sys, '_liquid_pose_world'))
            finally:
                if hasattr(sys, '_liquid_pose_world'):
                    del sys._liquid_pose_world

    def test_cleanup_before_journal_is_a_noop(self):
        self.assertFalse(hasattr(sys, '_liquid_pose_world'))
        namespace = {}
        exec(guarded_cleanup("raise RuntimeError('must not run')", '_liquid_pose_world'), namespace)
        self.assertTrue(namespace['_result'])

    def test_mutating_environment_setup_failure_restores_from_server_journal(self):
        state = {'time': 1000, 'rules': {'daylight_cycle': True, 'weather_cycle': True},
                 'raining': True, 'thunder': True}
        before = dict(state, rules=dict(state['rules']))
        def rules(value):
            state['rules'] = value['cheat_info']
            return True
        def set_time(value):
            state['time'] = value
            return value == before['time']
        def weather(key, value):
            state[key] = bool(value)
            return True
        factory = SimpleNamespace(CreateTime=lambda level: SimpleNamespace(GetTime=lambda: state['time'], SetTime=set_time),
            CreateGame=lambda level: SimpleNamespace(GetGameRulesInfoServer=lambda: {'cheat_info': dict(state['rules'])},
                                                      SetGameRulesInfoServer=rules),
            CreateWeather=lambda level: SimpleNamespace(IsRaining=lambda: state['raining'], IsThunder=lambda: state['thunder'],
                SetRaining=lambda value, duration: weather('raining', value),
                SetThunder=lambda value, duration: weather('thunder', value)))
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory, api.GetLevelId = lambda: factory, lambda: 'level'
        try:
            with self.assertRaises(AssertionError):
                self.execute_world(SETUP, api)
            self.assertTrue(hasattr(sys, '_context_environment_saved'))
            self.assertNotEqual(before, state)
            self.execute_world(guarded_cleanup(RESTORE, '_context_environment_saved'), api)
            self.assertEqual(before, state)
            self.assertFalse(hasattr(sys, '_context_environment_saved'))
        finally:
            if hasattr(sys, '_context_environment_saved'):
                del sys._context_environment_saved


if __name__ == '__main__':
    unittest.main()

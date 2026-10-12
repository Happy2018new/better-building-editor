"""Short lifecycle diagnostics stay separate and recover owned native state."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_scaffold_state_lifecycle as probe


class NativeStub:
    def __init__(self):
        self.front, self.liquid, self.states = {}, {}, {}
        self.writes, self.semantic, self.conversions = [], [], []
        self.fail_clear, self.fail_states, self.reject_flow_restore = False, False, False
        self.tile_drops, self.flow_forbidden = False, False
        self.timers = []
        self.max_pending_timers = 0
        self.clears = []

    def GetBlockNew(self, pos, dimension):
        return dict(self.front.get(pos, {'name': 'minecraft:air', 'aux': 0}))

    def GetLiquidBlock(self, pos, dimension):
        return copy.deepcopy(self.liquid.get(pos))

    def GetBlockStates(self, pos, dimension):
        if self.fail_states:
            raise RuntimeError('Injected state readback failure')
        return copy.deepcopy(self.states.get(pos, {}))

    def GetBlockAuxValueFromStates(self, name, states):
        name = name.decode('utf8') if isinstance(name, bytes) else name
        value = probe.registry.from_states(name, states)
        self.conversions.append((name, copy.deepcopy(states)))
        return value[1] if value else -1

    def SetBlockStates(self, pos, states, dimension):
        self.semantic.append((pos, copy.deepcopy(states)))
        self.states[pos] = copy.deepcopy(states)
        pair = probe.registry.from_states(self.front[pos]['name'], states)
        self.front[pos]['aux'] = pair[1]
        return True

    def SetBlockNew(self, pos, value, handling, dimension, legacy, neighbors):
        value = dict(value)
        value['name'] = value['name'].decode('utf8') if isinstance(value['name'], bytes) else value['name']
        self.writes.append((pos, value, legacy, neighbors))
        self.front[pos] = value
        self.states[pos] = probe.registry.states((value['name'], value['aux']))
        if value['name'] == 'minecraft:acacia_shelf':
            self.front[pos]['aux'] = 0
            self.states[pos] = probe.registry.states(('minecraft:acacia_shelf', 0))
        if value['name'] == 'minecraft:acacia_door':
            upper = (pos[0], pos[1] + 1, pos[2])
            self.front[upper] = {'name': value['name'], 'aux': 8}
            self.states[upper] = probe.registry.states((value['name'], 8))
        if value['name'] == 'minecraft:scaffolding':
            self.front[pos]['aux'] = 8
            self.states[pos] = probe.registry.states(('minecraft:scaffolding', 8))
        return True

    def GetBlankBlockPalette(self):
        return types.SimpleNamespace(DeserializeBlockPalette=self.deserialize)

    def deserialize(self, data):
        if data['common'] != {('minecraft:air', 0): [0]} or data['extra'] != {('minecraft:air', 0): [0]}:
            raise AssertionError('Both layers must be explicitly cleared')
        return True

    def SetBlockByBlockPalette(self, palette, dimension, pos, rotation, conflict):
        self.clears.append(pos)
        if self.fail_clear:
            raise RuntimeError('Injected dual-layer clear failure')
        self.front[pos] = {'name': 'minecraft:air', 'aux': 0}
        self.states[pos] = {}
        self.liquid.pop(pos, None)
        return True

    def GetGameRulesInfoServer(self):
        return {'option_info': {'tile_drops': self.tile_drops}}

    def SetGameRulesInfoServer(self, value):
        self.tile_drops = value['option_info']['tile_drops']
        return True

    def ForbidLiquidFlow(self, forbidden):
        if not forbidden and self.reject_flow_restore:
            return False
        self.flow_forbidden = forbidden
        return True

    def AddTimer(self, delay, callback):
        if delay != .35:
            raise AssertionError('Unexpected observation delay')
        self.timers.append(callback)
        self.max_pending_timers = max(self.max_pending_timers, len(self.timers))


class ScaffoldStateLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.native, self.scope = NativeStub(), {}
        self.identity = {'session_id': 'owned-session', 'owner': 'test-owner', 'game_pid': 100,
                         'game_identity': '12345', 'run_id': 'run-one'}
        factory = types.SimpleNamespace(
            CreateBlockInfo=lambda level: self.native, CreateBlock=lambda level: self.native,
            CreateBlockState=lambda level: self.native, CreateGame=lambda level: self.native,
            CreateDimension=lambda player: types.SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0, 64, 0)))
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId, api.GetPlayerList = lambda: 'level', lambda: ['player']
        api.GetMinecraftVersion = lambda: probe.RUNTIME
        mod, server = types.ModuleType('mod'), types.ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        package = types.ModuleType('modern_projection')
        projection = types.ModuleType('modern_projection.projection')
        package.projection, projection.block_registry = projection, probe.registry
        modules = {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api,
                   'modern_projection': package, 'modern_projection.projection': projection}
        self.patched = patch.dict(sys.modules, modules)
        self.patched.start()
        self.addCleanup(self.patched.stop)
        self.addCleanup(lambda: vars(sys).pop(probe.MARKER, None))

    def execute(self, code):
        exec(compile(code, '<scaffold-lifecycle>', 'exec'), self.scope)
        return json.loads(self.scope['_result'])

    def start(self, allowed=True):
        return self.execute(probe.start_payload(self.identity, 'a' * 64, allowed))

    def restore(self, identity=None):
        return self.execute(probe.RESTORE % (probe.MARKER, identity or self.identity))

    def complete(self):
        start = self.start()
        while self.native.timers:
            self.native.timers.pop(0)()
        native = self.execute(probe.STATUS % (probe.MARKER, self.identity))
        cleanup = self.restore()
        payload = probe.start_payload(self.identity, 'a' * 64, True)
        report = {'schema': 1, 'kind': probe.KIND, 'method': probe.METHOD, 'source_sha256': 'a' * 64,
                  'completed': True, 'restored': cleanup['restored'], 'start': start, 'native': native,
                  'cleanup': cleanup, 'plans': probe.plans(), 'actor_data': probe.ACTOR_SCOPE,
                  'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
                  'provenance': dict(self.identity, game_executable_sha256='c' * 64,
                                     native_payload_sha256=probe.digest(payload.encode('utf8')),
                                     native_status_payload_sha256=probe.digest((probe.STATUS % (probe.MARKER, self.identity)).encode('utf8')),
                                     native_restore_payload_sha256=probe.digest((probe.RESTORE % (probe.MARKER, self.identity)).encode('utf8')))}
        return report

    def test_exact_controls_reserve_phases_and_typed_semantic_difference(self):
        selected = probe.plans()
        self.assertEqual(17, len(selected))
        self.assertEqual(8, sum(row['method'] == probe.DIRECT for row in selected))
        self.assertEqual(8, sum(row['method'] == probe.SEMANTIC for row in selected))
        self.assertEqual(17, len(probe.reserved_positions(selected)))
        self.assertEqual({(0, 0, 0)}, {tuple(row['slot']) for row in selected})
        report = self.complete()
        result = probe.validate_report(report, 'a' * 64)
        self.assertTrue(result['positive_control_matched'])
        self.assertEqual(51, len(self.native.writes))
        self.assertEqual(8, len(self.native.semantic))
        self.assertEqual(1, self.native.max_pending_timers)
        self.assertEqual(18 * 17, len(self.native.clears))
        self.assertEqual(153, report['native']['sequence'])
        rows = {row['id']: row for row in report['native']['rows']}
        self.assertFalse(result['rows'][14]['support_state_matches']['support_written'])
        self.assertTrue(result['rows'][15]['support_state_matches']['support_written'])
        upper = probe.cell_at(rows['door_direct_legacy']['samples'][0], (0, 1, 0))
        self.assertEqual({'name': 'minecraft:acacia_door', 'aux': 8}, upper['front'])
        self.assertEqual(upper, dict(rows['door_direct_legacy']['writes'][2]['before'], offset=[0, 1, 0]))
        self.assertFalse(self.native.tile_drops)
        self.assertFalse(self.native.flow_forbidden)
        self.assertFalse(hasattr(sys, probe.MARKER))

    def test_positive_control_requires_consistent_native_pair_and_typed_stability(self):
        report = self.complete()
        scaffold = probe.cell_at(report['native']['rows'][-1]['samples'][-1], (0, 1, 0))
        scaffold['states']['stability'] = False
        self.assertFalse(probe.validate_report(report, 'a' * 64)['positive_control_matched'])
        scaffold['states']['stability'] = 0
        scaffold['front']['aux'] = 0
        self.assertFalse(probe.validate_report(report, 'a' * 64)['positive_control_matched'])

    def test_true_native_states_are_not_replaced_with_registry_inference(self):
        self.start()
        state = getattr(sys, probe.MARKER)
        slot = tuple(state['config']['plans'][0]['slot'][i] + (4, 82, 4)[i] for i in range(3))
        self.native.states[slot] = {'unexpected_native_state': 1}
        while self.native.timers:
            self.native.timers.pop(0)()
        row = self.execute(probe.STATUS % (probe.MARKER, self.identity))['rows'][0]
        self.assertEqual({'unexpected_native_state': 1}, probe.cell_at(row['samples'][-1], (0, 0, 0))['states'])
        self.restore()

    def test_rejects_unowned_missing_or_wet_baseline_without_mutation(self):
        with self.assertRaises(ValueError):
            probe.owned_session({})
        with self.assertRaisesRegex(AssertionError, 'allowed-flow'):
            self.start(False)
        self.assertEqual([], self.native.writes)
        self.native.liquid[(4, 82, 4)] = {'name': 'minecraft:water', 'aux': 0}
        with self.assertRaisesRegex(AssertionError, 'Non-dry reserve'):
            self.start()
        self.assertEqual([], self.native.writes)
        self.assertFalse(hasattr(sys, probe.MARKER))

    def test_failed_cleanup_restores_policies_and_retains_retry_state(self):
        self.start()
        self.native.fail_clear = True
        cleanup = self.restore()
        self.assertFalse(cleanup['restored'])
        self.assertTrue(cleanup['rules_restored'])
        self.assertTrue(cleanup['flow_restored'])
        self.assertTrue(hasattr(sys, probe.MARKER))
        self.native.fail_clear = False
        self.assertTrue(self.restore()['restored'])

    def test_each_case_must_clear_both_layers_before_next_case_and_stale_timer_is_inert(self):
        self.start()
        self.assertEqual(3, len(self.native.writes))
        callback = self.native.timers.pop(0)
        callback()
        self.assertEqual(6, len(self.native.writes))
        self.assertEqual(17, len(self.native.clears))
        self.assertEqual(1, len(self.native.timers))
        callback()
        self.assertEqual(6, len(self.native.writes))
        self.assertEqual(17, len(self.native.clears))
        self.native.fail_clear = True
        self.native.timers.pop(0)()
        value = self.execute(probe.STATUS % (probe.MARKER, self.identity))
        self.assertEqual(1, value['observed'])
        self.assertEqual(6, len(self.native.writes))
        self.assertEqual([], self.native.timers)
        self.assertIsNone(value['rows'][2])
        self.assertEqual('case_clear', value['error']['stage'])
        self.assertEqual(3, len(value['rows'][1]['samples']))
        self.native.fail_clear = False
        self.assertTrue(self.restore()['restored'])

    def test_callback_failure_and_late_callback_do_not_write_after_cleanup(self):
        self.start()
        callback = self.native.timers.pop(0)
        self.native.fail_states = True
        callback()
        value = self.execute(probe.STATUS % (probe.MARKER, self.identity))
        self.assertFalse(value['done'])
        self.assertIn('readback failure', value['error']['message'])
        self.assertEqual(3, len(value['rows'][0]['samples']))
        self.assertEqual(17, len(value['rows'][0]['samples'][-1]['read_errors']))
        self.assertIsNone(value['rows'][1])
        self.native.fail_states = False
        self.assertTrue(self.restore()['restored'])
        count = len(self.native.writes)
        for late in self.native.timers:
            late()
        self.assertEqual(count, len(self.native.writes))
        self.assertFalse(hasattr(sys, probe.MARKER))

    def test_cleanup_cannot_touch_another_run_and_callbacks_keep_local_components(self):
        self.start()
        other = dict(self.identity, run_id='another-run')
        with self.assertRaisesRegex(AssertionError, 'identity differs'):
            self.restore(other)
        self.scope.update(info=None, state=None, game=None, probe={}, json=None, sys=None, snapshot=None)
        while self.native.timers:
            self.native.timers.pop(0)()
        value = self.execute(probe.STATUS % (probe.MARKER, self.identity))
        self.assertTrue(value['done'])
        self.assertTrue(self.restore()['restored'])

    def test_partial_reordered_tampered_or_unrestored_evidence_is_rejected(self):
        valid = self.complete()
        for mutation in ('order', 'phase', 'source', 'payload', 'runtime', 'flags', 'reset', 'flow',
                         'typed_expected', 'plans', 'case_reset', 'sequence', 'states_missing', 'baseline',
                         'setup', 'executable', 'image_acceptance', 'actor', 'timer'):
            report = copy.deepcopy(valid)
            if mutation == 'order':
                report['native']['rows'].reverse()
            elif mutation == 'phase':
                report['native']['rows'][0]['samples'].pop()
            elif mutation == 'source':
                report['source_sha256'] = 'b' * 64
            elif mutation == 'payload':
                report['provenance']['native_payload_sha256'] = 'b' * 64
            elif mutation == 'runtime':
                report['start']['runtime'] = 'next'
            elif mutation == 'flags':
                report['native']['rows'][0]['writes'][1]['update_neighbors'] = True
            elif mutation == 'reset':
                report['cleanup']['air_reset_returns'].pop()
            elif mutation == 'flow':
                report['cleanup']['flow_restored'] = False
            elif mutation == 'typed_expected':
                report['native']['rows'][4]['expected_states']['button_pressed_bit'] = 0
            elif mutation == 'plans':
                report['plans'][0]['slot'] = [3, 0, 0]
            elif mutation == 'case_reset':
                report['native']['rows'][0]['air_reset_returns'].pop()
            elif mutation == 'sequence':
                report['native']['rows'][1]['baseline']['sequence'] = 1
            elif mutation == 'states_missing':
                report['native']['rows'][0]['samples'][0]['cells'][0]['states'] = None
            elif mutation == 'baseline':
                report['native']['rows'][1]['baseline']['cells'][0]['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            elif mutation == 'setup':
                report['start']['setup']['rules_returned'] = False
            elif mutation == 'executable':
                report['provenance']['game_executable_sha256'] = None
            elif mutation == 'image_acceptance':
                report['acceptance']['editor'] = True
            elif mutation == 'actor':
                report['native']['rows'][0]['actor_data'] = 'accepted'
            else:
                report['native']['rows'][0].pop('timer')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                probe.validate_report(report, 'a' * 64)

    def test_host_checkpoints_partial_progress_and_cleanup_before_marking_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'diagnostic.json'
            executable = Path(directory) / 'game.exe'
            executable.write_bytes(b'owned-test-game')
            session = dict(self.identity, id=self.identity['session_id'], game_executable=str(executable))
            native = self.native
            observations = []
            class HostClient:
                binding = session
                def __init__(self, timeout):
                    pass
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
            class HostCheck:
                def __init__(self, *args):
                    pass
                def wait(self, label, ready, read):
                    while True:
                        value = read()
                        persisted = json.loads(output.read_bytes())
                        observations.append(persisted)
                        if ready(value):
                            return value
                        native.timers.pop(0)()
            with patch.object(probe, 'owned_session', return_value=('owned.json', self.identity['owner'], session)), \
                    patch.object(probe, 'Client', HostClient), patch.object(probe, 'BlueprintCheck', HostCheck), \
                    patch.object(probe, 'run', side_effect=lambda client, code: self.execute(code)), \
                    patch.object(sys, 'argv', ['probe', str(output), '--fresh-owned-flow-allowed']), \
                    patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO):
                self.assertEqual(0, probe.main())
                with self.assertRaises(SystemExit):
                    probe.main()
            self.assertEqual(list(range(18)), [value['native']['observed'] for value in observations])
            self.assertTrue(all(value['completed'] is False for value in observations))
            self.assertEqual(2, len(observations[0]['native']['rows'][0]['samples']))
            self.assertIsNone(observations[0]['native']['rows'][1])
            final = json.loads(output.read_bytes())
            self.assertTrue(final['completed'])
            self.assertTrue(final['restored'])
            self.assertTrue(final['diagnostic']['positive_control_matched'])
            self.assertEqual([], list(Path(directory).glob('*.tmp')))

    def test_server_payloads_compile_under_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game-compatible Python2 interpreter unavailable')
        for payload in (probe.start_payload(self.identity, 'a' * 64, True),
                        probe.STATUS % (probe.MARKER, self.identity), probe.RESTORE % (probe.MARKER, self.identity)):
            result = subprocess.run([str(pypy), '-c', 'compile(%r,"lifecycle","exec")' % payload],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

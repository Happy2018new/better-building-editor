"""Single-door diagnosis preserves both native half states through failed setters."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_single_door as probe


class NativeSingleDoorTests(unittest.TestCase):
    def native_setup(self, fail_state=False):
        rows, support, reserved = probe.single_pair((4, -48, 4))
        values, properties, calls = {}, {}, []
        foot = (.5, -60., .5)
        class Info:
            def GetBlockNew(self, pos, dimension):
                return values.get(pos, {'name': 'minecraft:air', 'aux': 0})
            def GetLiquidBlock(self, pos, dimension):
                return None
            def SetBlockNew(self, pos, value, handling, dimension, legacy, updates):
                calls.append((pos, copy.deepcopy(value), updates))
                value = dict(value)
                if isinstance(value['name'], bytes):
                    value['name'] = value['name'].decode('utf8')
                changed = self.GetBlockNew(pos, dimension) != value
                values[pos] = value
                if value['name'] == 'minecraft:wooden_door':
                    properties[pos] = copy.deepcopy(rows[int(pos[1] == -47)]['states'])
                    if pos[1] == -48:
                        values[(4, -47, 4)] = {'name': 'minecraft:wooden_door', 'aux': 8}
                        properties[(4, -47, 4)] = copy.deepcopy(rows[1]['states'])
                else:
                    properties[pos] = {}
                return changed
        class State:
            def GetBlockStates(self, pos, dimension):
                return properties.get(pos)
            def GetBlockAuxValueFromStates(self, name, data):
                return 8 if data['upper_block_bit'] else 0
            def SetBlockStates(self, pos, data, dimension):
                if fail_state:
                    raise RuntimeError('native state failure')
                properties[pos] = copy.deepcopy(data)
                return True
        info, state = Info(), State()
        factory = SimpleNamespace(CreateBlockInfo=lambda level: info, CreateBlockState=lambda level: state,
                                  CreateDimension=lambda player: SimpleNamespace(GetEntityDimensionId=lambda: 0),
                                  CreatePos=lambda player: SimpleNamespace(GetFootPos=lambda: foot))
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId = lambda: 'test-level'
        api.GetPlayerList = lambda: ['test-player']
        api.GetMinecraftVersion = lambda: 'test-runtime'
        server = ModuleType('modern_projection.server_system')
        server.WorldAdapter = SimpleNamespace(_native_tree=lambda value: value)
        modules = {'mod': ModuleType('mod'), 'mod.server': ModuleType('mod.server'),
                   'mod.server.extraServerApi': api, 'modern_projection': ModuleType('modern_projection'),
                   'modern_projection.server_system': server}
        namespace = {}
        with mock.patch.dict(sys.modules, modules):
            try:
                exec(probe.SETUP % (probe.MARKER, rows, support, reserved), namespace)
                report = probe.json.loads(namespace['_result'])
                exec(probe.CLEAR % probe.MARKER, namespace)
                cleanup = probe.json.loads(namespace['_result'])
            finally:
                if hasattr(sys, probe.MARKER):
                    delattr(sys, probe.MARKER)
        return rows, reserved, report, cleanup, calls

    def test_native_no_change_return_is_recorded_with_both_halves_and_exact_states(self):
        rows, reserved, report, cleanup, calls = self.native_setup()
        self.assertIsNone(report['error'])
        self.assertEqual([True, False, True, True], [step['returned'] for step in report['steps']])
        self.assertTrue(all(len(step['both_halves']) == 2 for step in report['steps']))
        self.assertTrue(probe.shapes.replicated(report['after'], rows))
        self.assertTrue(cleanup['restored'])
        self.assertTrue(cleanup['player_unchanged'])
        self.assertEqual(17, len(reserved))
        self.assertTrue(all(updates is False for pos, value, updates in calls))

    def test_native_setter_exception_preserves_actual_halves_and_complete_cleanup(self):
        rows, reserved, report, cleanup, calls = self.native_setup(fail_state=True)
        self.assertIn('native state failure', report['error'])
        self.assertEqual(2, len(report['steps']))
        self.assertEqual(2, len(report['after']['rows']))
        self.assertTrue(cleanup['restored'])
        cleared = {pos for pos, value, updates in calls if value['name'] == 'minecraft:air'}
        self.assertEqual(set(reserved), cleared)

    def failed_observation(self, failed_side):
        rows, support, reserved = probe.single_pair((4, -48, 4))
        snapshot = {'runtime': 'test-runtime', 'rows': [
            {'pos': row['pos'], 'value': row['value'], 'states': row['states']} for row in rows]}
        binding = {key: 'test' for key in ('id', 'owner', 'game_pid', 'game_identity',
                                         'mcdk_pid', 'mcdk_identity', 'mcp_url', 'game_executable')}
        binding['project'] = str(ROOT)
        binding['noactivation'] = {'requested': True, 'background_safe': True, 'window_noactivate': True,
                                  'mcdk': {'path': 'binary', 'sha256': 'test'},
                                  'dll': {'path': 'guard', 'sha256': 'test'}}
        writes = []
        def execute(client, code, server):
            if code == probe.shapes.PREFLIGHT % probe.MARKER:
                return {'origin': (4, -48, 4)}
            if code == probe.SETUP % (probe.MARKER, rows, support, reserved):
                return {'error': None, 'after': snapshot}
            if code == probe.CLEAR % probe.MARKER:
                return {'restored': True, 'player_unchanged': True}
            if code == probe.READ_CLIENT % [{'pos': pos} for pos in reserved]:
                return {'rows': [{'pos': pos, 'value': ('minecraft:air', 0)} for pos in reserved]}
            side = 'server' if server else 'client'
            if side == failed_side:
                raise RuntimeError('native %s palette unavailable' % side)
            return copy.deepcopy(snapshot)
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(probe.os.environ, clear=False):
            output = Path(folder) / 'report.json'
            with mock.patch.object(probe.shapes, 'load_session', return_value=binding), \
                 mock.patch.object(probe.shapes, 'source_record', return_value={'sha256': 'test'}), \
                 mock.patch.object(probe.shapes, 'Client'), \
                 mock.patch.object(probe.shapes, 'execute', side_effect=execute), \
                 mock.patch.object(probe.time, 'sleep'), \
                 mock.patch.object(probe.shapes, 'write', side_effect=lambda path, data: writes.append(copy.deepcopy(data))):
                report = probe.probe(output, Path(folder) / 'session.json', 'test')
        return report, writes

    def test_delayed_client_failure_preserves_server_snapshots_and_cleanup(self):
        report, writes = self.failed_observation('client')
        self.assertFalse(report['completed'])
        self.assertFalse(report['exact_native_pair'])
        self.assertTrue(report['restored'])
        self.assertEqual([('after_200ms', 'client'), ('later', 'client')],
                         [(error['stage'], error['side']) for error in report['observation_errors']])
        self.assertTrue(all('server' in report[stage] and 'client' not in report[stage]
                            for stage in ('after_200ms', 'later')))
        self.assertTrue(any('server' in write.get('after_200ms', {}) and not write['observation_errors']
                            for write in writes))
        self.assertTrue(report['cleanup']['player_unchanged'])
        self.assertEqual(17, len(report['client_after_cleanup']['rows']))

    def test_delayed_server_failure_still_records_client_observations(self):
        report, writes = self.failed_observation('server')
        self.assertFalse(report['completed'])
        self.assertFalse(report['exact_native_pair'])
        self.assertTrue(report['restored'])
        self.assertTrue(all('client' in report[stage] and 'server' not in report[stage]
                            for stage in ('after_200ms', 'later')))
        self.assertEqual(['server', 'server'], [error['side'] for error in report['observation_errors']])

    def test_frozen_native_diagnosis_is_exact_immediate_evidence_only(self):
        base = ROOT / 'tools/data/native_state_transform_shapes_r11.door-single-diagnostic'
        raw, source = Path(str(base) + '.json').read_bytes(), Path(str(base) + '.probe.py').read_bytes()
        self.assertEqual('a2e48d95e2a064b01bc8d2725c8e6889757b7f27bf5308fe4e462a3fb95bede9',
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual('6887bd5bf129483fe8406d289102b581fd4fa1486ddd9f51e512b99ed82f9764',
                         hashlib.sha256(source).hexdigest())
        report = probe.json.loads(raw)
        self.assertEqual(hashlib.sha256(source).hexdigest(), report['host_sources']['probe']['sha256'])
        self.assertFalse(report['completed'])
        self.assertFalse(report['physical_orientation_accepted'])
        self.assertTrue(report['restored'])
        self.assertNotIn('after_200ms', report)
        self.assertNotIn('later', report)
        self.assertNotIn('exact_native_pair', report)
        self.assertIn('native client palette unavailable', report['error'])
        self.assertTrue(probe.shapes.replicated(report['setup']['after'], report['requested']))
        self.assertEqual([True, False, True, True],
                         [step['returned'] for step in report['setup']['steps']])
        self.assertTrue(all(probe.shapes.replicated({'rows': step['both_halves']}, report['requested'])
                            for step in report['setup']['steps']))
        self.assertTrue(report['cleanup']['player_unchanged'])
        self.assertEqual(17, len(report['client_after_cleanup']['rows']))


if __name__ == '__main__':
    unittest.main()

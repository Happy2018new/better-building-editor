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
from projection.cell import freeze, thaw


class NativeSingleDoorTests(unittest.TestCase):
    def native_setup(self, fail_state=False, guard_fault=None, support_refused=False):
        rows, support, reserved = probe.single_pair((4, -48, 4))
        values, properties, calls = {}, {}, []
        foot = (.5, -60., .5)
        foot_reads = []
        chunk_reads = []
        def get_foot():
            foot_reads.append(True)
            if guard_fault == 'invalid_foot':
                return (.5, 32768., .5)
            if guard_fault == 'moved_before_marker' and len(foot_reads) >= 3:
                return (.5, -59., .5)
            return foot
        def loaded_chunk(dimension, pos):
            chunk_reads.append(pos)
            return not (guard_fault == 'chunk_unloaded' or
                        guard_fault == 'chunk_unloaded_before_marker' and len(chunk_reads) >= 2)
        class Info:
            def GetBlockNew(self, pos, dimension):
                if guard_fault == 'reserve_non_air' and pos == support:
                    return {'name': 'minecraft:dirt', 'aux': 0}
                return values.get(pos, {'name': 'minecraft:air', 'aux': 0})
            def GetLiquidBlock(self, pos, dimension):
                return None
            def SetBlockNew(self, pos, value, handling, dimension, legacy, updates):
                calls.append((pos, copy.deepcopy(value), updates))
                if support_refused and pos == support and value['name'] == 'minecraft:stone':
                    return False
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
                                  CreateDimension=lambda player: SimpleNamespace(
                                      GetEntityDimensionId=lambda: 1 if guard_fault == 'dimension' else 0),
                                  CreatePos=lambda player: SimpleNamespace(GetFootPos=get_foot),
                                  CreateChunkSource=lambda level: SimpleNamespace(
                                      CheckChunkState=loaded_chunk))
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId = lambda: 'test-level'
        api.GetPlayerList = lambda: ['test-player']
        api.GetMinecraftVersion = lambda: probe.load_gate.RUNTIME
        server = ModuleType('modern_projection.server_system')
        server.WorldAdapter = SimpleNamespace(_native_tree=lambda value: value)
        modules = {'mod': ModuleType('mod'), 'mod.server': ModuleType('mod.server'),
                   'mod.server.extraServerApi': api, 'modern_projection': ModuleType('modern_projection'),
                   'modern_projection.server_system': server}
        namespace = {}
        raw = {'runtime': probe.load_gate.RUNTIME, 'level': 'test-level', 'players': ['test-player'],
               'player': 'test-player', 'dimension': 0, 'foot': foot, 'marker_present': False}
        status, anchor = probe.load_gate.anchor_status(raw, probe.single_pair)
        with mock.patch.dict(sys.modules, modules):
            try:
                exec(probe.setup_code(anchor), namespace)
                report = probe.json.loads(namespace['_result'])
                exec(probe.CLEAR % probe.MARKER, namespace)
                cleanup = probe.json.loads(namespace['_result'])
            finally:
                if hasattr(sys, probe.MARKER):
                    delattr(sys, probe.MARKER)
        return rows, reserved, report, cleanup, calls

    def test_same_setup_guard_refuses_invalid_anchor_unloaded_chunks_movement_and_occupied_reserve(self):
        for fault in ('invalid_foot', 'dimension', 'chunk_unloaded', 'chunk_unloaded_before_marker',
                      'moved_before_marker', 'reserve_non_air'):
            with self.subTest(fault=fault):
                rows, reserved, report, cleanup, calls = self.native_setup(guard_fault=fault)
                self.assertFalse(report['mutation_attempted'])
                self.assertIsNone(report['support_write'])
                self.assertEqual([], report['steps'])
                self.assertEqual([], report['write_intents'])
                self.assertEqual([], calls)
                self.assertFalse(cleanup['marker_present'])

    def test_support_refusal_retains_actual_air_and_one_support_intent_then_restores_reserve(self):
        rows, reserved, report, cleanup, calls = self.native_setup(support_refused=True)
        self.assertTrue(report['mutation_attempted'])
        self.assertEqual('support_setter_refused_or_not_applied', report['classification'])
        self.assertEqual('AssertionError: Support not stone', report['error'])
        self.assertFalse(report['support_write']['returned'])
        self.assertEqual({'name': 'minecraft:air', 'aux': 0}, report['support_write']['value'])
        self.assertEqual([], report['steps'])
        self.assertEqual(['support'], [row['kind'] for row in report['write_intents']])
        self.assertEqual(report['write_intents'], cleanup['recovered_setup']['write_intents'])
        self.assertEqual(17, len(cleanup['clear_steps']))
        self.assertTrue(cleanup['restored'])

    def test_native_no_change_return_is_recorded_with_both_halves_and_exact_states(self):
        rows, reserved, report, cleanup, calls = self.native_setup()
        self.assertIsNone(report['error'])
        self.assertTrue(report['mutation_attempted'])
        self.assertEqual(5, len(report['write_intents']))
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

    def native_client(self, upper_value=('minecraft:wooden_door', 8), pair_available=True, loaded=True):
        rows, support, reserved = probe.single_pair((4, -48, 4))
        lower, upper = (tuple(row['pos']) for row in rows)
        values = {lower: ('minecraft:wooden_door', 0), upper: upper_value,
                  tuple(support): ('minecraft:stone', 0)}
        pair_data = {'volume': (1, 1, 2), 'common': {('minecraft:wooden_door', 0): [0]},
                     'states': {('minecraft:wooden_door', 0): rows[0]['states']}}
        calls = []
        class Block:
            def GetBlockPaletteBetweenPos(self, low, high, eliminate_air):
                calls.append((low, high, eliminate_air))
                if low == upper or low == lower and high == upper and not pair_available:
                    return None
                data = pair_data if low == lower else {'volume': (1, 1, 1),
                    'common': {('minecraft:stone', 0): [0]}, 'states': {('minecraft:stone', 0): {}}}
                return SimpleNamespace(SerializeBlockPalette=lambda: copy.deepcopy(data))
        api = ModuleType('mod.client.extraClientApi')
        api.GetEngineCompFactory = lambda: SimpleNamespace(CreateBlock=lambda level: Block(),
            CreateBlockInfo=lambda level: SimpleNamespace(GetBlock=lambda pos: values[pos]))
        api.GetLevelId = lambda: 'test-level'
        api.GetMinecraftVersion = lambda: 'test-runtime'
        api.GetSystem = lambda namespace, name: SimpleNamespace(projection_loaded_chunks={(0, 0, 0)}) if loaded else None
        cell = ModuleType('modern_projection.projection.cell')
        cell.freeze = freeze
        modules = {'mod': ModuleType('mod'), 'mod.client': ModuleType('mod.client'),
                   'mod.client.extraClientApi': api, 'modern_projection': ModuleType('modern_projection'),
                   'modern_projection.projection': ModuleType('modern_projection.projection'),
                   'modern_projection.projection.cell': cell}
        namespace = {}
        with mock.patch.dict(sys.modules, modules):
            exec(probe.READ_CLIENT_PAIR % (rows, support, 0), namespace)
        return probe.json.loads(namespace['_result']), rows, support, calls

    def test_whole_pair_palette_retains_documented_upper_omission_and_actual_front(self):
        client, rows, support, calls = self.native_client()
        server = {'rows': [{'pos': row['pos'], 'value': row['value'], 'states': row['states']} for row in rows]}
        result = probe.diagnose_pair(server, client, rows, support, [0, 8])
        self.assertEqual('documented_upper_omission_observed', result['classification'])
        self.assertTrue(result['data_replication_verified'])
        self.assertFalse(result['client_typed_upper_verified'])
        self.assertFalse(result['physical_orientation_accepted'])
        self.assertEqual([0], result['palette_covered_indices'])
        self.assertEqual([1], result['palette_omitted_indices'])
        self.assertEqual(('minecraft:wooden_door', 8), probe.shapes.pair(client['fronts_before'][1]['value']))
        self.assertFalse(client['palettes']['upper']['available'])
        self.assertIsNone(client['palettes']['upper']['serialized'])
        self.assertEqual((tuple(rows[0]['pos']), tuple(rows[1]['pos']), False), calls[0])
        self.assertEqual(4, len(calls))
        self.assertNotIn(1, probe.palette_rows(client, rows))

    def test_missing_client_front_and_unavailable_pair_remain_unresolved(self):
        for upper, available, classification in ((None, True, 'client_front_unavailable_loading_unresolved'),
                (('minecraft:air', 0), True, 'client_front_not_replicated'),
                (('minecraft:wooden_door', 8), False, 'pair_palette_unavailable')):
            with self.subTest(classification=classification):
                client, rows, support, calls = self.native_client(upper, available, loaded=False)
                server = {'rows': [{'pos': row['pos'], 'value': row['value'], 'states': row['states']} for row in rows]}
                result = probe.diagnose_pair(server, client, rows, support, [0, 8])
                self.assertEqual(classification, result['classification'])
                self.assertFalse(result['data_replication_verified'])
                self.assertFalse(result['loaded_chunk_tracking']['available'])

    def test_python2_byte_key_palette_verifies_observed_lower_without_synthesizing_upper(self):
        client, rows, support, calls = self.native_client()
        data = thaw(client['palettes']['pair']['serialized'])
        data = {key.encode('ascii'): value for key, value in data.items()}
        for layer in (b'common', b'states'):
            data[layer] = {(name.encode('ascii'), aux): value for (name, aux), value in data[layer].items()}
        data[b'states'] = {material: {key.encode('ascii'): value.encode('ascii') if isinstance(value, str) else value
                                     for key, value in properties.items()}
                           for material, properties in data[b'states'].items()}
        client['palettes']['pair']['serialized'] = freeze(data)
        self.assertIsNone(thaw(client['palettes']['pair']['serialized']).get('volume'))
        server = {'rows': [{'pos': row['pos'], 'value': row['value'], 'states': row['states']} for row in rows]}
        result = probe.diagnose_pair(server, client, rows, support, [0, 8])
        self.assertTrue(result['data_replication_verified'])
        self.assertEqual('documented_upper_omission_observed', result['classification'])
        self.assertEqual([0], result['palette_covered_indices'])
        self.assertEqual([1], result['palette_omitted_indices'])
        self.assertFalse(result['client_typed_upper_verified'])
        self.assertFalse(result['physical_orientation_accepted'])

    def test_duplicate_text_and_byte_metadata_keys_cannot_accept_a_palette(self):
        client, rows, support, calls = self.native_client()
        data = thaw(client['palettes']['pair']['serialized'])
        data[b'volume'] = data['volume']
        client['palettes']['pair']['serialized'] = freeze(data)
        server = {'rows': [{'pos': row['pos'], 'value': row['value'], 'states': row['states']} for row in rows]}
        result = probe.diagnose_pair(server, client, rows, support, [0, 8])
        self.assertEqual('pair_palette_invalid', result['classification'])
        self.assertIn('duplicate text/byte metadata keys', result['palette_error'])
        self.assertFalse(result['data_replication_verified'])

    def test_typed_state_index_and_during_read_changes_cannot_verify_replication(self):
        for fault in ('duplicate', 'out_of_range', 'wrong_bounds', 'boolean_type', 'front_changed', 'server_changed'):
            with self.subTest(fault=fault):
                client, rows, support, calls = self.native_client()
                server = {'rows': [{'pos': row['pos'], 'value': row['value'], 'states': copy.deepcopy(row['states'])}
                                  for row in rows]}
                data = thaw(client['palettes']['pair']['serialized'])
                if fault == 'duplicate':
                    data['common'][('minecraft:stone', 0)] = [0]
                elif fault == 'out_of_range':
                    data['common'][('minecraft:wooden_door', 0)] = [2]
                elif fault == 'wrong_bounds':
                    client['palettes']['pair']['low'] = (5, -48, 4)
                elif fault == 'boolean_type':
                    data['states'][('minecraft:wooden_door', 0)]['open_bit'] = 0
                elif fault == 'front_changed':
                    client['fronts_after'][1]['value'] = ('minecraft:air', 0)
                else:
                    server['rows'][0]['states']['open_bit'] = True
                client['palettes']['pair']['serialized'] = freeze(data)
                result = probe.diagnose_pair(server, client, rows, support, [0, 8])
                self.assertFalse(result['data_replication_verified'])
                self.assertFalse(result['physical_orientation_accepted'])

    def failed_observation(self, failed_side, client_observation=None, setup_uncertain=False,
                           setup_guard_fails=False, load_fails=False):
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
        raw = {'runtime': probe.load_gate.RUNTIME, 'level': 'test-level', 'players': ['test-player'],
               'player': 'test-player', 'dimension': 0, 'foot': [.5, -60., .5], 'marker_present': False}
        status, anchor = probe.load_gate.anchor_status(raw, probe.single_pair)
        def execute(client, code, server):
            if code == probe.setup_code(anchor):
                if setup_uncertain:
                    raise TimeoutError('setup reply lost after possible mutation')
                if setup_guard_fails:
                    return {'mutation_attempted': False, 'classification': 'world_player_not_loaded_before_setup'}
                return {'error': None, 'mutation_attempted': True, 'after': snapshot, 'steps': [
                    {'method': 'SetBlockNew', 'legacy_aux': 0}, {'method': 'SetBlockNew', 'legacy_aux': 8}]}
            if code == probe.CLEAR % probe.MARKER:
                return {'restored': True, 'player_unchanged': True}
            if code == probe.READ_CLIENT % [{'pos': pos} for pos in reserved]:
                return {'rows': [{'pos': pos, 'value': ('minecraft:air', 0)} for pos in reserved]}
            side = 'server' if server else 'client'
            if side == failed_side:
                raise RuntimeError('native %s palette unavailable' % side)
            if not server and client_observation is not None:
                return copy.deepcopy(client_observation)
            return copy.deepcopy(snapshot)
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(probe.os.environ, clear=False):
            output = Path(folder) / 'report.json'
            with mock.patch.object(probe.shapes, 'load_session', return_value=binding), \
                 mock.patch.object(probe.shapes, 'source_record', return_value={'sha256': 'test'}), \
                 mock.patch.object(probe, 'DeadlineClient'), \
                 mock.patch.object(probe.load_gate, 'wait_for_load', return_value=anchor,
                                   side_effect=probe.load_gate.LoadPreflightError('world not loaded') if load_fails else None), \
                 mock.patch.object(probe.shapes, 'execute', side_effect=execute), \
                 mock.patch.object(probe.time, 'sleep'), \
                 mock.patch.object(probe.shapes, 'write', side_effect=lambda path, data: writes.append(copy.deepcopy(data))):
                report = probe.probe(output, Path(folder) / 'session.json', 'test')
        return report, writes

    def test_uncertain_setup_reply_keeps_mutation_intent_and_attempts_cleanup_without_replay(self):
        report, writes = self.failed_observation(None, setup_uncertain=True)
        self.assertFalse(report['completed'])
        self.assertTrue(report['mutation_attempted'])
        self.assertTrue(report['setup_intent']['sent'])
        self.assertFalse(report['setup_intent']['acknowledged'])
        self.assertTrue(report['setup_intent']['response_uncertain'])
        self.assertTrue(report['cleanup_intent']['sent'])
        self.assertTrue(report['cleanup_intent']['acknowledged'])
        self.assertTrue(report['restored'])
        self.assertTrue(any(row['setup_intent']['sent'] and 'setup' not in row for row in writes))

    def test_load_failure_and_explicit_setup_refusal_never_call_fixture_cleanup(self):
        for load_fails in (False, True):
            report, writes = self.failed_observation(None, setup_guard_fails=True, load_fails=load_fails)
            self.assertFalse(report['mutation_attempted'])
            self.assertFalse(report['cleanup_intent']['sent'])
            self.assertEqual({'restored': True, 'mutation_attempted': False}, report['cleanup'])
            self.assertTrue(report['restored'])
            self.assertEqual(not load_fails, report['setup_intent']['sent'])
            self.assertEqual(not load_fails, report['setup_intent']['acknowledged'])

    def test_delayed_client_failure_preserves_server_snapshots_and_cleanup(self):
        report, writes = self.failed_observation('client')
        self.assertFalse(report['completed'])
        self.assertFalse(report['exact_native_pair'])
        self.assertTrue(report['restored'])
        self.assertTrue(report['server_exact_native_pair'])
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
        self.assertFalse(report['server_exact_native_pair'])
        self.assertTrue(all('client' in report[stage] and 'server' not in report[stage]
                            for stage in ('after_200ms', 'later')))
        self.assertEqual(['server', 'server'], [error['side'] for error in report['observation_errors']])

    def test_bounded_pair_diagnosis_and_unavailable_palette_both_restore_reserve(self):
        for available in (True, False):
            with self.subTest(pair_available=available):
                client, rows, support, calls = self.native_client(pair_available=available)
                report, writes = self.failed_observation(None, client)
                self.assertTrue(report['completed'])
                self.assertTrue(report['restored'])
                self.assertTrue(report['server_exact_native_pair'])
                self.assertEqual(available, report['data_replication_verified'])
                self.assertFalse(report['client_typed_pair_verified'])
                self.assertFalse(report['exact_native_pair'])
                self.assertFalse(report['physical_orientation_accepted'])
                self.assertEqual(17, len(report['client_after_cleanup']['rows']))

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

    def test_prepared_pair_probe_and_plan_are_frozen_without_native_acceptance(self):
        directory = ROOT / 'tools/data'
        prepared = probe.json.loads((directory / 'native_state_transform_shapes_r11.door-pair-prepared.json').read_bytes())
        for flag in ('native_attempted', 'physical_orientation_accepted', 'production_mapping_changed'):
            self.assertFalse(prepared[flag])
        self.assertTrue(prepared['root_review_required_before_native_attempt'])
        self.assertEqual((1, 17, 2, 4), tuple(prepared[key] for key in
                         ('fixture_door_pairs', 'reserved_cells', 'delayed_observations',
                          'client_palette_queries_per_observation')))
        for filename, expected in prepared['files'].items():
            self.assertEqual(expected, hashlib.sha256((directory / filename).read_bytes()).hexdigest())
        self.assertEqual('6fe41694606a33f6ede15cbccf72f4c4a951dcf424017ce524af1ae0281517a8',
            hashlib.sha256((directory / 'native_state_transform_shapes_r11.door-pair-prepared.probe.py').read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()

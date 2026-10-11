"""Host fault evidence for sealed liquid captures; no game or pixels are accepted."""
import copy
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
POSE = {'stable': {'screen': (80, 60), 'fov': 70.}}
sys.path.insert(0, str(ROOT / 'tools'))
import capture_pure_liquid_native_controls as controls
from projection.cell import AIR, encode, make_cell
from projection import cell, world_capture


def snapshot(state):
    return {'valid': True, 'raw_palette': ['diagnostic_fake'],
            'cells': [{'pos': pos, 'foreground': value[0], 'background': value[1], 'actor': value[2]}
                      for pos, value in sorted(state.items())]}


def png_record(path, session, blank=False):
    frame = Image.new('RGB', (80, 60), (35, 45, 55))
    if not blank:
        ImageDraw.Draw(frame).rectangle((15, 10, 45, 40), fill=(10, 80, 210))
    frame.save(path)
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    capture = {key: session[key] for key in ('session_file', 'owner', 'game_pid', 'game_identity')}
    capture.update(ok=True, reliable=True, background_only=True, background_safe=True,
                   backend='Windows.Graphics.Capture', window={'pid': session['game_pid']},
                   frame={'ok': True, 'request_qpc_100ns': 100, 'frame_qpc_100ns': 101,
                          'width': frame.width, 'height': frame.height},
                   sha256=digest, bytes=len(payload))
    return {'path': str(path), 'sha256': digest, 'bytes': len(payload), 'size': frame.size,
            'background_only': True, 'capture': capture}


class FaultHarness:
    def __init__(self, plan, output, report=None):
        self.plan, self.report = plan, report if report is not None else {}
        self.args = SimpleNamespace(output=output)
        self.session = {'session_file': str(output.parent / 'session.json'), 'owner': 'test-owner',
                        'game_pid': 321, 'game_identity': 'test-process-creation'}
        self.state = controls.expected_native(
            [(pos, encode(plan['shell_value'])) for pos in plan['shell']] +
            [(plan['platform'], encode(('minecraft:stone', 0)))], plan['reserved'])
        self.events, self.checkpoints = [], []
        self.residual = self.fail_frame = self.invalid_snapshot = self.drift = False
        self.frame_count = 0

    def checkpoint(self):
        self.checkpoints.append(copy.deepcopy(self.report))

    def settle(self):
        self.events.append(('settle',))

    def snapshot(self, positions):
        self.events.append(('snapshot', tuple(map(tuple, positions))))
        observed = snapshot(self.state)
        if self.invalid_snapshot:
            observed['valid'] = False
        return {'server': observed, 'client': copy.deepcopy(observed)}

    def clear(self, positions):
        selected = set(map(tuple, positions))
        self.events.append(('clear', selected))
        for pos in selected:
            self.state[pos] = (AIR, AIR, False)
        if self.residual:
            self.state[tuple(self.plan['cavity'][0])] = (AIR, ('minecraft:water', 0), False)
        return {'writes': [{'pos': pos, 'written': True} for pos in positions],
                'after': snapshot(self.state)}

    def write(self, cells):
        self.events.append(('write', copy.deepcopy(cells)))
        if any(self.state[tuple(pos)] != (tuple(self.plan['shell_value']), AIR, False)
               for pos in self.plan['shell']):
            raise RuntimeError('Shell gate failed before liquid seed')
        for pos, value in controls.expected_native(cells, self.plan['cavity']).items():
            self.state[pos] = value
        if self.drift:
            self.state[tuple(self.plan['cell_origin'])] = (('minecraft:flowing_water', 7), AIR, False)
        return {'writes': [{'pos': pos, 'written': True} for pos, value in cells],
                'after': snapshot(self.state)}

    def frame(self, label, pose):
        self.frame_count += 1
        self.events.append(('frame', label))
        if self.fail_frame and self.frame_count == 2:
            raise RuntimeError('Uncertain native capture identity')
        path = self.args.output.with_name(self.args.output.stem + '_' + label + '_native.png')
        record = png_record(path, self.session)
        record.update(camera_before=copy.deepcopy(POSE['stable']), camera_after=copy.deepcopy(POSE['stable']))
        return record

    def marker(self):
        return {'owned': True, 'player_foot': (0., 4., 0.)}

    def restore_player(self):
        self.events.append(('restore_player',))
        return {'player_foot': (0., 4., 0.)}

    def delete_marker(self):
        self.events.append(('delete_marker',))


class NativeScriptWorld:
    def __init__(self, plan):
        self.plan = plan
        self.state = {tuple(pos): (AIR, AIR, False) for pos in plan['reserved']}
        self.writes = []
        self.failed_write = None
        self.server_sys = SimpleNamespace()
        self.api = SimpleNamespace(GetPlayerList=lambda: ['test-player'], GetMinecraftVersion=lambda: 'test-runtime')
        world = self

        class Palette:
            def __init__(self, low, high):
                self.low, self.high = low, high

            def SerializeBlockPalette(self):
                size = tuple(self.high[i] - self.low[i] + 1 for i in range(3))
                raw = {'volume': (size[2], size[0], size[1]), 'common': {}, 'extra': {}, 'actor': {}}
                for x, y, z in controls.itertools.product(range(size[0]), range(size[1]), range(size[2])):
                    pos = (self.low[0] + x, self.low[1] + y, self.low[2] + z)
                    value = world.state.get(pos, (AIR, AIR, False))
                    index = (y * size[0] + x) * size[2] + z
                    for key, material in (('common', value[0]), ('extra', value[1])):
                        raw[key].setdefault(material, []).append(index)
                return raw

        class Adapter:
            def __init__(self, player):
                self.player, self.dimension = player, 0
                self.palette_block = SimpleNamespace(GetBlockPaletteBetweenPos=lambda dimension, low, high, flag:
                                                      Palette(tuple(low), tuple(high)))

            def read(self, pos):
                value = world.state.get(tuple(pos), (AIR, AIR, False))
                return make_cell(value[0], value[1])

            def write(self, pos, value, origin=(0, 0, 0)):
                world.writes.append((tuple(pos), value))
                if tuple(pos) == world.failed_write:
                    return False
                world.state[tuple(pos)] = (cell.foreground(value), cell.background(value), False)
                return True

        self.modules = {'sys': self.server_sys, 'mod': SimpleNamespace(server=SimpleNamespace(extraServerApi=self.api)),
                        'mod.server': SimpleNamespace(extraServerApi=self.api), 'mod.server.extraServerApi': self.api,
                        'modern_projection': SimpleNamespace(projection=SimpleNamespace(cell=cell, world_capture=world_capture)),
                        'modern_projection.server_system': SimpleNamespace(WorldAdapter=Adapter),
                        'modern_projection.projection.cell': cell,
                        'modern_projection.projection.world_capture': world_capture}

    def run(self, source):
        scope = {}
        with patch.dict(sys.modules, self.modules):
            exec(compile(source, '<native-liquid-fault-world>', 'exec'), scope)
        return json.loads(scope['_result'])


class PureLiquidNativeControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / 'controls.json'
        self.plan = controls.fixture_plan(controls.CASES[0], (8, 90, -3), (4, 88, -7))

    def test_sealed_plan_is_bounded_and_preserves_exact_four_public_sources(self):
        self.assertEqual(42, len(self.plan['shell']))
        self.assertEqual(3, len(self.plan['cavity']))
        self.assertFalse(set(self.plan['shell']) & set(self.plan['cavity']))
        shell = set(self.plan['shell'])
        cavity = set(self.plan['cavity'])
        for pos in cavity:
            for offset in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                self.assertIn(tuple(pos[i] + offset[i] for i in range(3)), shell | cavity)
        for case in controls.CASES:
            plan = controls.fixture_plan(case, self.plan['cell_origin'], self.plan['platform'])
            for control in controls.CONTROLS:
                public = controls.source_document(case, isolated=True, control=control)
                self.assertEqual([(pos, encode(value)) for pos, value in sorted(public.blocks.items())],
                                 plan['controls'][control]['isolated_cells'])
            self.assertTrue(plan['context_changed'])
            self.assertFalse(plan['public_controls_eligible'])

    def test_unsupported_case_is_rejected_before_native_work(self):
        with self.assertRaisesRegex(ValueError, 'two source foreground'):
            controls.fixture_plan('water_depth_7_background', (0, 0, 0), (-4, -2, -4))

    def test_incomplete_shell_prevents_any_requested_liquid_write(self):
        harness = FaultHarness(self.plan, self.output)
        harness.state[self.plan['shell'][0]] = (AIR, AIR, False)
        row = {}
        with self.assertRaisesRegex(RuntimeError, 'Shell gate failed'):
            controls.capture_control(harness, self.plan, 'supported_positive', row, POSE, None)
        self.assertFalse(any(event[0] == 'frame' for event in harness.events))
        self.assertEqual((AIR, AIR, False), harness.state[self.plan['cell_origin']])
        self.assertFalse(row['completed'])
        self.assertIn('error', row)

    def test_uncertain_later_capture_preserves_earlier_capture_and_after_snapshot(self):
        report = {'controls': {}}
        harness = FaultHarness(self.plan, self.output, report)
        harness.fail_frame = True
        first = report['controls']['supported_positive'] = {}
        controls.capture_control(harness, self.plan, 'supported_positive', first, POSE, None)
        second = report['controls']['supported_negative'] = {}
        with self.assertRaisesRegex(RuntimeError, 'Uncertain native capture'):
            controls.capture_control(harness, self.plan, 'supported_negative', second, POSE, (80, 60))
        self.assertTrue(first['completed'])
        self.assertTrue(Path(first['capture']['path']).is_file())
        self.assertFalse(second['completed'])
        self.assertIn('native_before_capture', second)
        self.assertIn('native_after_capture', second)
        self.assertTrue(harness.checkpoints[-1]['controls']['supported_positive']['completed'])

    def test_native_state_drift_is_recorded_without_forcing_requested_state(self):
        harness = FaultHarness(self.plan, self.output)
        harness.drift = True
        row = {}
        controls.capture_control(harness, self.plan, 'liquid_only', row, POSE, None)
        self.assertTrue(row['completed'])
        self.assertFalse(row['native_gate']['declared_context_state_passed'])
        self.assertFalse(row['native_gate']['public_controls_eligible'])
        self.assertEqual(1, sum(event[0] == 'write' for event in harness.events))
        self.assertEqual(('minecraft:flowing_water', 7), harness.state[self.plan['cell_origin']][0])
        self.assertTrue(all(corner['status'] == 'unobservable' for corner in row['corners']))

    def test_before_after_extra_layer_drift_fails_even_when_source_stays_exact(self):
        harness = FaultHarness(self.plan, self.output)
        requested = self.plan['controls']['liquid_only']['cells']
        harness.write(requested)
        before = harness.snapshot(self.plan['reserved'])
        bottom = self.plan['cavity'][0]
        harness.state[bottom] = (AIR, ('minecraft:water', 0), False)
        after = harness.snapshot(self.plan['reserved'])
        gate = controls.capture_native_gate(before, after, self.plan, requested)
        self.assertFalse(gate['declared_context_state_passed'])
        self.assertEqual(bottom, gate['sides']['server']['cavity_changes']['changes'][0]['pos'])

    def test_duplicate_missing_invalid_and_actor_cells_cannot_supply_a_state_gate(self):
        harness = FaultHarness(self.plan, self.output)
        harness.write(self.plan['controls']['supported_positive']['cells'])
        state = harness.snapshot(self.plan['reserved'])
        self.assertTrue(controls.capture_native_gate(state, state, self.plan,
                        self.plan['controls']['supported_positive']['cells'])['declared_context_state_passed'])
        for fault in ('duplicate', 'missing', 'invalid', 'actor'):
            changed = copy.deepcopy(state)
            if fault == 'duplicate':
                changed['client']['cells'].append(changed['client']['cells'][0])
            elif fault == 'missing':
                changed['client']['cells'].pop()
            elif fault == 'invalid':
                changed['client']['valid'] = False
            else:
                changed['client']['cells'][0]['actor'] = True
            with self.subTest(fault=fault):
                self.assertFalse(controls.capture_native_gate(state, changed, self.plan,
                                 self.plan['controls']['supported_positive']['cells'])['declared_context_state_passed'])

    def test_background_residue_refuses_shell_removal_and_restored_claim(self):
        harness = FaultHarness(self.plan, self.output)
        harness.residual = True
        report = {}
        with self.assertRaisesRegex(RuntimeError, 'residue; shell removal refused'):
            controls.cleanup_containment(harness, self.plan, report)
        self.assertFalse(report['contained_cleanup']['restored'])
        self.assertTrue(report['contained_cleanup']['containment_retained'])
        for event in harness.events:
            if event[0] == 'clear':
                self.assertFalse(event[1] & set(self.plan['shell']))
        self.assertFalse(any(event[0] == 'delete_marker' for event in harness.events))
        self.assertTrue(any(event[0] == 'restore_player' for event in harness.events))

    def test_uncertain_cleanup_snapshot_retains_shell(self):
        harness = FaultHarness(self.plan, self.output)
        harness.invalid_snapshot = True
        report = {}
        with self.assertRaises(RuntimeError):
            controls.cleanup_containment(harness, self.plan, report)
        self.assertFalse(report['contained_cleanup']['restored'])
        self.assertTrue(report['contained_cleanup']['containment_retained'])

    def test_cleanup_verifies_empty_nonshell_twice_before_removing_walls(self):
        harness = FaultHarness(self.plan, self.output)
        harness.write(self.plan['controls']['liquid_only']['cells'])
        report = {}
        restored = controls.cleanup_containment(harness, self.plan, report)
        self.assertTrue(restored['restored'])
        events = [event[0] for event in harness.events]
        clears = [index for index, event in enumerate(harness.events) if event[0] == 'clear']
        self.assertEqual(2, len(clears))
        self.assertEqual(2, events[clears[0] + 1:clears[1]].count('snapshot'))
        self.assertEqual(set(self.plan['shell']), harness.events[clears[1]][1])
        self.assertGreater(events.index('restore_player'), clears[1])
        self.assertTrue(controls.matches(snapshot(harness.state), [], self.plan['reserved']))

    def test_png_gate_rejects_blank_wrong_owner_stale_fingerprint_and_changed_viewport(self):
        harness = FaultHarness(self.plan, self.output)
        path = self.output.with_suffix('.png')
        record = png_record(path, harness.session)
        self.assertTrue(controls.validate_png(record, harness.session)['reliable'])
        for key, value in (('owner', 'foreign'), ('backend', 'win32-printwindow'),
                           ('reliable', False), ('background_safe', False), ('sha256', 'changed')):
            changed = copy.deepcopy(record)
            changed['capture'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                controls.validate_png(changed, harness.session)
        changed = copy.deepcopy(record)
        changed['capture']['frame']['frame_qpc_100ns'] = 99
        with self.assertRaisesRegex(ValueError, 'not fresh'):
            controls.validate_png(changed, harness.session)
        with self.assertRaisesRegex(ValueError, 'viewport changed'):
            controls.validate_png(record, harness.session, (81, 60))
        blank = png_record(path, harness.session, blank=True)
        with self.assertRaisesRegex(ValueError, 'blank'):
            controls.validate_png(blank, harness.session)

    def test_frozen_viewport_rejects_fov_change_without_pixel_or_pose_fitting(self):
        record = {'camera_before': copy.deepcopy(POSE['stable']), 'camera_after': copy.deepcopy(POSE['stable'])}
        self.assertTrue(controls.fixed_viewport(record, POSE)['passed'])
        for side in ('camera_before', 'camera_after'):
            for key, value in (('screen', (160, 120)), ('fov', 71.)):
                changed = copy.deepcopy(record)
                changed[side][key] = value
                with self.subTest(side=side, key=key), self.assertRaisesRegex(ValueError, 'FOV changed'):
                    controls.fixed_viewport(changed, POSE)

    def test_real_v1_camera_schema_requires_actual_fov_and_never_fills_a_default(self):
        native = {'position': [15.5, 126.5, 13.5],
                  'rotation': [24.937969207763672, 144.46231079101562, -1.3652624147653114e-05],
                  'screen': [499., 277.]}
        record = {'camera_before': copy.deepcopy(native), 'camera_after': copy.deepcopy(native)}
        pose = {'stable': copy.deepcopy(native)}
        with self.assertRaisesRegex(ValueError, 'actual Camera.GetFov'):
            controls.fixed_viewport(record, pose)
        for item in (record['camera_before'], record['camera_after'], pose['stable']):
            item['fov'] = 70.
        self.assertTrue(controls.fixed_viewport(record, pose)['passed'])
        for side in ('camera_before', 'camera_after'):
            changed = copy.deepcopy(record)
            del changed[side]['fov']
            with self.subTest(side=side), self.assertRaisesRegex(ValueError, 'actual Camera.GetFov'):
                controls.fixed_viewport(changed, pose)
        for value in (float('nan'), float('inf'), None, True, 0., 180.):
            changed = copy.deepcopy(record)
            changed['camera_after']['fov'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'observation is invalid'):
                controls.fixed_viewport(changed, pose)

    def test_shared_native_camera_state_reports_engine_fov_and_rejects_absent_api(self):
        path = ROOT / 'tools/verify_missing_neighbor_visuals.py'
        module = ast.parse(path.read_text(encoding='utf8'))
        assignment = next(node for node in module.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == 'CAMERA_STATE'
                                  for target in node.targets))
        source = ast.literal_eval(assignment.value)
        camera = SimpleNamespace(GetPosition=lambda: [15.5, 126.5, 13.5],
                                 GetCameraRotation=lambda: [24.937969207763672, 144.46231079101562, 0.],
                                 GetFov=lambda: 63.25)
        factory = SimpleNamespace(CreateCamera=lambda level: camera,
                                  CreateGame=lambda level: SimpleNamespace(GetScreenSize=lambda: [499., 277.]))
        scope = {'b': SimpleNamespace(factory=factory, level='test-level'), 'json': json}
        exec(compile(source, '<real-native-camera-state>', 'exec'), scope)
        observed = json.loads(scope['_result'])
        self.assertEqual(63.25, observed['fov'])
        self.assertEqual([499., 277.], observed['screen'])
        pose = {'stable': observed}
        record = {'camera_before': copy.deepcopy(observed), 'camera_after': copy.deepcopy(observed)}
        self.assertTrue(controls.fixed_viewport(record, pose)['passed'])
        record['camera_after']['fov'] = 64.25
        with self.assertRaisesRegex(ValueError, 'FOV changed'):
            controls.fixed_viewport(record, pose)
        del camera.GetFov
        with self.assertRaisesRegex(AssertionError, 'Camera.GetFov'):
            exec(compile(source, '<real-native-camera-state>', 'exec'), scope)

    def test_support_pixels_cannot_satisfy_either_independent_liquid_signal(self):
        frames = {control: Image.new('RGB', (80, 60)) for control in controls.CONTROLS}
        support_box, liquid_box = (5, 35, 50, 50), (15, 5, 40, 25)
        for control in ('supported_positive', 'supported_negative'):
            ImageDraw.Draw(frames[control]).rectangle(support_box, fill=(180, 180, 180))
        paths = {}
        for control, frame in frames.items():
            paths[control] = self.output.with_name(control + '.png')
            frame.save(paths[control])
        liquid = Image.new('L', (80, 60))
        support = Image.new('L', (80, 60))
        ImageDraw.Draw(liquid).rectangle(liquid_box, fill=255)
        ImageDraw.Draw(support).rectangle(support_box, fill=255)
        result, signals = controls.positive_pixel_controls(paths, liquid, support, 16, 80)
        self.assertTrue(result['support_only_vs_empty']['valid_positive_signal'])
        self.assertFalse(result['liquid_only_vs_empty']['valid_positive_signal'])
        self.assertFalse(result['supported_vs_support_only']['valid_positive_signal'])
        self.assertFalse(result['independent_liquid_signals_passed'])
        for control in ('supported_positive', 'liquid_only'):
            ImageDraw.Draw(frames[control]).rectangle(liquid_box, fill=(10, 70, 220))
            frames[control].save(paths[control])
        result, signals = controls.positive_pixel_controls(paths, liquid, support, 16, 80)
        self.assertTrue(result['independent_liquid_signals_passed'])
        self.assertFalse(result['support_pixels_can_satisfy_gate'])
        self.assertFalse(result['native_geometry_accepted'])
        self.assertFalse(result['public_controls_eligible'])
        frames['liquid_only'] = frames['empty'].copy()
        frames['liquid_only'].save(paths['liquid_only'])
        result, signals = controls.positive_pixel_controls(paths, liquid, support, 16, 80)
        self.assertTrue(result['supported_vs_support_only']['valid_positive_signal'])
        self.assertFalse(result['independent_liquid_signals_passed'])

    def test_native_snippets_compile_and_cleanup_writes_both_layers_even_for_air_reads(self):
        plan = self.plan
        sources = [controls.snapshot_code(plan['reserved']), controls.snapshot_code(plan['reserved'], True),
                   controls.server_code(controls.RESERVE % (controls.wire(plan), 'token')),
                   controls.server_code(controls.WRITE_SHELL % 'token'),
                   controls.server_code(controls.WRITE_CONTROL % ('token', controls.wire(plan['controls']['liquid_only']['cells']))),
                   controls.server_code(controls.CLEAR_POSITIONS % ('token', controls.wire(plan['cavity']))),
                   controls.server_code(controls.RESTORE_PLAYER % 'token'),
                   controls.CAMERA % ((8.5, 90.5, -2.5), controls.VISUAL_CASE['camera']['world_offset'])]
        for source in sources:
            compile(source, '<native-liquid-controls>', 'exec')
        self.assertIn('adapter.write(tuple(pos),AIR)', sources[5])
        self.assertNotIn('adapter.read(pos)!=AIR', sources[5])
        self.assertNotIn('ForbidLiquidFlow', ''.join(sources))
        self.assertNotIn('SetLiquidBlock', ''.join(sources))

    def test_actual_server_snippet_reserves_before_shell_and_rejects_raw_background_water(self):
        native = NativeScriptWorld(self.plan)
        residue = self.plan['reserved'][0]
        native.state[residue] = (AIR, ('minecraft:water', 0), False)
        result = native.run(controls.server_code(controls.RESERVE % (controls.wire(self.plan), 'token')))
        self.assertFalse(result['reserved'])
        self.assertTrue(result['before']['raw_palette'])
        self.assertFalse(hasattr(native.server_sys, '_neighbor_world_saved'))
        self.assertFalse(native.writes)
        native.state[residue] = (AIR, AIR, False)
        result = native.run(controls.server_code(controls.RESERVE % (controls.wire(self.plan), 'token')))
        self.assertTrue(result['reserved'])
        self.assertFalse(native.writes)
        self.assertTrue(hasattr(native.server_sys, '_neighbor_world_saved'))

    def test_actual_server_shell_gate_blocks_seed_after_one_failed_wall_write(self):
        native = NativeScriptWorld(self.plan)
        native.run(controls.server_code(controls.RESERVE % (controls.wire(self.plan), 'token')))
        native.failed_write = self.plan['shell'][0]
        result = native.run(controls.server_code(controls.WRITE_SHELL % 'token'))
        self.assertFalse(result['verified'])
        liquid_writes = controls.server_code(controls.WRITE_CONTROL %
                                            ('token', controls.wire(self.plan['controls']['liquid_only']['cells'])))
        with self.assertRaisesRegex(AssertionError, 'Shell gate failed'):
            native.run(liquid_writes)
        self.assertEqual((AIR, AIR, False), native.state[self.plan['cell_origin']])
        self.assertFalse(any(cell.foreground(value)[0] == 'minecraft:water' for pos, value in native.writes))

    def test_actual_server_snippet_clears_entire_inner_cavity_and_extra_layers(self):
        native = NativeScriptWorld(self.plan)
        native.run(controls.server_code(controls.RESERVE % (controls.wire(self.plan), 'token')))
        native.run(controls.server_code(controls.WRITE_SHELL % 'token'))
        native.run(controls.server_code(controls.WRITE_CONTROL %
                                       ('token', controls.wire(self.plan['controls']['liquid_only']['cells']))))
        native.state[self.plan['cavity'][0]] = (AIR, ('minecraft:flowing_water', 8), False)
        native.state[self.plan['cavity'][2]] = (('minecraft:water', 0), ('minecraft:water', 0), False)
        result = native.run(controls.server_code(controls.CLEAR_POSITIONS % ('token', controls.wire(self.plan['cavity']))))
        self.assertTrue(controls.matches(result['after'], [], self.plan['cavity']))
        self.assertEqual(set(self.plan['cavity']), {tuple(item['pos']) for item in result['writes']})
        self.assertTrue(all(native.state[pos] == (tuple(self.plan['shell_value']), AIR, False) for pos in self.plan['shell']))


if __name__ == '__main__':
    unittest.main()

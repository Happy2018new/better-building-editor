"""Offline faults for bed framing; synthetic samples are not live acceptance."""
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
import verify_entity_appearance_visuals as tool
from tests.test_sign_capture_state import Check as EditorCheck

SESSION = 'owned-instance/session.json'
CALIBRATION = {'completed': True, 'passed': True, 'session_file': SESSION,
               'runtime_minecraft_version': 'test-version', 'reported_fov': 70.,
               'screen_aspect': 1., 'vertical_fov': 70.}


def sample(boxes):
    frame = Image.new('RGB', (160, 120))
    mask = Image.new('L', frame.size)
    for box in boxes:
        ImageDraw.Draw(frame).rectangle(box, fill=(55, 135, 205))
        ImageDraw.Draw(mask).rectangle(box, fill=255)
    return frame, mask


class RuntimeCheck:
    def __init__(self):
        self.namespace = {'json': json, 's': SimpleNamespace(origin=(100, 200, 300)),
                          'b': SimpleNamespace(projection_mesh=(1, 'mesh', (100, 200, 300))),
                          'api': SimpleNamespace(GetRotFromDir=lambda direction: (10., 20.))}

    def run(self, code):
        exec(code, self.namespace)
        value = self.namespace['_result']
        return json.loads(value) if isinstance(value, str) else value


class BedDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'MCDEV_SESSION_FILE': SESSION})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.roi = Image.new('L', (160, 120))
        ImageDraw.Draw(self.roi).rectangle((10, 0, 110, 45), fill=255)

    def compare(self, reference_boxes, actual_boxes):
        reference, reference_mask = sample(reference_boxes)
        actual, actual_mask = sample(actual_boxes)
        return tool.bed_comparison(reference, reference_mask, actual, actual_mask, self.roi, self.roi)

    def test_matching_source_above_old_central_crop_is_compared_in_full(self):
        result = self.compare([(20, 5, 99, 24)], [(20, 5, 99, 24)])
        self.assertTrue(result['passed'])
        self.assertEqual(1600, result['actual_pixels'])
        self.assertEqual(1600, result['source_presence']['actual_pixels'])

    def test_missing_bed_is_rejected(self):
        result = self.compare([(20, 5, 99, 24)], [])
        self.assertFalse(result['passed'])
        self.assertEqual(0, result['source_presence']['actual_pixels'])

    def test_shifted_bed_is_rejected(self):
        result = self.compare([(20, 5, 99, 24)], [(20, 65, 99, 84)])
        self.assertFalse(result['passed'])
        self.assertEqual(0, result['recall'])

    def test_matching_geometry_outside_fixed_source_roi_cannot_pass(self):
        result = self.compare([(20, 65, 99, 84)], [(20, 65, 99, 84)])
        self.assertEqual(1., result['recall'])
        self.assertEqual(1., result['precision'])
        self.assertFalse(result['source_presence']['passed'])
        self.assertFalse(result['passed'])

    def test_extra_geometry_outside_source_roi_remains_in_precision(self):
        result = self.compare([(20, 5, 99, 24)], [(20, 5, 99, 24), (20, 65, 99, 104)])
        self.assertTrue(result['source_presence']['passed'])
        self.assertEqual(4800, result['actual_pixels'])
        self.assertLess(result['precision'], .85)
        self.assertFalse(result['passed'])

    def test_missing_unpassed_or_other_instance_calibration_is_rejected(self):
        for calibration in (None, dict(CALIBRATION, passed=False),
                            dict(CALIBRATION, session_file='other-instance/session.json')):
            with self.subTest(calibration=calibration), self.assertRaises(AssertionError):
                tool.require_bed_calibration(calibration)

    def test_calibration_must_match_actual_runtime_fov_version_and_aspect(self):
        runtime = {'version': 'test-version', 'fov': 70., 'screen': (100, 100)}
        tool.require_bed_calibration(CALIBRATION, runtime)
        for key, wrong in (('version', 'other-version'), ('fov', 80.), ('screen', (200, 100))):
            with self.subTest(key=key), self.assertRaises(AssertionError):
                tool.require_bed_calibration(CALIBRATION, dict(runtime, **{key: wrong}))

    def test_windows_session_slashes_and_case_do_not_reject_same_instance(self):
        session = str((ROOT / 'offline-instance/session.json').resolve())
        calibration = dict(CALIBRATION, session_file=session.replace('\\', '/'))
        for equivalent in (session, session.swapcase(), session.replace('\\', '/')):
            with self.subTest(path=equivalent), patch.dict(os.environ, MCDEV_SESSION_FILE=equivalent):
                tool.require_bed_calibration(calibration)
        with patch.dict(os.environ, MCDEV_SESSION_FILE=str(ROOT / 'another-instance/session.json')):
            with self.assertRaisesRegex(AssertionError, 'another instance'):
                tool.require_bed_calibration(calibration)

    def test_existing_roi_helper_uses_canonical_same_instance_identity(self):
        check = RuntimeCheck()
        check.namespace.update(b=SimpleNamespace(level=1, factory=SimpleNamespace(
            CreateCamera=lambda level: SimpleNamespace(GetFov=lambda: 70.),
            CreateGame=lambda level: SimpleNamespace(GetScreenSize=lambda: (100, 100)))),
            api=SimpleNamespace(GetMinecraftVersion=lambda: 'test-version'))
        session = str((ROOT / 'offline-instance/session.json').resolve())
        calibration = dict(CALIBRATION, session_file=session.replace('\\', '/'))
        pose = {'position': (.5, .5, -5.), 'target': (.5, .5, .5), 'rotation': (0., 0., 0.)}
        with patch.dict(os.environ, MCDEV_SESSION_FILE=session.swapcase()):
            roi, evidence = tool.world_cell_roi(check, (0, 0, 100, 100), (100, 100),
                                               (0, 0, 0), pose, calibration)
            self.assertIsNotNone(roi.getbbox())
        with patch.dict(os.environ, MCDEV_SESSION_FILE=str(ROOT / 'another-instance/session.json')):
            with self.assertRaisesRegex(AssertionError, 'another instance'):
                tool.world_cell_roi(check, (0, 0, 100, 100), (100, 100), (0, 0, 0), pose, calibration)

    def test_public_bed_source_stays_complete_when_fresh_observation_loses_head(self):
        from modern_projection.projection.model import Document
        from modern_projection.projection.cell import foreground
        for identity in ('bed_silver', 'bed_light_blue'):
            with self.subTest(identity=identity):
                row = {'case': identity, 'pos': (100, 100, 100), 'cells': [(100, 100, 100)]}
                session = SimpleNamespace(editor=SimpleNamespace(document=Document((8, 8, 8))),
                    camera_pivot=('unchanged',), camera_view=lambda *pose: None, emit=lambda: None)
                session._loaded = lambda doc: setattr(session, 'editor', SimpleNamespace(document=doc))
                namespace = {'s': session, 'sys': SimpleNamespace(_p0_entity_appearance_entities=[row],
                    _blueprint_qa_nonce=0), 'json': json}
                exec(tool.LOAD % (identity, 'synthetic'), namespace)
                loaded = json.loads(namespace['_result'])
                self.assertEqual(2, len(loaded['public_source']['cells']))
                self.assertEqual(2, len(session.editor.document.blocks))
                self.assertEqual(('unchanged',), session.camera_pivot)
                local = tool.source_cells_at(loaded['public_source'], (3, 3, 3))
                self.assertEqual({tuple(cell['foreground']) for cell in loaded['public_source']['cells']},
                                 {foreground(session.editor.document.get(point)) for point in local})

    def test_fixed_source_mapping_keeps_both_cells_and_relative_orientation(self):
        source = {'target': (9, 1, 19), 'cells': [{'pos': (9, 1, 19)}, {'pos': (9, 1, 20)}]}
        self.assertEqual([(3, 3, 3), (3, 3, 4)], tool.source_cells_at(source, (3, 3, 3)))

    def test_source_roi_unites_complete_cells_with_verified_existing_projection(self):
        camera = SimpleNamespace(GetFov=lambda: 70.)
        check = RuntimeCheck()
        check.namespace.update(b=SimpleNamespace(level=1, factory=SimpleNamespace(
            CreateCamera=lambda level: camera,
            CreateGame=lambda level: SimpleNamespace(GetScreenSize=lambda: (100, 100)))),
            api=SimpleNamespace(GetMinecraftVersion=lambda: 'test-version'))
        pose = {'position': (.5, .5, -5.), 'target': (.5, .5, .5), 'rotation': (0., 0., 0.)}
        cells = [(0, 0, 0), (1, 0, 0)]
        roi, evidence = tool.bed_world_roi(check, (100, 100), cells, pose, CALIBRATION)
        self.assertEqual(cells, evidence['cells'])
        self.assertEqual(2, len(evidence['cell_projection']))
        self.assertTrue(all(row['method'] == 'native-cube calibrated perspective projection'
                            for row in evidence['cell_projection']))
        first_bounds = evidence['cell_projection'][0]['bounds']
        self.assertNotEqual(roi.getbbox(), first_bounds)
        with self.assertRaisesRegex(AssertionError, 'requires a completed'):
            tool.bed_world_roi(check, (100, 100), cells, pose, None)

    def test_source_cells_outside_camera_cannot_be_dropped_from_roi(self):
        check = Mock()
        check.run.return_value = {'version': 'test-version', 'fov': 70., 'screen': (100, 100)}
        with patch.object(tool, 'world_cell_roi', side_effect=AssertionError('Plant cell lies outside the screen')):
            with self.assertRaisesRegex(AssertionError, 'outside the screen'):
                tool.bed_world_roi(check, (100, 100), [(0, 0, 0), (1, 0, 0)], {}, CALIBRATION)

    def test_noop_support_write_uses_readback_and_rejects_failed_material_change(self):
        for material in ('minecraft:stone', 'minecraft:magenta_concrete'):
            with self.subTest(material=material):
                support = (100, 99, 100)
                blocks = {support: {'name': 'minecraft:stone', 'aux': 0}}
                position = SimpleNamespace(point=(0.5, 113., 0.5))
                position.GetFootPos = lambda: position.point
                position.SetFootPos = lambda point: setattr(position, 'point', point) or True
                def write(point, value, *unused):
                    if point == support:
                        return False
                    blocks[point] = value
                    return True
                info = SimpleNamespace(GetBlockNew=lambda point, dimension: blocks.get(
                    point, {'name': 'minecraft:air', 'aux': 0}), SetBlockNew=write)
                api = ModuleType('mod.server.extraServerApi')
                api.GetEngineCompFactory = lambda: SimpleNamespace(
                    CreatePos=lambda player: position, CreateBlockInfo=lambda player: info)
                server = ModuleType('mod.server')
                server.extraServerApi = api
                mod = ModuleType('mod')
                mod.server = server
                saved = {'player': 'player', 'dimension': 0, 'reserved': []}
                captured = []
                def execute(client, code):
                    namespace = {}
                    exec(code, namespace)
                    value = json.loads(namespace['_result'])
                    captured.append(value)
                    return value
                check = SimpleNamespace(client=object(), run=Mock(side_effect=[True, RuntimeError('setup captured')]))
                row = {'pos': (100, 100, 100), 'support': support}
                with patch.dict(sys.modules, {'mod': mod, 'mod.server': server,
                                             'mod.server.extraServerApi': api}), \
                     patch.object(sys, '_p0_entity_appearances', saved, create=True), \
                     patch.object(tool, 'execute', side_effect=execute):
                    if material == 'minecraft:stone':
                        with self.assertRaisesRegex(RuntimeError, 'setup captured'):
                            tool.native_capture(check, row, (-2., -.8, -3.), material)
                        self.assertFalse(captured[0]['support_write'])
                        self.assertEqual({'name': material, 'aux': 0}, captured[0]['support_readback'])
                    else:
                        with self.assertRaises(AssertionError):
                            tool.native_capture(check, row, (-2., -.8, -3.), material)
                        self.assertEqual([], captured)

    def test_wrong_camera_before_capture_is_rejected_even_after_settle_witness(self):
        binding = {'anchor': (3, 3, 3), 'offset': (-2., -.8, -3.), 'projection': True,
                   'cells': [(3, 3, 3), (3, 3, 4)], 'calibration': CALIBRATION}
        with patch.object(tool, 'wait_camera_pose', return_value={}), \
             patch.object(tool, 'camera_read', return_value={'position': (0, 0, 0), 'rotation': (0, 0, 0)}), \
             patch.object(tool, 'bed_world_roi') as roi, \
             patch.object(tool, 'pixels') as capture:
            with self.assertRaisesRegex(AssertionError, 'declared pose'):
                tool.capture_bound_world(RuntimeCheck(), 'bed', binding, capture)
            capture.assert_not_called()
            roi.assert_not_called()

    def test_camera_motion_during_capture_or_roi_is_rejected(self):
        binding = {'anchor': (3, 3, 3), 'offset': (-2., -.8, -3.), 'projection': True,
                   'cells': [(3, 3, 3), (3, 3, 4)], 'calibration': CALIBRATION}
        correct = {'position': (101.5, 202.7, 300.5), 'rotation': (10., 200., 0.),
                   'source_origin': (100, 200, 300)}
        wrong = dict(correct, position=(101.5, 203.7, 300.5))
        with TemporaryDirectory() as directory:
            for reads in ([correct, wrong], [correct, correct, wrong]):
                with self.subTest(reads=reads), patch.object(tool, 'wait_camera_pose', return_value=correct), \
                     patch.object(tool, 'camera_read', side_effect=reads), \
                     patch.object(tool, 'bed_world_roi', return_value=(self.roi, {})):
                    shot = {'path': str(Path(directory) / 'bed.png'), 'size': self.roi.size}
                    with self.assertRaisesRegex(AssertionError, 'declared pose'):
                        tool.capture_bound_world(RuntimeCheck(), 'bed', binding, lambda: shot)
                    self.assertFalse((Path(directory) / 'bed_source_roi.png').exists())

    def test_bound_capture_projects_all_declared_cells_and_retains_actual_pose(self):
        binding = {'anchor': (3, 3, 3), 'offset': (-2., -.8, -3.), 'projection': True,
                   'cells': [(3, 3, 3), (3, 3, 4)], 'calibration': CALIBRATION}
        actual = {'position': (101.5, 202.7, 300.5), 'rotation': (10., 200., 0.),
                  'source_origin': (100, 200, 300)}
        with TemporaryDirectory() as directory, patch.object(tool, 'wait_camera_pose', return_value=actual), \
             patch.object(tool, 'camera_read', return_value=actual), \
             patch.object(tool, 'bed_world_roi', return_value=(self.roi, {})) as project:
            shot = {'path': str(Path(directory) / 'bed.png'), 'size': self.roi.size}
            result = tool.capture_bound_world(RuntimeCheck(), 'bed', binding, lambda: shot)
            self.assertEqual([[103, 203, 303], [103, 203, 304]], project.call_args.args[2])
            self.assertEqual(actual, result['camera_binding']['before'])
            self.assertEqual(actual, result['camera_binding']['after'])
            self.assertTrue(Path(result['source_roi']['path']).is_file())

    def test_half_cell_origin_offset_uses_actual_mesh_for_camera_and_source_roi(self):
        binding = {'anchor': (3, 3, 3), 'offset': (-2., -.8, -3.), 'projection': True,
                   'cells': [(3, 3, 3), (3, 3, 4)], 'calibration': CALIBRATION}
        check = RuntimeCheck()
        check.namespace['s'].origin = (100.5, 200, 300.5)
        actual = {'position': (101.5, 202.7, 300.5), 'rotation': (10., 200., 0.),
                  'source_origin': (100, 200, 300)}
        with TemporaryDirectory() as directory, patch.object(tool, 'wait_camera_pose', return_value=actual), \
             patch.object(tool, 'camera_read', return_value=actual), \
             patch.object(tool, 'bed_world_roi', return_value=(self.roi, {})) as project:
            shot = {'path': str(Path(directory) / 'bed.png'), 'size': self.roi.size}
            result = tool.capture_bound_world(check, 'bed', binding, lambda: shot)
            self.assertEqual([[103, 203, 303], [103, 203, 304]], project.call_args.args[2])
            self.assertEqual([100.5, 200, 300.5], result['camera_binding']['requested_origin'])
            self.assertEqual([100, 200, 300], result['camera_binding']['origin'])
            self.assertEqual([103.5, 203.5, 303.5], result['camera_binding']['expected']['target'])
        raw_origin_camera = dict(actual, position=(102., 202.7, 301.))
        with patch.object(tool, 'wait_camera_pose', return_value=raw_origin_camera), \
             patch.object(tool, 'camera_read', return_value=raw_origin_camera):
            with self.assertRaisesRegex(AssertionError, 'declared pose'):
                tool.capture_bound_world(check, 'bed', binding, Mock())

    def test_mesh_origin_drift_rejects_capture_even_when_camera_does_not_move(self):
        binding = {'anchor': (3, 3, 3), 'offset': (-2., -.8, -3.), 'projection': True,
                   'cells': [(3, 3, 3), (3, 3, 4)], 'calibration': CALIBRATION}
        actual = {'position': (101.5, 202.7, 300.5), 'rotation': (10., 200., 0.),
                  'source_origin': (100, 200, 300)}
        moved_source = dict(actual, source_origin=(101, 200, 300))
        with patch.object(tool, 'wait_camera_pose', return_value=actual), \
             patch.object(tool, 'camera_read', side_effect=[actual, moved_source]), \
             patch.object(tool, 'bed_world_roi') as roi:
            with self.assertRaisesRegex(AssertionError, 'source origin changed'):
                tool.capture_bound_world(RuntimeCheck(), 'bed', binding, lambda: {'path': 'bed.png'})
            roi.assert_not_called()

    def test_maintained_world_sample_keeps_sign_default_and_enables_mesh_camera_for_bed(self):
        position = SimpleNamespace(point=None, rotation=None)
        camera = SimpleNamespace(DepartCamera=lambda: None, LockModCameraPitch=lambda value: None,
            LockModCameraYaw=lambda value: None,
            SetCameraPos=lambda point: setattr(position, 'point', point) or True,
            SetCameraRotation=lambda rotation: setattr(position, 'rotation', rotation) or True,
            GetPosition=lambda: position.point, GetCameraRotation=lambda: position.rotation)
        session = SimpleNamespace(origin=None)
        bridge = SimpleNamespace(entity=1, level=1, projection_mesh=None,
            player_origin=lambda: (.5, 113., .5), factory=SimpleNamespace(
                CreateCamera=lambda level: camera,
                CreateActorRender=lambda entity: SimpleNamespace(SetNotRenderAtAll=lambda value: True)))
        bridge.project = lambda: setattr(bridge, 'projection_mesh',
            (1, 'mesh', tuple(int(value) for value in session.origin)))
        namespace = {'s': session, 'b': bridge, 'sys': SimpleNamespace(_blueprint_qa_records=[]),
                     'json': json, 'api': SimpleNamespace(GetRotFromDir=lambda direction: (10., 20.))}
        ready = {'error': None, 'active': True, 'ready': True, 'preparing': False,
                 'actors': 1, 'mesh': True, 'scale': 1.}
        def run(code):
            if code == tool.PROJECTION_STATUS:
                return dict(ready)
            exec(code, namespace)
            value = namespace['_result']
            return json.loads(value) if isinstance(value, str) else value
        def wait(label, predicate, current):
            result = current()
            self.assertTrue(predicate(result) or predicate(result))
            return result
        check = SimpleNamespace(run=run, wait=wait, navigation=lambda: {'open': False},
            capture=lambda label: {'path': 'offline.png'}, output=Path('offline/report.json'))
        with patch.object(tool.world_sample.__globals__['time'], 'sleep'), \
             patch.dict(tool.world_sample.__globals__, projection_pixels=lambda *args: {'changed_pixels': 200}):
            default = tool.world_sample(check, 'sign', (3, 3, 3), (-2., -.8, -3.), height_offset=20)
            bed = tool.world_sample(check, 'bed', (3, 3, 3), (-2., -.8, -3.), height_offset=20, mesh_origin=True)
        self.assertEqual([3.5, 130., 3.5], default['pose']['source_origin'])
        self.assertEqual([3, 130, 3], bed['pose']['source_origin'])
        self.assertEqual([7., 133.5, 7.], default['pose']['target'])
        self.assertEqual([6.5, 133.5, 6.5], bed['pose']['target'])

    def test_grid_and_real_overlay_controls_restore_when_editor_capture_fails(self):
        check = EditorCheck(capture_error=True)
        check.session.grid = True
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            tool.capture_bed_editor(check, 'bed', {})
        self.assertTrue(check.session.grid)
        self.assertTrue(check.controls['edge_control'].GetVisible())
        self.assertFalse(check.controls['cursor_control'].GetVisible())


if __name__ == '__main__':
    unittest.main()

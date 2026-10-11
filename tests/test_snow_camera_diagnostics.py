"""Native camera failures retain their exact stage and game traceback."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_snow_plant_visibility import projection_camera_pose, projection_capture


class Camera:
    def __init__(self, failed=None):
        self.failed = failed
        self.calls = []

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name, args))
            if name == self.failed:
                raise IndexError('native camera test failure')
            return True
        return call


class Check:
    def __init__(self, output, failed=None, origin=(5, -37, 5)):
        self.output = output
        self.camera = Camera(failed)
        self.session = SimpleNamespace(origin=origin)
        self.scope = {'json': json, 's': self.session,
                      'api': SimpleNamespace(GetRotFromDir=lambda value: (-2.7, -141.3)),
                      'b': SimpleNamespace(level='level',
                           factory=SimpleNamespace(CreateCamera=lambda level: self.camera))}

    def run(self, code):
        exec(compile(code, '<game-camera-diagnostic>', 'exec'), self.scope)
        value = self.scope['_result']
        return json.loads(value) if isinstance(value, str) else value


class SnowCameraDiagnosticTests(unittest.TestCase):
    def test_success_keeps_camera_math_and_native_call_order(self):
        with tempfile.TemporaryDirectory() as directory:
            check = Check(Path(directory)/'report.json')
            pose = projection_camera_pose(check, 'case', (1, 1, 1), (-2., .15, -2.5))
            self.assertEqual({'target': [6.5, -35.5, 6.5],
                              'position': [4.5, -35.35, 4.],
                              'rotation': [-2.7, 38.69999999999999, 0.]}, pose)
            self.assertEqual(['DepartCamera', 'LockModCameraPitch', 'LockModCameraYaw',
                              'SetCameraPos', 'SetCameraRotation'],
                             [name for name, args in check.camera.calls])
            self.assertFalse(list(Path(directory).glob('*camera_error.json')))

    def test_native_index_error_is_preserved_at_each_operation(self):
        for operation in ('DepartCamera', 'LockModCameraPitch', 'LockModCameraYaw',
                          'SetCameraPos', 'SetCameraRotation'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                check = Check(Path(directory)/'report.json', operation)
                with self.assertRaisesRegex(RuntimeError, 'failed at '+operation):
                    projection_camera_pose(check, 'covered_h2', (1, 1, 1), (-2., .15, -2.5))
                report = json.loads((Path(directory)/'report_covered_h2_camera_error.json').read_text(encoding='utf8'))
                self.assertEqual(operation, report['stage'])
                self.assertEqual('IndexError', report['error_type'])
                self.assertIn('IndexError: native camera test failure', report['traceback'])
                self.assertEqual([6.5, -35.5, 6.5], report['target'])

    def test_invalid_origin_preserves_index_error_before_native_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            check = Check(Path(directory)/'report.json', origin=())
            with self.assertRaisesRegex(RuntimeError, 'failed at target'):
                projection_camera_pose(check, 'case', (1, 1, 1), (-2., .15, -2.5))
            self.assertEqual([], check.camera.calls)
            report = json.loads((Path(directory)/'report_case_camera_error.json').read_text(encoding='utf8'))
            self.assertEqual('IndexError', report['error_type'])

    def test_fixed_lift_moves_projection_focus_and_reference_cell_together(self):
        class SetupComplete(Exception):
            pass

        for lift in (0, 16):
            with self.subTest(lift=lift), tempfile.TemporaryDirectory() as directory:
                check = Check(Path(directory)/'report.json')
                foot = (0, -60, 0)
                check.scope['b'].player_origin = lambda: foot
                check.scope['b'].project = lambda: None
                check.scope['sys'] = SimpleNamespace(_blueprint_qa_records=[])
                check.wait = lambda *args: (_ for _ in ()).throw(SetupComplete())
                with self.assertRaises(SetupComplete):
                    projection_capture(check, 'case', (1, 1, 1), (-2., .15, -2.5), fixture_lift_y=lift)
                native_target = (foot[0]+6, foot[1]+8+lift, foot[2]+6)
                self.assertEqual(tuple(value+1.5 for value in check.session.origin),
                                 tuple(value+.5 for value in native_target))


if __name__ == '__main__':
    unittest.main()

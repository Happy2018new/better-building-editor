"""Offline checks for settled-bank ordering, isolation and recovery."""
import ast
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.test_liquid_render import Doll, Model, SkeletonLiquidRenderer, group, POSE
from projection.liquid_transport import with_preview_distance
from candidate import entity_draw_pose
from runtime_engine import SettledPool


class NativeDoll(Doll):
    def RenderEntity(self, params):
        self.calls.append(params)
        return self.submit_ok


class NativeModel(Model):
    def __init__(self):
        super().__init__()
        self.values = {}
        self.bad_readback = False

    def SetExtraUniformValue(self, identity, index, value):
        self.values[identity, index] = value
        return super().SetExtraUniformValue(identity, index, value)

    def GetExtraUniformValue(self, identity, index):
        return (0.,) * 4 if self.bad_readback else self.values[identity, index]


class SettledPoolTests(unittest.TestCase):
    def setUp(self):
        registry = {}
        for index in range(8):
            dolls, model = (NativeDoll(), NativeDoll()), NativeModel()
            renderer = SkeletonLiquidRenderer(dolls, model, lambda slot, visible: None)
            value = with_preview_distance(group(key=index), -4.)
            renderer.update(value, POSE, 0.)
            dolls[1].model_id = index + 1
            for now in (.03, .06, .09):
                renderer.update(value, POSE, now)
            control = SimpleNamespace(GetGlobalPosition=lambda: (1., 2.), GetSize=lambda: (3., 4.))
            registry[index] = {'renderer': renderer, 'dolls': (SimpleNamespace(current=control),) * 2,
                               'geometry': (1, 2), 'clip_offset': (0, 0)}
        self.session = SimpleNamespace(liquid_controls=SimpleNamespace(
            closed=False, pending=False, error=None, registry=registry),
            camera_pose=(35., 25., 4.6), camera_pan=(0., 0.), camera_depth=0., camera_depth_pose=0.)
        self.engine = SettledPool(self.session, entity_draw_pose)
        self.engine.suspend()

    def test_reversible_sequence_keeps_each_original_published_id(self):
        for mode in ('S', 'SE', 'S', 'SE', 'S'):
            rows = self.engine.submit(mode)
            self.assertEqual(8, len(rows))
            self.assertFalse(self.engine.poll_ids()['ready'])
            self.assertTrue(self.engine.poll_ids()['ready'])
            self.assertEqual(list(range(1, 9)), self.engine.last_ids)
            self.assertEqual(self.engine.initial, self.engine.snapshot())
            wet = self.engine.payload()
            hidden = self.engine.payload(True)
            self.assertTrue(all(row['actual_uniforms'][3][3] == 0. for row in hidden))
            self.assertEqual(wet, self.engine.payload())
        self.assertTrue(self.engine.finish()['restored'])
        self.assertFalse(self.session.liquid_controls.closed)

    def test_rejects_alias_in_an_unpublished_bank(self):
        renderer = self.engine.rows[0]['renderer']
        renderer.dolls[0].model_id = 2
        with self.assertRaisesRegex(AssertionError, 'alias'):
            self.engine.snapshot()

    def test_rejects_native_uniform_mismatch(self):
        self.engine.rows[0]['renderer'].model_component.bad_readback = True
        with self.assertRaises(AssertionError):
            self.engine.payload()

    def test_rejects_api_failure(self):
        self.engine.rows[0]['renderer'].dolls[1].submit_ok = False
        with self.assertRaisesRegex(AssertionError, 'rejected'):
            self.engine.submit('SE')

    def test_depth_override_is_per_instance_and_restored(self):
        shared = SkeletonLiquidRenderer.__dict__['_render_pose']
        self.engine.release_for_depth()
        self.assertFalse(self.session.liquid_controls.closed)
        self.assertIs(shared, SkeletonLiquidRenderer.__dict__['_render_pose'])
        self.assertTrue(all('_render_pose' in row['renderer'].__dict__ for row in self.engine.rows))
        self.assertTrue(self.engine.restore_methods()['restored'])
        self.assertTrue(all('_render_pose' not in row['renderer'].__dict__ for row in self.engine.rows))

    def test_failed_depth_return_cannot_finish(self):
        self.session.camera_depth = 1.
        with self.assertRaises(AssertionError):
            self.engine.finish()

    def test_cleanup_attempts_every_owned_group_after_one_api_failure(self):
        for row in self.engine.rows:
            row['renderer'].dolls[1].calls[:] = []
        self.engine.rows[0]['renderer'].dolls[1].submit_ok = False
        result = self.engine.restore_submissions()
        self.assertFalse(result['restored'])
        self.assertEqual(8, len(result['rows']))
        self.assertEqual([1] * 8, [len(row['renderer'].dolls[1].calls) for row in self.engine.rows])

    def test_finish_rejects_changed_geometry(self):
        self.engine.rows[0]['entry']['geometry'] = (9, 9)
        with self.assertRaisesRegex(AssertionError, 'differs'):
            self.engine.finish()

    def test_exact_installation_snippet_executes(self):
        import runtime
        session = self.session
        session.liquid_controls.closed = False
        scope = {'sys': SimpleNamespace(), 's': session}
        code = runtime.INSTALL % ((Path(__file__).parent / 'candidate.py').read_text(),
                                  (Path(__file__).parent / 'runtime_engine.py').read_text())
        exec(compile(code, 'exact-install', 'exec'), scope)
        self.assertTrue(scope['sys']._water_ui_se.suspended)
        self.assertEqual(8, len(scope['_result']['entries']))

    def test_host_only_exposes_run_and_recover(self):
        import runtime
        self.assertEqual(('S', 'SE', 'S', 'SE', 'S'), tuple(mode for _, mode in runtime.PHASES))
        tree = ast.parse(Path(runtime.__file__).read_bytes())
        self.assertFalse(any(isinstance(node, ast.FunctionDef) and node.name == 'launch'
                             for node in ast.walk(tree)))


if __name__ == '__main__':
    unittest.main()

"""Exercise the native probe's generated commands against real application state."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from run_snow_scene_lifecycle_r20 import (BIND_SOURCE, MEMORY_LIBRARY, RESTORE_LIBRARY,
    RESTORE_CAMERA_POSE, RESTORE_CAMERA_PAN, CAMERA_STATE, STEPS, camera_stable, snow_control_checks,
    INSTALL_EMPTY_PLACEHOLDER_GUARD, HIDE_EMPTY_PLACEHOLDER, RESTORE_EMPTY_PLACEHOLDER)
from projection.camera import OrbitCamera
from projection import block_registry as registry
from projection.cell import make_cell
from projection.model import Document
from projection.session import Session
from test_complete_cell_workflows_r11 import WorkflowBridge


class SnowLifecycleProbeR20Tests(unittest.TestCase):
    def placeholder_scope(self, visible=True):
        class Native:
            def __init__(self):
                self.visible, self.writes = visible, []

            def GetVisible(self):
                return self.visible

            def SetVisible(self, value):
                self.writes.append(value)
                self.visible = value

        native = Native()
        mapped = SimpleNamespace(key=None, native_path='/viewport/empty', child_fibers=[])
        empty = SimpleNamespace(key='empty_model', native_path=None, child_fibers=[mapped])
        root = SimpleNamespace(key='root', native_path=None, child_fibers=[empty])
        host = SimpleNamespace(_root_fiber=root, GetBaseUIControl=lambda path: native)
        session = object()
        scope = dict(sys=SimpleNamespace(), s=session, owner=SimpleNamespace(session=session),
                     navigator=SimpleNamespace(top=SimpleNamespace(_host=host)), json=json)
        exec(INSTALL_EMPTY_PLACEHOLDER_GUARD, scope)
        return scope, host, empty, mapped, native

    def test_placeholder_guard_preserves_original_visibility_across_repeated_captures(self):
        for visible in (True, False):
            with self.subTest(original_visible=visible):
                scope, unused_host, unused_empty, unused_mapped, native = self.placeholder_scope(visible)
                exec(HIDE_EMPTY_PLACEHOLDER, scope)
                first = json.loads(scope['_result'])['nodes'][0]
                self.assertEqual(visible, first['original_visible'])
                self.assertFalse(native.visible)
                exec(HIDE_EMPTY_PLACEHOLDER, scope)
                self.assertEqual(visible, json.loads(scope['_result'])['nodes'][0]['original_visible'])
                exec(RESTORE_EMPTY_PLACEHOLDER, scope)
                self.assertEqual(visible, native.visible)
                self.assertEqual('restored', json.loads(scope['_result'])['nodes'][0]['action'])
                self.assertFalse(hasattr(scope['sys'], '_snow_empty_placeholder_guard'))

    def test_placeholder_guard_does_not_restore_a_reused_path_after_unmount(self):
        scope, host, old_empty, mapped, native = self.placeholder_scope()
        exec(HIDE_EMPTY_PLACEHOLDER, scope)
        new_mapped = SimpleNamespace(key=None, native_path=mapped.native_path, child_fibers=[])
        replacement = SimpleNamespace(key='different_ui', native_path=None, child_fibers=[new_mapped])
        host._root_fiber.child_fibers = [replacement]
        native.visible, native.writes = False, []
        exec(RESTORE_EMPTY_PLACEHOLDER, scope)
        self.assertEqual('removed', json.loads(scope['_result'])['nodes'][0]['action'])
        self.assertEqual([], native.writes)
        self.assertFalse(native.visible)

    def test_placeholder_guard_tracks_new_fiber_at_the_same_path_and_refuses_other_host(self):
        scope, host, unused_empty, mapped, native = self.placeholder_scope()
        exec(HIDE_EMPTY_PLACEHOLDER, scope)
        new_mapped = SimpleNamespace(key=None, native_path=mapped.native_path, child_fibers=[])
        new_empty = SimpleNamespace(key='empty_model', native_path=None, child_fibers=[new_mapped])
        host._root_fiber.child_fibers = [new_empty]
        native.visible = True
        exec(HIDE_EMPTY_PLACEHOLDER, scope)
        scope['navigator'].top._host = object()
        with self.assertRaises(AssertionError):
            exec(HIDE_EMPTY_PLACEHOLDER, scope)
        exec(RESTORE_EMPTY_PLACEHOLDER, scope)
        rows = json.loads(scope['_result'])['nodes']
        self.assertEqual(['removed', 'restored'], [row['action'] for row in rows])
        self.assertTrue(native.visible)

    def test_placeholder_hide_failure_keeps_original_visibility_available_for_cleanup(self):
        scope, unused_host, unused_empty, unused_mapped, native = self.placeholder_scope()
        original_set = native.SetVisible
        native.SetVisible = lambda value: None
        with self.assertRaisesRegex(AssertionError, 'did not hide'):
            exec(HIDE_EMPTY_PLACEHOLDER, scope)
        native.SetVisible = original_set
        exec(RESTORE_EMPTY_PLACEHOLDER, scope)
        self.assertTrue(native.visible)
        self.assertTrue(json.loads(scope['_result'])['restored'])

    def test_failed_native_capture_retains_actual_source_camera_and_placeholder_receipt(self):
        import run_snow_scene_lifecycle_r20 as probe
        from verify_debug_blueprints import STATUS
        module = ast.parse(Path(probe.__file__).read_text(encoding='utf8'))
        main = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        guarded = next(node for node in main.body if isinstance(node, ast.ClassDef) and node.name == 'GuardedCheck')
        snapshots = []

        class BaseCheck:
            def run(self, code):
                return {BIND_SOURCE: {'cells': [[[1, 1, 1], 'snow']]},
                        STATUS: {'current_source': True}, CAMERA_STATE: {'pan': [0., -.12]},
                        HIDE_EMPTY_PLACEHOLDER: {'matched': 1, 'nodes': [{'before': True, 'after': False}]}}[code]

            def capture(self, label, tree):
                raise RuntimeError('injected native capture failure')

        report = {'resource_checks': [], 'capture_observations': []}
        scope = dict(SignCheck=BaseCheck, args=SimpleNamespace(minimum_commit_gib=6., max_handles=215000,
            output=Path('unused.json')), report=report, started=time.monotonic(), time=time,
            session={'game_pid': 123, 'session_file': 'fake', 'owner': 'fake'},
            assertion_dialogs=lambda: [], transport=SimpleNamespace(metrics=lambda *args: {'handles': 100}),
            commit_at_boundary=lambda: {'commit_available_bytes': 8 * 1024 ** 3},
            write_json=lambda path, value: snapshots.append(copy.deepcopy(value)),
            BIND_SOURCE=BIND_SOURCE, CAMERA_STATE=CAMERA_STATE, STATUS=STATUS,
            HIDE_EMPTY_PLACEHOLDER=HIDE_EMPTY_PLACEHOLDER)
        exec(compile(ast.Module(body=[guarded], type_ignores=[]), probe.__file__, 'exec'), scope)
        with self.assertRaisesRegex(RuntimeError, 'injected native capture failure'):
            scope['GuardedCheck']().capture('control_snow')
        observed = snapshots[-1]['capture_observations'][-1]
        self.assertEqual('before_native_capture', observed['phase'])
        self.assertEqual({'pan': [0., -.12]}, observed['camera_state'])
        self.assertTrue(observed['state']['current_source'])
        self.assertEqual(1, observed['empty_placeholder']['matched'])
        self.assertEqual(1, len(observed['source']['cells']))

    def test_library_camera_restore_does_not_rebase_unsettled_pan_during_zoom(self):
        path = ROOT / 'behavior_pack/modern_projection/projection/scene.py'
        module = ast.parse(path.read_text(encoding='utf8'))
        scene = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'Scene')
        aim = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'aim')
        tick = next(node for node in scene.body if isinstance(node, ast.FunctionDef) and node.name == 'tick')
        start = next(index for index, node in enumerate(tick.body) if isinstance(node, ast.If)
                     and ast.unparse(node.test) == 'reset_revision.current != session.camera_reset_revision')
        stop = next(index for index, node in enumerate(tick.body) if isinstance(node, ast.If)
                    and ast.unparse(node.test).startswith('wheel_time.current is not None'))
        frame = compile(ast.Module(body=copy.deepcopy(tick.body[start:stop]), type_ignores=[]), str(path), 'exec')
        effect = compile(ast.Module(body=[copy.deepcopy(aim)], type_ignores=[]), str(path), 'exec')
        for frame_before_effect in (False, True):
            with self.subTest(frame_before_effect=frame_before_effect):
                bridge = WorkflowBridge()
                session = Session(bridge)
                session._loaded(Document((3, 3, 3)))
                camera = OrbitCamera()
                scope = dict(s=session, session=session, camera=camera, width=1070., height=491.,
                    Theme=SimpleNamespace(scale=1., motion=True), dt=.005,
                    reset_revision=SimpleNamespace(current=session.camera_reset_revision),
                    drag=SimpleNamespace(current=None), wheel_time=SimpleNamespace(current=None),
                    placed_pointer=SimpleNamespace(current=None), hover_preview=SimpleNamespace(current=None),
                    outline=SimpleNamespace(invalidate=lambda: None),
                    sys=SimpleNamespace(_snow_lifecycle_saved={'camera': ((35., 10., 2.8), (1.5, 1.5, 1.5), (0., -.12))}))
                exec(effect, scope)
                exec(RESTORE_CAMERA_POSE, scope)
                if frame_before_effect:
                    exec(frame, scope)
                scope['aim']()
                for unused in range(240):
                    exec(frame, scope)
                for actual, expected in zip(session.camera_pose, (35., 10., 2.8)):
                    self.assertAlmostEqual(expected, actual, places=3)
                self.assertEqual((0., 0.), session.camera_pan)
                exec(RESTORE_CAMERA_PAN, scope)
                for unused in range(240):
                    exec(frame, scope)
                self.assertEqual((0., -.12), session.camera_pan)
                self.assertEqual((0., -.12), camera.pan)
                if frame_before_effect:
                    session.reset_camera(False)
                    camera.reset()
                    scope['reset_revision'].current = session.camera_reset_revision
                    exec(RESTORE_CAMERA_PAN, scope)
                    exec(RESTORE_CAMERA_POSE, scope)
                    exec(frame, scope)
                    scope['aim']()
                    for unused in range(240):
                        exec(frame, scope)
                    vertical_error = (camera.pan[1] + .12) * 491.
                    self.assertGreater(vertical_error, 40.)
                    self.assertLess(vertical_error, 50.)
                    self.assertNotEqual((0., -.12), session.camera_pan)

    def test_camera_observation_reads_owned_scene_instead_of_session_targets(self):
        session = Session(WorkflowBridge())
        camera = OrbitCamera(35., 10., 2.8)
        session.camera_pose = camera.target
        session.camera_yaw, session.camera_pitch, session.zoom = camera.target
        session.camera_pan = (0., -.12)
        theme = SimpleNamespace(scale=1.5)
        width, height = 800., 400.
        revision = SimpleNamespace(current=session.camera_reset_revision)

        def tick(unused):
            return camera, session, theme, width, height, revision

        # Keep the same closure names and module guard used by the actual Scene.
        source = '''def make_tick(camera,session,width,height,reset_revision):
 def tick(unused):return camera,session,Theme,width,height,reset_revision
 return tick
'''
        scope = {'Theme': theme}
        exec(source, scope)
        callback = scope['make_tick'](camera, session, width, height, revision)
        callback.__module__ = 'modern_projection.projection.scene'
        host = SimpleNamespace(_animation_frames={1: {'callback': tick}, 2: {'callback': callback}})
        scope.update(s=session, b=SimpleNamespace(model_layouts={}), json=json)
        with patch.dict(sys.modules, {'modern_projection.pyreact.host': SimpleNamespace(_ACTIVE_HOST=[host])}):
            exec(CAMERA_STATE, scope)
            observed = json.loads(scope['_result'])
            self.assertEqual([0., 0.], observed['pan'])
            self.assertEqual([0., -.12], observed['session']['pan'])
            self.assertEqual([1200., 600.], observed['viewport'])
            self.assertFalse(camera_stable(observed, (35., 10., 2.8), (0., -.12)))
            self.assertTrue(camera_stable(observed, (35., 10., 2.8)))
            observed['session']['reset_revision'] += 1
            self.assertFalse(camera_stable(observed, (35., 10., 2.8)))
            host._animation_frames[3] = {'callback': callback}
            with self.assertRaises(AssertionError):
                exec(CAMERA_STATE, scope)

    def test_preserved_pixels_reject_toolbar_occlusion_and_stale_or_absent_snow(self):
        from PIL import Image
        from verify_snow_package_r20 import remap
        from verify_snow_plant_visibility import capture_frame

        package = ROOT / 'docs/evidence/snow-product-r20-v1'
        manifest = json.loads((package / 'manifest.json').read_bytes())
        report = remap(json.loads((package / 'matrix/report.json').read_bytes()),
                       manifest['original_to_package'], package)
        blank = next(row['editor'] for row in report['rows'] if row['kind'] == 'blank')
        plant = next(row for row in report['rows'] if row['kind'] == 'plant')
        stale = capture_frame(plant['editor']['path'], plant['editor_crop'], blank['path'])
        for row in report['rows']:
            if row['kind'] != 'snow':
                continue
            with self.subTest(height=row['height']):
                for record in (row['editor'], blank, plant['editor']):
                    self.assertEqual(record['sha256'], hashlib.sha256(Path(record['path']).read_bytes()).hexdigest())
                frame = capture_frame(row['editor']['path'], row['editor_crop'], blank['path'])
                values = (row['editor_crop'], row['camera_state'], (1, 1, 1), row['height'])
                check = snow_control_checks(*values, frame['object'])
                self.assertEqual(row['height'] != 0, check['passed'])
                self.assertFalse(snow_control_checks(*values, stale['object'])['passed'])
                self.assertFalse(snow_control_checks(*values, Image.new('L', frame['object'].size))['passed'])

    def test_generated_steps_use_real_history_and_keep_persistent_library_untouched(self):
        bridge = WorkflowBridge()
        session = Session(bridge)
        focus = (1, 1, 1)
        snow = registry.from_states('minecraft:snow_layer', {'height': 0, 'covered_bit': True})
        covered = make_cell(snow, ('minecraft:blue_orchid', 0))
        session._loaded(Document((3, 3, 3), {focus: covered}, name='snow lifecycle'))
        session.editor.select_box(focus, focus)
        original_library = session.library
        local_sys = SimpleNamespace(_blueprint_qa_nonce=0)
        scope = {'sys': local_sys, 's': session, 'focus': focus,
                 'snow_material': snow, 'Document': Document, 'json': json}
        exec(MEMORY_LIBRARY, scope)
        proxy = session.bridge
        self.assertIsNot(bridge, proxy)
        try:
            for label, unused_expected, code in STEPS:
                with self.subTest(step=label):
                    exec(code, scope)
                    bridge.settle()
                    exec(BIND_SOURCE, scope)
                    source = scope['json'].loads(scope['_result'])
                    self.assertEqual(id(session.editor), source['editor_id'])
                    self.assertEqual(id(session.editor.document), source['document_id'])
                    self.assertEqual(1, source['metadata']['blocks'])
                    self.assertIsNone(bridge.index)
            self.assertEqual(covered, session.editor.document.get(focus))
            self.assertIsNotNone(proxy.data)
        finally:
            exec(RESTORE_LIBRARY, scope)
        self.assertIs(bridge, session.bridge)
        self.assertIs(original_library, session.library)
        self.assertIsNone(bridge.index)
        self.assertFalse(hasattr(local_sys, '_snow_lifecycle_saved'))


if __name__ == '__main__':
    unittest.main()

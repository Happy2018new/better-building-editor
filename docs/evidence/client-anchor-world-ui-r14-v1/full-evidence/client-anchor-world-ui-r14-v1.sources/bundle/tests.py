"""Verify one-binding ownership, fixed evidence and failure cleanup offline."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import execute_frame_item_translation as executor
import probe_client_anchor_world_ui as probe
from test_client_anchor_paper_doll import AnchorFixture
from test_native_item_paper_doll import NativeFixture, RAW, marker_capture


class PairedFixture(AnchorFixture):
    def __init__(self):
        super().__init__()
        self.entries.clear()
        self.nav.top = None
        self.camera = {'position': (20., 66., 20.), 'rotation': (0., 0., 0.),
                       'forward': (0., 0., 1.), 'pitch_lock': False, 'yaw_lock': False, 'motions': {}}
        self.camera_writes, self.block_reads, self.visibility_calls = [], [], []
        self.block_value, self.visible, self.visibility_error = ('minecraft:air', 0), True, None
        self.factory.CreateCamera = lambda level: SimpleNamespace(
            GetPosition=lambda: self.camera['position'], GetCameraRotation=lambda: self.camera['rotation'],
            GetForward=lambda: self.camera['forward'], GetCameraMotions=lambda: self.camera['motions'],
            IsModCameraLockPitch=lambda: self.camera['pitch_lock'], IsModCameraLockYaw=lambda: self.camera['yaw_lock'],
            DepartCamera=lambda: self.camera_writes.append('depart'), SetCameraPos=lambda value: self.camera_writes.append(value))
        self.factory.CreateBlockInfo = lambda level: SimpleNamespace(GetBlock=self.block_read)
        self.root_control.GetVisible = lambda: self.visible
        self.root_control.SetVisible = self.set_visible

    def saved(self):
        return getattr(self.namespace['sys'], probe.ATTRIBUTE)

    def create(self, *args):
        self.created.append(args)
        if self.saved()['create'] != {'state': 'pending', 'attempted': True}:
            raise AssertionError('Creation not journaled')
        if self.creation_error:
            raise self.creation_error
        self.alive = self.creation_value == self.actor
        return self.creation_value

    def destroy(self, actor):
        if not self.saved()['destroy_attempted'] or actor != self.actor:
            raise AssertionError('Only exact actor may be destroyed')
        self.destroyed.append(actor)
        if self.destroy_error:
            raise self.destroy_error
        self.alive = False

    def bind(self, *args):
        row = self.saved()['attachments'][-1]
        if row['state'] != 'pending' or not row['attempted'] or row['id'] is not None:
            raise AssertionError('Binding not journaled')
        return NativeFixture.bind(self, *args)

    def block_read(self, cell):
        self.block_reads.append(cell)
        return self.block_value

    def set_visible(self, visible):
        row = self.saved()['journal'][-1]
        if row['state'] != 'pending' or row['requested'] != visible:
            raise AssertionError('Visibility not journaled')
        self.visibility_calls.append(visible)
        if self.visibility_error:
            raise self.visibility_error
        self.visible = visible

    def run(self, code):
        self.native_calls.append(code)
        return NativeFixture.run(self, code)

    def programs(self):
        return probe.snippets('offline-owned', probe.anchor.base.item_controls(RAW.read_bytes())[0]['plain'])

    def install(self):
        return self.run(self.programs()['install_client.py'])

    def cleanup(self):
        for name in ('remove_client.py', 'pop_client.py', 'destroy_client.py'):
            self.run(self.programs()[name])
        return self.run(self.programs()['verify_client.py'])


class PairedProbeTests(unittest.TestCase):
    def test_position_uses_documented_forward_and_empty_loaded_cells_before_create(self):
        fixture = PairedFixture()
        fixture.camera['forward'] = (0., 0., 5.)
        initial = fixture.install()
        self.assertEqual([20., 66., 23.], initial['position'])
        self.assertEqual(('modern_projection:anchor', (20., 66., 23.), (0., 0.)), fixture.created[0])
        self.assertEqual(27, len(fixture.block_reads))
        self.assertTrue(initial['roi_receipt']['declared_before_capture'])
        self.assertEqual(probe.FIXED_ROI, initial['roi_receipt']['world'])
        self.assertTrue(fixture.cleanup()['restored'])
        self.assertFalse(fixture.camera_writes)

    def test_occupied_or_unknown_cell_prevents_actor_creation_and_keeps_safe_cleanup(self):
        for value in (None, ('minecraft:stone', 0), ('', 0)):
            with self.subTest(value=value):
                fixture = PairedFixture()
                fixture.block_value = value
                with self.assertRaisesRegex(AssertionError, 'verified loaded air'):
                    fixture.install()
                self.assertFalse(fixture.created)
                self.assertFalse(fixture.destroyed)
                self.assertFalse(hasattr(fixture.namespace['sys'], probe.ATTRIBUTE))
                self.assertTrue(fixture.cleanup()['restored'])

    def test_invalid_player_camera_motion_or_existing_page_aborts_before_actor(self):
        for mutate in (lambda f: setattr(f, 'foot', (0., 32768., 0.)),
                       lambda f: f.camera.update(forward=(0., 0., 0.)),
                       lambda f: f.camera.update(position=(float('nan'), 66., 20.)),
                       lambda f: f.camera.update(motions={8: 1}),
                       lambda f: f.entries.append(SimpleNamespace(key='unrelated'))):
            fixture = PairedFixture()
            mutate(fixture)
            with self.assertRaises(AssertionError):
                fixture.install()
            self.assertFalse(fixture.created)
            self.assertFalse(fixture.camera_writes)

    def test_single_plain_binding_is_retained_through_ui_and_world_then_removed_once(self):
        fixture = PairedFixture()
        fixture.install()
        programs = fixture.programs()
        fixture.run(programs['world_empty_client.py'])
        fixture.run(programs['open_ui_client.py'])
        fixture.run(programs['ui_empty_client.py'])
        ui = fixture.run(programs['ui_plain_client.py'])
        world = fixture.run(programs['world_plain_client.py'])
        self.assertEqual(ui['native_item'], world['native_item'])
        self.assertEqual(1, len(fixture.binds))
        self.assertFalse(fixture.visible)
        fixture.run(programs['world_empty_restored_client.py'])
        fixture.run(programs['ui_empty_restored_client.py'])
        self.assertTrue(fixture.visible)
        self.assertTrue(fixture.cleanup()['restored'])
        self.assertEqual([(fixture.actor, 40, '', True)], fixture.removes)
        self.assertEqual(1, fixture.pop_calls)
        self.assertEqual([fixture.actor], fixture.destroyed)

    def test_unknown_create_retained_and_unknown_binding_needs_proven_actor_absence(self):
        fixture = PairedFixture()
        fixture.creation_error = TimeoutError('unknown creation')
        with self.assertRaises(TimeoutError):
            fixture.install()
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertFalse(fixture.destroyed)
        self.assertFalse(fixture.run(fixture.programs()['absent_client.py'])['absent'])
        fixture = PairedFixture()
        fixture.install()
        fixture.run(fixture.programs()['open_ui_client.py'])
        fixture.bind_error = TimeoutError('unknown binding')
        with self.assertRaises(TimeoutError):
            fixture.run(fixture.programs()['ui_plain_client.py'])
        fixture.run(fixture.programs()['remove_client.py'])
        fixture.run(fixture.programs()['pop_client.py'])
        with self.assertRaises(AssertionError):
            fixture.run(fixture.programs()['verify_client.py'])
        fixture.run(fixture.programs()['destroy_client.py'])
        self.assertTrue(fixture.run(fixture.programs()['verify_client.py'])['attachments'][0]['disposed_by_owned_actor_destruction'])

    def run_matrix(self, directory, world=True, ui=False, markers=True, drift=False):
        from PIL import Image, ImageDraw
        fixture = PairedFixture()
        bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
        probe.prepare(RAW, bundle)

        def capture(runtime, path):
            saved = fixture.saved()
            label = saved['control']
            if label.startswith('ui_'):
                status = fixture.run((bundle / 'status_client.py').read_text(encoding='ascii'))
                layout = probe.anchor.layout_readback(fixture.tree(), status, {'actor': fixture.actor, 'size_inputs': fixture.screen_observed})
                record = marker_capture(path, layout, scale=3.9974978978239917,
                    translation=(.12427449291408266, -2.1534588486227904), missing=None if markers else 1)
                with Image.open(path) as source:
                    image = source.convert('RGB')
            else:
                image = Image.new('RGB', tuple(probe.PHYSICAL_SIZE), (100, 100, 100))
                record = {'path': str(path), 'mime': 'image/png', 'size': probe.PHYSICAL_SIZE,
                          'capture': {'path': str(path), 'width': 1994, 'height': 1105, 'frame': {'width': 1994, 'height': 1105}}}
            draw = ImageDraw.Draw(image)
            if label == 'world_plain' and world or label == 'ui_plain' and ui:
                draw.rectangle((900, 430, 970, 500), fill=(15, 180, 145))
            image.save(path)
            payload = path.read_bytes()
            record['sha256'], record['bytes'] = probe.digest(payload), len(payload)
            record['capture'].update(sha256=record['sha256'], bytes=record['bytes'])
            if drift and label == 'world_plain':
                fixture.camera['position'] = (21., 66., 20.)
            return record

        with patch.object(executor.BoundedRuntime, 'capture_adapter', lambda value: None), \
                patch.object(executor.BoundedRuntime, 'capture', capture), patch.object(probe.time, 'sleep', lambda value: None):
            report = probe.execute_probe(bundle, output, fixture.check(), SimpleNamespace(guard=lambda: None), time.monotonic() + 120.)
        return fixture, report

    def test_world_positive_ui_zero_classification_and_exact_cleanup(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory)
            self.assertTrue(report['completed'], report['errors'])
            self.assertTrue(report['restored'], report['cleanup_errors'])
            self.assertEqual(12, sum(len(row['frames']) for row in report['states'].values()))
            score = probe.score_probe(report)
            self.assertEqual('world_positive_ui_zero_on_this_anchor_and_pose', score['classification'])
            self.assertGreaterEqual(score['modes']['world']['stable_plain_pixels'], 80)
            self.assertEqual(0, score['modes']['ui']['stable_plain_pixels'])
            self.assertTrue(score['ui_marker_gate_passed'])
            self.assertEqual(1, len(fixture.binds))
            self.assertFalse(fixture.camera_writes)
            self.assertFalse(score['production_rendering_accepted'])

    def test_both_zero_is_retained_as_unresolved_not_failed_dispatch(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory, world=False)
            self.assertTrue(report['completed'])
            self.assertTrue(report['restored'])
            self.assertEqual('both_zero_cause_unresolved', probe.score_probe(report)['classification'])
            self.assertEqual(1, len(fixture.binds))

    def test_failed_marker_cannot_be_promoted_by_fixed_roi(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory, markers=False)
            self.assertTrue(report['completed'])
            self.assertTrue(report['restored'])
            score = probe.score_probe(report)
            self.assertFalse(score['ui_marker_gate_passed'])
            self.assertEqual('invalid_controls', score['classification'])
            self.assertEqual(12, sum(len(row['frames']) for row in report['states'].values()))

    def test_camera_drift_keeps_original_capture_and_exact_cleanup_without_camera_write(self):
        with TemporaryDirectory() as directory:
            fixture, report = self.run_matrix(directory, drift=True)
            self.assertFalse(report['completed'])
            self.assertFalse(report['restored'])
            self.assertTrue(report['states']['world_plain']['frames'])
            self.assertTrue(Path(report['states']['world_plain']['frames'][0]['capture']['path']).is_file())
            self.assertEqual([fixture.actor], fixture.destroyed)
            self.assertEqual(1, fixture.pop_calls)
            self.assertFalse(fixture.camera_writes)
            self.assertTrue(hasattr(fixture.namespace['sys'], probe.ATTRIBUTE))

    def test_visibility_timeout_still_removes_binding_and_owned_actor(self):
        fixture = PairedFixture()
        fixture.install()
        fixture.run(fixture.programs()['open_ui_client.py'])
        fixture.run(fixture.programs()['ui_plain_client.py'])
        fixture.visibility_error = TimeoutError('unknown visibility')
        with self.assertRaises(TimeoutError):
            fixture.run(fixture.programs()['world_plain_client.py'])
        self.assertEqual('pending', fixture.saved()['journal'][-1]['state'])
        self.assertTrue(fixture.cleanup()['restored'])
        self.assertEqual(1, len(fixture.removes))
        self.assertEqual([fixture.actor], fixture.destroyed)

    def test_roi_tamper_and_binding_id_change_rejected_offline(self):
        with TemporaryDirectory() as directory:
            _, report = self.run_matrix(directory)
            changed = copy.deepcopy(report)
            changed['initial']['roi_receipt']['world'] = [900, 430, 970, 500]
            with self.assertRaisesRegex(ValueError, 'ROI'):
                probe.score_probe(changed)
            changed = copy.deepcopy(report)
            changed['states']['world_plain']['native']['native_item']['id'] += 1
            with self.assertRaisesRegex(ValueError, 'one exact binding'):
                probe.score_probe(changed)

    def test_preflight_preserves_all_original_paths_and_dependency_hashes(self):
        with TemporaryDirectory() as directory:
            bundle, output = Path(directory) / 'bundle', Path(directory) / 'report.json'
            plan = probe.prepare(RAW, bundle)
            probe.verify_bundle(bundle)
            self.assertEqual(probe.FIXED_ROI, plan['fixed_rois']['world'])
            for name in probe.snippets(plan['nonce'], json.loads((bundle / 'plain.json').read_bytes())):
                compile((bundle / name).read_text(encoding='ascii'), name, 'exec')
            shot = probe.anchor.base.capture_path(output, 'ui_empty_restored', 1)
            shot.write_bytes(b'preserved')
            with self.assertRaisesRegex(ValueError, 'Preserve existing paired'):
                probe.preflight(bundle, output)
            self.assertEqual(b'preserved', shot.read_bytes())
            (bundle / 'world_plain_client.py').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'frozen file changed'):
                probe.verify_bundle(bundle)

    def test_persistent_report_failure_does_not_interrupt_cleanup(self):
        original, calls = executor.save_report, []

        def fail_after_dispatch(path, report):
            calls.append(len(calls))
            if len(calls) > 20:
                raise OSError('persistent evidence write failure')
            original(path, report)

        with TemporaryDirectory() as directory, patch.object(executor, 'save_report', fail_after_dispatch):
            fixture, report = self.run_matrix(directory)
            self.assertFalse(report['completed'])
            self.assertTrue(report['cleanup_errors'])
            self.assertEqual([fixture.actor], fixture.destroyed)
            self.assertEqual(1, fixture.pop_calls)
            self.assertFalse(hasattr(fixture.namespace['sys'], probe.ATTRIBUTE))


if __name__ == '__main__':
    unittest.main()

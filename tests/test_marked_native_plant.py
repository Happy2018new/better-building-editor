"""Bitmap probes preserve alpha, stay in the pack and refuse restoration drift."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prepare_marked_native_plant as marker
import verify_marked_native_plant as observer


class MarkedNativePlantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scope = patch.object(marker, 'ROOT', self.root)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.native = self.root / 'native.png'
        image = Image.new('RGBA', (16, 16), (24, 80, 16, 0))
        image.putpixel((4, 5), (255, 0, 0, 128))
        image.putpixel((6, 9), (255, 0, 0, 255))
        image.save(self.native)
        self.plan = self.root / 'plan.json'
        self.plan.write_text(json.dumps({
            'texture_source': {'atlas_path': marker.ATLAS_PATH,
                               'installed_path': str(self.native),
                               'sha256': marker.digest(self.native.read_bytes())},
            'marker_descriptor': {'base_rgb': [128, 128, 128],
                                  'regions_in_order': [{'bounds': [0, 0, 4, 4],
                                                        'rgb': [255, 255, 255]}]}}))
        self.target = self.root / 'resource_pack' / (marker.ATLAS_PATH + '.png')
        self.snapshot = self.root / 'snapshot.json'

    def test_preserves_every_alpha_byte_and_restores_absent_override(self):
        original = self.native.read_bytes()
        row = marker.prepare(self.plan, self.snapshot)
        self.assertEqual(row['native_alpha_sha256'], row['candidate_alpha_sha256'])
        with Image.open(self.native) as native, Image.open(self.target) as probe:
            self.assertEqual(native.getchannel('A').tobytes(), probe.getchannel('A').tobytes())
            self.assertNotEqual(native.getchannel('R').tobytes(), probe.getchannel('R').tobytes())
        marker.validate_marker(self.snapshot, self.plan, 'alpha_marker')
        self.assertTrue(marker.restore(self.snapshot)['restored'])
        self.assertFalse(self.target.exists())
        self.assertEqual(original, self.native.read_bytes())

    def test_restores_existing_override_and_rejects_stage_mismatch(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'original override bytes')
        marker.prepare(self.plan, self.snapshot, opaque=True)
        with self.assertRaisesRegex(ValueError, 'stage differs'):
            marker.validate_marker(self.snapshot, self.plan, 'alpha_marker')
        marker.validate_marker(self.snapshot, self.plan, 'opaque_marker')
        marker.restore(self.snapshot)
        self.assertEqual(b'original override bytes', self.target.read_bytes())

    def test_refuses_target_traversal_before_writes(self):
        plan = json.loads(self.plan.read_bytes())
        plan['texture_source']['atlas_path'] = '../outside'
        self.plan.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, 'target differs'):
            marker.prepare(self.plan, self.snapshot)
        self.assertFalse(self.snapshot.exists())
        self.assertFalse(self.target.exists())

    def test_restore_refuses_candidate_drift(self):
        marker.prepare(self.plan, self.snapshot)
        self.target.write_bytes(b'unrelated edit')
        with self.assertRaisesRegex(ValueError, 'refuse to overwrite'):
            marker.restore(self.snapshot)
        self.assertEqual(b'unrelated edit', self.target.read_bytes())


class NativeMarkerCleanupTests(unittest.TestCase):
    def check_failure(self, existing=False, dirty=False):
        class Client:
            def __init__(self, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class Check:
            def __init__(self, *args):
                pass

            def run(self, code):
                return {'runtime': 'test', 'options': {}} if code == observer.GRAPHICS_STATE else True

        def server(client, code):
            if 'hasattr(sys,' in code:
                return existing
            raise RuntimeError('setup failed after saving fixture')

        def freeze(path):
            path.write_text('{}')
            return observer.record(path)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = root / 'report.json'
            plan = root / 'plan.json'
            plan.write_text(json.dumps({'calibration_coordinates': [[6, 117, 6]]}))
            calibration = root / 'camera.json'
            session_file = root / 'session.json'
            calibration.write_text(json.dumps({'completed': True, 'passed': True,
                                               'restored': True, 'session_file': str(session_file)}))
            session = {'project': str(root), 'session_file': str(session_file),
                       'owner': 'test', 'game_pid': 1, 'game_identity': '1'}
            args = SimpleNamespace(output=output, plan=plan, camera_calibration=calibration,
                                   stage='original', partition='calibration', marker_snapshot=None)
            with patch.object(observer, 'ROOT', root), patch.object(observer, 'Client', Client), \
                    patch.object(observer, 'SignCheck', Check), \
                    patch.object(observer, 'load_session', return_value=session), \
                    patch.object(observer, 'freeze', side_effect=freeze), \
                    patch.object(observer, 'source_errors', return_value=[]), \
                    patch.object(observer, 'server_run', side_effect=server), \
                    patch.object(observer, 'cleanup_fixture', return_value=[{'clean': not dirty}]) as cleanup, \
                    patch.dict(os.environ, {'MCDEV_NATIVE_CAPTURE_HELPER': str(root / 'tools/capture_native_window.py')}):
                with self.assertRaises((RuntimeError, ValueError)):
                    observer.run(args)
            report = json.loads(output.read_bytes())
        return report, cleanup.call_count

    def test_partial_fixture_setup_restores_before_reporting_error(self):
        report, calls = self.check_failure()
        self.assertEqual(1, calls)
        self.assertTrue(report['restored'])
        self.assertFalse(report['completed'])

    def test_failed_fixture_cleanup_cannot_report_restored(self):
        report, calls = self.check_failure(dirty=True)
        self.assertEqual(1, calls)
        self.assertFalse(report['restored'])
        self.assertTrue(report['cleanup_errors'])

    def test_previous_fixture_is_left_for_its_owner(self):
        report, calls = self.check_failure(existing=True)
        self.assertEqual(0, calls)
        self.assertFalse(report['completed'])
        self.assertFalse(report['restored'])


if __name__ == '__main__':
    unittest.main()

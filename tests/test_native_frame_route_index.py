"""Reject checkout normalization and drift in available frozen route evidence."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'tools/data/native_frame_route_r11.json'
EXPECTED_SHA256 = 'e1fa7772c84323c23803c8569a78e7bc8938aa6b041d5d1c0a93f9fe5d012d92'


class NativeFrameRouteIndex(unittest.TestCase):
    def test_frozen_index_retains_the_declared_bytes_and_stopped_session_graph(self):
        payload = INDEX.read_bytes()
        self.assertEqual(EXPECTED_SHA256, hashlib.sha256(payload).hexdigest())
        report = json.loads(payload)
        self.assertFalse(report['production_rendering_accepted'])
        self.assertEqual(8, len(report['sessions']))
        paths = set()
        for session in report['sessions']:
            self.assertEqual('stopped', session['state'])
            self.assertEqual(32, len(session['id']))
            for row in [session['session'], session['log']] + session['artifacts']:
                path = Path(row['path'])
                self.assertTrue(path.is_absolute())
                self.assertIn(session['id'], path.parts)
                self.assertNotIn(str(path), paths)
                paths.add(str(path))
                self.assertGreater(row['bytes'], 0)
                self.assertRegex(row['sha256'], r'^[0-9a-f]{64}$')
                if path.is_file():
                    payload = path.read_bytes()
                    self.assertEqual(row['bytes'], len(payload), str(path))
                    self.assertEqual(row['sha256'], hashlib.sha256(payload).hexdigest(), str(path))
        self.assertEqual(232, len(paths))

    def test_corrected_crosshair_control_keeps_the_frame_route_unaccepted(self):
        report = json.loads(INDEX.read_bytes())
        markers = report['corrected_route_markers']
        for scope in ('body', 'combined'):
            self.assertFalse(markers[scope]['magenta']['positive'])
            self.assertEqual(0, markers[scope]['magenta']['pixels'])
        self.assertEqual(68693, markers['sign_control']['magenta']['pixels'])
        self.assertTrue(markers['sign_control']['magenta']['positive'])
        self.assertEqual(0, markers['sign_control']['green']['pixels'])
        self.assertFalse(markers['sign_control']['green']['positive'])


if __name__ == '__main__':
    unittest.main()

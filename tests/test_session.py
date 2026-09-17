import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.session import Session


class Bridge:
    def __init__(self):
        self.data = None
    def save_library(self, data):
        self.data = data
        return True
    def later(self, delay, callback):
        pass


class SessionTests(unittest.TestCase):
    def test_native_utf8_input_can_be_saved_and_reloaded(self):
        b = Bridge()
        s = Session(b)
        s.set('name', '中文建筑名称足够长以覆盖字节截断'.encode('utf8'))
        s.save()
        s.load(s.library[0]['id'])
        self.assertEqual(s.editor.document.name, '中文建筑名称足够长以覆盖字节截断')
        self.assertEqual(s.editor.document.name[:4], '中文建筑')

    def test_notifications_have_monotonic_versions_for_memoized_components(self):
        s = Session(Bridge())
        observed = []
        s.subscribe(lambda: observed.append(s.ui_revision))
        s.set('camera_yaw', 90)
        s.set('page', 'library')
        self.assertEqual(observed, [1, 2])

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
    def test_pane_navigation_only_notifies_owners_without_invalidating_content(self):
        s = Session(Bridge())
        calls = []
        s.subscribe(lambda: calls.append('workspace'), ())
        s.subscribe(lambda: calls.append('viewport'), ('view',))
        remove = s.subscribe(lambda: calls.append('inspector'), ('view', 'inspector'))
        s.set('inspector', 'layers')
        self.assertEqual(calls, ['inspector'])
        calls[:] = []
        s.set('view', 'layer')
        self.assertEqual(calls, ['viewport', 'inspector'])
        self.assertEqual(s.content_revision, 0)
        calls[:] = []
        s.set('view', 'layer')
        self.assertEqual(calls, [])
        remove()
        s.set_editor('thickness', 3)
        self.assertEqual(calls, ['workspace', 'viewport'])
        self.assertEqual(s.content_revision, 1)

    def test_slider_changes_store_immediately_but_publish_once_after_settle(self):
        b = Bridge()
        timers = []
        b.later = lambda delay, callback: timers.append(callback)
        s = Session(b)
        published = []
        s.subscribe(lambda: published.append(s.editor.thickness))
        for value in (2, 3, 4, 4, 5):
            s.range_value('thickness', value)
        self.assertEqual(s.editor.thickness, 5)
        self.assertEqual(published, [])
        for timer in timers:
            timer()
        self.assertEqual(published, [5])
        s.range_value('opacity', .35, editor=False)
        self.assertEqual(s.opacity, .35)

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

    def test_failed_preview_preserves_last_model_and_can_retry(self):
        b = Bridge()
        s = Session(b)
        s.model_name = 'last_good'
        def failure(*unused):
            raise ValueError('invalid geometry')
        b.geometry = failure
        s._build_preview()
        self.assertEqual(s.model_name, 'last_good')
        self.assertIsNone(s.model_revision)
        b.geometry = lambda *unused: 'recovered'
        s._build_preview()
        self.assertEqual(s.model_name, 'recovered')
        self.assertIsNotNone(s.model_revision)

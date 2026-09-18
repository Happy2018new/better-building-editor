import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.session import Session
from projection.model import Document, Editor


class Bridge:
    def __init__(self):
        self.data = None
    def save_library(self, data):
        self.data = data
        return True
    def later(self, delay, callback):
        pass


class SessionTests(unittest.TestCase):
    def test_restart_normalizes_native_utf8_large_archive_titles(self):
        b = Bridge()
        title = '自动验证 · 大范围建筑'
        b.load_library = lambda: {'serial': 12, 'buildings': [{'id': 9, 'data': {
            'version': 3, 'name': title.encode('utf8'), 'size': [256, 384, 256], 'parts': 13, 'blockCount': 25165824}}]}
        b.player_origin = lambda: (0, 64, 0)
        s = Session(b)
        s.initialize()
        self.assertEqual(title, s.library[0]['data']['name'])
        self.assertIsInstance(s.library[0]['data']['name'], str)
        self.assertEqual(12, s.library_serial)

    def test_detail_camera_center_does_not_follow_each_picked_block(self):
        s = Session(Bridge())
        s.editor = Editor(Document((256, 384, 256)))
        s.focus_preview((120, 120, 120))
        signature = s.preview_signature()
        s.focused = (125, 125, 125)
        self.assertEqual(signature, s.preview_signature())
        self.assertEqual((120, 120, 120), s.preview_center)
        s.layer(200)
        self.assertEqual((120, 200, 120), s.preview_center)

    def test_failed_async_load_retains_current_draft_and_releases_ui(self):
        b = Bridge()
        timers = []
        b.later = lambda delay, callback: timers.append(callback)
        b.load_archive_page = lambda identity, part: None
        s = Session(b)
        before = s.editor
        s.library = [{'id': 3, 'data': {'version': 3, 'name': 'missing', 'size': [256, 384, 256], 'parts': 2, 'blockCount': 5}}]
        s.load(3)
        self.assertIs(s.editor, before)
        self.assertIsNotNone(s.io_job)
        self.assertFalse(s.action(s.demo))
        timers.pop(0)()
        self.assertIsNone(s.io_job)
        self.assertIs(s.editor, before)
        self.assertIn('缺失', s.editor.message)

    def test_async_large_save_load_and_delete_preserve_small_index(self):
        b = Bridge()
        timers, pages = [], {}
        b.later = lambda delay, callback: timers.append(callback)
        def write(identity, part, value):
            pages[identity, part] = value
            return True
        b.save_archive_page = write
        b.load_archive_page = lambda identity, part: pages.get((identity, part))
        cleared = []
        b.clear_archive = lambda identity, parts: cleared.append((identity, parts))
        s = Session(b)
        s.editor = Editor(Document((256, 384, 256)))
        s.editor.run('fill')
        s.save()
        while s.io_job is not None:
            timers.pop(0)()
        self.assertEqual(1, len(s.library))
        self.assertNotIn('chunks', b.data['buildings'][0]['data'])
        identity = s.library[0]['id']
        self.assertEqual(3, s.library[0]['data']['version'])
        s.editor = Editor(Document())
        s.load(identity)
        while s.io_job is not None:
            timers.pop(0)()
        self.assertEqual(25165824, len(s.editor.document.blocks))
        s.delete(identity)
        self.assertEqual([], s.library)
        self.assertEqual(identity, cleared[0][0])

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

    def test_page_and_category_navigation_do_not_broadcast_document_changes(self):
        s = Session(Bridge())
        calls = []
        s.subscribe(lambda: calls.append('root'), ())
        s.subscribe(lambda: calls.append('page'), ('page',))
        s.subscribe(lambda: calls.append('tools'), ('group', 'query'))
        s.set('page', 'library')
        s.set('query', '填充')
        s.choose_group('shape')
        self.assertEqual(calls, ['page', 'tools', 'tools'])
        self.assertEqual(s.content_revision, 0)
        self.assertEqual(s.query, '')
        s.choose_group('shape')
        self.assertEqual(len(calls), 3)

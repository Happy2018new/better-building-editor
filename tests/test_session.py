import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.session import Session
from projection.model import Document, Editor
from projection.coordinates import parse_coordinates


class Bridge:
    def __init__(self):
        self.data = None
    def save_library(self, data):
        self.data = data
        return True
    def later(self, delay, callback):
        pass


class SessionTests(unittest.TestCase):
    def test_rename_uses_target_dialog_name_and_preserves_archived_data(self):
        import copy
        bridge = Bridge(); s = Session(bridge)
        s.name = 'unsaved draft'
        s.library = [{'id': 7, 'data': {'name': 'old', 'version': 3, 'size': [256,384,256],
                      'parts': 50, 'blockCount': 100000}},
                     {'id': 8, 'data': {'name': 'neighbor', 'version': 1, 'size': [1,1,1], 'blocks': []}}]
        before = copy.deepcopy(s.library)
        calls = []
        s.subscribe(lambda: calls.append('workspace'), ())
        s.subscribe(lambda: calls.append('library'), ('library',))
        s.open_rename(7)
        self.assertEqual((7, 'old'), s.pending_rename)
        s.accept_rename('  renamed  ')
        self.assertIsNone(s.pending_rename)
        self.assertEqual('unsaved draft', s.name)
        before[0]['data']['name'] = 'renamed'
        self.assertEqual(before, s.library)
        self.assertEqual(before, bridge.data['buildings'])
        self.assertEqual(['library'], calls)

    def test_rename_validation_failure_and_cancel_never_mutate_library(self):
        bridge = Bridge(); s = Session(bridge)
        original = [{'id': 1, 'data': {'name': 'original', 'size': [1,1,1], 'blocks': []}}]
        s.library = original
        s.open_rename(1)
        s.accept_rename(' ')
        self.assertIs(s.library, original)
        self.assertIsNone(bridge.data)
        self.assertIsNotNone(s.pending_rename)
        self.assertTrue(s.rename_error)
        s.io_job = iter(())
        s.accept_rename('while saving')
        self.assertIsNone(bridge.data)
        self.assertIs(s.library, original)
        s.io_job = None
        bridge.save_library = lambda data: False
        s.accept_rename('valid')
        self.assertEqual('original', s.library[0]['data']['name'])
        self.assertIsNotNone(s.pending_rename)
        s.set('pending_rename', None)
        self.assertIsNone(s.pending_rename)
        self.assertEqual('original', s.library[0]['data']['name'])
        with self.assertRaisesRegex(ValueError, '不存在'):
            s.rename(2, 'valid')

    def test_smaller_editing_cap_preserves_old_library_entries(self):
        b = Bridge()
        entries = [{'id': 1, 'data': {'version': 1, 'name': 'legacy',
                   'size': [256, 384, 256], 'blocks': []}},
                   {'id': 2, 'data': {'version': 3, 'name': 'archive',
                   'size': [256, 384, 256], 'blockCount': 25165824, 'parts': 50}}]
        b.load_library = lambda: {'serial': 2, 'buildings': entries}
        b.player_origin = lambda: (0, 64, 0)
        s = Session(b); s.initialize()
        before = s.editor
        for identity in (1, 2):
            with self.assertRaisesRegex(ValueError, '64 × 128 × 64'):
                s.load(identity)
            self.assertIs(before, s.editor)
            self.assertIsNone(s.io_job)
        s.save()
        self.assertEqual(entries, b.data['buildings'][:2])
        self.assertEqual(3, b.data['serial'])

    def test_size_preset_works_when_native_text_input_is_invalid(self):
        s = Session(Bridge()); s.new_size_valid = False
        s.empty((64, 100, 64))
        self.assertEqual((64, 100, 64), s.editor.document.size)
        self.assertEqual(409600, len(s.editor.selection))

    def test_camera_buttons_only_invalidate_view_owners(self):
        s = Session(Bridge()); calls = []
        s.subscribe(lambda: calls.append('workspace'), ())
        s.subscribe(lambda: calls.append('navigation'), ('camera_depth',))
        revision = s.content_revision
        s.move_depth(1)
        self.assertEqual(['navigation'], calls)
        self.assertEqual(revision, s.content_revision)

    def test_edit_modes_notify_only_consumers_and_preserve_selection(self):
        s = Session(Bridge()); calls = []
        s.subscribe(lambda: calls.append('workspace'), ())
        s.subscribe(lambda: calls.append('editor'), ('editing_mode',))
        selection = s.editor.selection
        revision = s.content_revision
        s.inspector = 'history'
        s.choose_tool('paste')
        self.assertEqual(['editor'], calls)
        self.assertEqual('params', s.inspector)
        self.assertFalse(s.paste_pinned)
        self.assertEqual(tuple(s.editor.start), s.paste_origin)
        calls[:] = []
        s.box_anchor = (0, 0, 0)
        s.choose_mode('place')
        self.assertEqual(['editor'], calls)
        self.assertIsNone(s.box_anchor)
        self.assertIs(selection, s.editor.selection)
        self.assertEqual(revision, s.content_revision)

    def test_inventory_visibility_and_material_choice_publish_to_their_owners(self):
        s = Session(Bridge()); s.catalogue_ready = True
        calls = []
        s.subscribe(lambda: calls.append('workspace'), ())
        s.subscribe(lambda: calls.append('inventory'), ('material_browser',))
        s.subscribe(lambda: calls.append('materials'), ('materials',))
        s.open_materials('secondary')
        self.assertEqual(['inventory'], calls)
        calls[:] = []
        s.set('material_browser', None)
        self.assertEqual(['inventory'], calls)
        s.open_materials('secondary'); calls[:] = []
        s.add_material(('minecraft:stone',0))
        self.assertEqual(['materials','inventory'],calls)
        self.assertEqual(('minecraft:stone',0),s.editor.secondary)

    def test_touch_direct_actions_commit_without_confirmation(self):
        s = Session(Bridge()); s.editor = Editor(Document((8,8,8))); s.touch_mode = True
        s.choose_mode('place'); self.assertTrue(s.point_action((3,0,3)))
        self.assertEqual(1,len(s.editor.document.blocks))
        s.choose_mode('erase'); s.erase_scope = 'single'
        self.assertTrue(s.point_action((3,0,3)))
        self.assertFalse(s.editor.document.blocks)
        s.editor.undo(); self.assertEqual(1,len(s.editor.document.blocks))

    def test_reset_cancels_pending_locate_and_all_camera_targets(self):
        s = Session(Bridge()); s.camera_pivot = (50.,70.,60.)
        s.focused = (40,50,30); s.locate_selected()
        s.camera_pan = (7.,-5.); s.zoom = 80.
        serial=s.camera_reset_revision; s.reset_camera()
        self.assertIsNone(s.camera_focus_request)
        self.assertIsNone(s.camera_pivot)
        self.assertEqual((0.,0.),s.camera_pan)
        self.assertEqual((35.,25.,1.),(s.camera_yaw,s.camera_pitch,s.zoom))
        self.assertEqual(serial+1,s.camera_reset_revision)

    def test_dimensions_accept_native_utf8_and_common_separators(self):
        for text in ('3, 8, 3', '3，8，3', '３，８，３', '3×8×3', '3 * 8 * 3', '3 8 3', '3、8、3'):
            for raw in (text, text.encode('utf8')):
                self.assertEqual((3, 8, 3), parse_coordinates(raw))
        for raw in ('3,8', '3,,8,3', '3.5,8,3', '3,8,', ''):
            with self.assertRaises(ValueError):
                parse_coordinates(raw)

    def test_new_size_never_silently_uses_previous_document(self):
        s = Session(Bridge())
        for size in ((3, 8, 3), (37, 13, 63), (64, 100, 64)):
            s.new_size = size
            s.empty()
            self.assertEqual(size, s.editor.document.size)
            self.assertEqual(size[0]*size[1]*size[2], len(s.editor.selection))
        previous = s.editor
        for size in ((0, 8, 3), (257, 8, 3)):
            s.new_size = size
            with self.assertRaises(ValueError):
                s.empty()
            self.assertIs(previous, s.editor)
        s.new_size_valid = False
        with self.assertRaises(ValueError):
            s.empty()
        self.assertIs(previous, s.editor)

    def test_empty_space_boundary_controls_modify_one_shared_selection(self):
        s = Session(Bridge())
        s.editor = Editor(Document((5, 5, 5)))
        s.editor.select_box((2, 2, 2), (2, 2, 2))
        s.box_anchor = (1, 1, 1)
        for axis in range(3):
            s.adjust_boundary(axis, 0, -1)
            s.adjust_boundary(axis, 1, 1)
        self.assertEqual((1, 1, 1), s.editor.start)
        self.assertEqual((3, 3, 3), s.editor.end)
        self.assertEqual(27, len(s.editor.selection))
        self.assertIsNone(s.box_anchor)
        self.assertEqual(0, len(s.editor.document.blocks))
        self.assertFalse(s.editor.undo_stack)
        for unused in range(8):
            s.adjust_boundary(0, 0, -1)
            s.adjust_boundary(0, 1, 1)
        self.assertEqual(0, s.editor.start[0])
        self.assertEqual(4, s.editor.end[0])

    def test_picking_does_not_move_workplane_and_section_preserves_data(self):
        s = Session(Bridge())
        s.editor.layer = 3
        before = s.editor.document.to_data()
        s.choose_mode('select')
        s.point_action((2, 8, 2))
        self.assertEqual(3, s.editor.layer)
        signature = s.preview_signature()
        s.toggle_section()
        self.assertNotEqual(signature, s.preview_signature())
        self.assertTrue(s.visible_layer(3))
        self.assertFalse(s.visible_layer(4))
        self.assertIn(4, s.preview_hidden())
        self.assertEqual(before, s.editor.document.to_data())
        s.layer(8)
        self.assertTrue(s.visible_layer(8))
        s.choose_mode('place')
        s.point_action((2, 8, 2), (0, 1, 0))
        self.assertFalse(s.editor.undo_stack)

    def test_restart_normalizes_native_utf8_large_archive_titles(self):
        b = Bridge()
        title = '自动验证 · 大范围建筑'
        b.load_library = lambda: {'serial': 12, 'buildings': [{'id': 9, 'data': {
            'version': 3, 'name': title.encode('utf8'), 'size': [64, 100, 64], 'parts': 13, 'blockCount': 409600}}]}
        b.player_origin = lambda: (0, 64, 0)
        s = Session(b)
        s.initialize()
        self.assertEqual(title, s.library[0]['data']['name'])
        self.assertIsInstance(s.library[0]['data']['name'], str)
        self.assertEqual(12, s.library_serial)

    def test_locate_is_camera_only_and_never_hides_other_blocks(self):
        s = Session(Bridge()); s.editor = Editor(Document((64,128,64)))
        s.focused = (55,95,63); before=s.preview_signature(); s.locate_selected()
        self.assertEqual((55.5,95.5,63.5),s.camera_focus_request)
        self.assertEqual(before,s.preview_signature())
        self.assertTrue(s.visible_position((0,0,0)))
        self.assertTrue(s.visible_position((63,127,63)))

    def test_failed_async_load_retains_current_draft_and_releases_ui(self):
        b = Bridge()
        timers = []
        b.later = lambda delay, callback: timers.append(callback)
        b.load_archive_page = lambda identity, part: None
        s = Session(b)
        before = s.editor
        s.library = [{'id': 3, 'data': {'version': 3, 'name': 'missing', 'size': [64, 100, 64], 'parts': 2, 'blockCount': 5}}]
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
        s.editor = Editor(Document((64, 100, 64)))
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
        self.assertEqual(409600, len(s.editor.document.blocks))
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

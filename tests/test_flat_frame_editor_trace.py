"""Keep submitted item coordinates when a ready editor still renders no item."""
import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_debug_blueprints import INSTALL_PROBE
from trace_flat_frame_editor import frame_submission
import trace_flat_frame_editor as trace


class FrameEditorTraceTests(unittest.TestCase):
    def archived_report(self, directory):
        from PIL import Image
        directory = Path(directory)
        controls = {}
        for name in ('combined', 'combined_repeat', 'body', 'blank', 'item_only', 'positive'):
            image = Image.new('RGB', (20, 20), 'white')
            if name != 'blank':
                image.paste('black', (4, 4, 16, 16))
            capture = directory / (name + '.png')
            image.save(capture)
            controls[name] = {'capture': {
                'path': str(directory / 'removed-session' / capture.name),
                'sha256': hashlib.sha256(capture.read_bytes()).hexdigest()}}
        report = directory / 'report.json'
        report.write_text(json.dumps({'controls': controls, 'crop': [0, 0, 20, 20]}), encoding='utf8')
        return report

    def test_archived_report_replays_after_original_session_is_removed(self):
        with TemporaryDirectory() as directory:
            report = self.archived_report(directory)
            original = report.read_bytes()
            result = trace.score_existing(report)
            self.assertEqual(144, result['body_roi_from_body_vs_blank']['pixels'])
            self.assertEqual(0, result['combined_vs_body']['combined']['pixels'])
            self.assertFalse(result['production_rendering_accepted'])
            self.assertEqual(original, report.read_bytes())

    def test_archived_capture_with_wrong_hash_is_rejected(self):
        with TemporaryDirectory() as directory:
            report = self.archived_report(directory)
            (Path(directory) / 'combined.png').write_bytes(b'altered archive bytes')
            with self.assertRaisesRegex(ValueError, 'Capture SHA-256 mismatch'):
                trace.score_existing(report)

    def test_item_only_control_preserves_volume_and_item_index_without_source_mutation(self):
        data = {'volume': (8, 8, 17), 'common': {('minecraft:frame', 2): [219],
            ('modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0): [795]},
            'states': {('minecraft:frame', 2): {'facing_direction': 2}},
            'actor': {'minecraft:frame': {219: {'Item': 'retained document actor'}}}}
        original = copy.deepcopy(data)
        native_calls = []

        class Palette:
            def SerializeBlockPalette(self):
                return self.data

            def DeserializeBlockPalette(self, value):
                self.data = value
                return True

        palette = Palette()
        palette.data = data
        native = SimpleNamespace(CombineBlockPaletteToGeometry=lambda palette, name, mode:
                                 native_calls.append(copy.deepcopy(palette.data)) or name)
        factory = SimpleNamespace(CreateBlockGeometry=lambda level: native,
                                  CreateBlock=lambda level: SimpleNamespace(GetBlankBlockPalette=Palette))
        bridge = SimpleNamespace(factory=factory)
        probe_sys = SimpleNamespace(_blueprint_qa_nonce=1)
        namespace = {'b': bridge, 'sys': probe_sys}
        exec(compile(trace.INSTALL_CONTROLS, '<frame controls>', 'exec'), namespace)
        for control in ('item_only', 'blank', 'positive'):
            probe_sys._frame_editor_control = control
            self.assertEqual('model', bridge.factory.CreateBlockGeometry('level').CombineBlockPaletteToGeometry(palette, 'model'))
        self.assertEqual(original, data)
        for row in native_calls:
            self.assertEqual((8, 8, 17), row['volume'])
            self.assertEqual([795], list(row['common'].values())[0])
            self.assertEqual({}, row['states'])
            self.assertEqual({}, row['actor'])
        self.assertEqual(original['common'][('modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0)],
                         native_calls[0]['common'][('modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0)])
        self.assertEqual([795], native_calls[1]['common'][('minecraft:air', 0)])
        self.assertEqual([795], native_calls[2]['common'][('modern_projection:preview_shulker_blue_0', 0)])

    def test_pixel_trace_keeps_absolute_bounds_outside_body_roi(self):
        from PIL import Image
        with TemporaryDirectory() as directory:
            blank_path, shown_path = (Path(directory) / name for name in ('blank.png', 'shown.png'))
            Image.new('RGB', (40, 30), 'white').save(blank_path)
            shown = Image.new('RGB', (40, 30), 'white')
            shown.paste('black', (25, 20, 28, 24))
            shown.save(shown_path)
            full = trace.pixel_trace(shown_path, blank_path, (5, 5, 35, 28))
            roi = trace.pixel_trace(shown_path, blank_path, (5, 5, 20, 20))
            self.assertEqual(12, full['pixels'])
            self.assertEqual([25, 20, 28, 24], full['bbox'])
            self.assertEqual(0, roi['pixels'])
            self.assertIsNone(roi['bbox'])

    def test_native_probe_records_serialized_items_without_mutating_palette(self):
        data = {'volume': (8, 8, 17), 'common': {
            ('minecraft:frame', 2): [219],
            ('modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0): [795],
            ('minecraft:stone', 0): [0]}, 'actor': {}, 'extra': {}}
        original = copy.deepcopy(data)
        native = SimpleNamespace(CombineBlockPaletteToGeometry=lambda palette, name, mode: name)
        factory = SimpleNamespace(CreateBlockGeometry=lambda level: native)
        s = SimpleNamespace(busy=False, edit_job=None, io_job=None, projection_active=False,
                            pending_confirm=None, pending_rename=None,
                            sharing=SimpleNamespace(opened=False),
                            editor=SimpleNamespace(document=object()))
        for field in ('page', 'name', 'view', 'focus_view', 'section', 'solo_layer', 'focused', 'box_anchor',
                      'canvas_x', 'canvas_z', 'paste_origin', 'paste_pinned', 'camera_pose', 'camera_yaw',
                      'camera_pitch', 'zoom', 'camera_pan', 'camera_pivot', 'camera_depth', 'camera_depth_pose',
                      'camera_focus_request', 'camera_reset_animated', 'progress', 'direct_mode'):
            setattr(s, field, None)
        b = SimpleNamespace(factory=factory, preparing_entity=None)
        probe_sys = SimpleNamespace()
        namespace = {'s': s, 'b': b, 'sys': probe_sys,
                     'navigator': SimpleNamespace(is_transitioning=False, top=None, contains=lambda key: False),
                     'time': SimpleNamespace(time=lambda: 1.)}
        exec(compile(INSTALL_PROBE, '<frame diagnostic probe>', 'exec'), namespace)
        palette = SimpleNamespace(SerializeBlockPalette=lambda: data)
        self.assertEqual('frame', b.factory.CreateBlockGeometry('level').CombineBlockPaletteToGeometry(palette, 'frame'))
        record = probe_sys._blueprint_qa_records[0]
        self.assertEqual(original, data)
        self.assertEqual({219, 795}, {index for row in record['frame_materials'] for index in row['indices']})
        self.assertEqual(2, len(record['frame_materials']))
        summary = frame_submission({'native_calls': [record], 'parts': [{'render_layout': ((8, 8, 8), (8, 8, 17))}]})
        self.assertEqual(1, summary['item_cells'])
        self.assertEqual([795], summary['item_materials'][0]['indices'])
        self.assertEqual([((8, 8, 8), (8, 8, 17))], summary['layouts'])

    def test_body_only_and_cached_submissions_remain_distinguishable(self):
        body = {'frame_materials': [{'material': ('minecraft:frame', 2), 'indices': [219]}]}
        self.assertEqual(0, frame_submission({'native_calls': [body], 'parts': []})['item_cells'])
        cached = frame_submission({'native_calls': [], 'parts': [{'render_layout': ((8, 8, 8), (8, 8, 17))}]})
        self.assertEqual(0, cached['native_call_count'])
        self.assertEqual(0, cached['item_cells'])
        self.assertEqual(1, len(cached['layouts']))

    def test_capture_failure_keeps_ready_submission_and_runs_restoration(self):
        loaded = {'metadata': {'name': 'frame', 'size': [8, 8, 8], 'blocks': 1},
                  'document': {'same': True}, 'editor_id': 1, 'document_id': 2}
        ready = {'native_calls': [{'frame_materials': [{'material': [
            'modern_projection:preview_item_minecraft_diamond_sword_0_f2_r0', 0], 'indices': [795]}]}],
                 'parts': [{'render_layout': [[8, 8, 8], [8, 8, 17]]}]}
        calls = []

        def run(code):
            calls.append(code)
            return loaded if code == trace.LOAD else True

        def capture(label):
            raise RuntimeError('declared capture failure')

        check = SimpleNamespace(run=run, wait=lambda *args: None,
                                editor_preview=lambda *args: ready, capture=capture,
                                navigation=lambda: {'open': False, 'transition': False})
        context = SimpleNamespace(__enter__=lambda self: self, __exit__=lambda *args: False)

        class Client:
            def __enter__(self):
                return context

            def __exit__(self, *args):
                return False

        with TemporaryDirectory() as directory:
            output = Path(directory) / 'failed.json'
            with patch.object(trace, 'Client', lambda **kwargs: Client()), \
                    patch.object(trace, 'SignCheck', lambda *args, **kwargs: check), \
                    patch.object(sys, 'argv', ['trace', str(output)]), \
                    patch.dict(os.environ, {'MCDEV_NATIVE_CAPTURE_HELPER': str(ROOT / 'tools/capture_native_window.py')}):
                with self.assertRaisesRegex(RuntimeError, 'declared capture failure'):
                    trace.main()
            result = json.loads(output.read_text(encoding='utf8'))
            self.assertEqual(ready, result['controls']['combined']['ready'])
            self.assertEqual(1, result['controls']['combined']['submission']['item_cells'])
            self.assertEqual([795], result['controls']['combined']['submission']['item_materials'][0]['indices'])
            self.assertFalse(result['completed'])
            self.assertFalse(result['passed'])
            self.assertTrue(result['restored'])
            self.assertIn(trace.RESTORE_PROFILES, calls)
            self.assertIn(trace.RESTORE, calls)


if __name__ == '__main__':
    unittest.main()

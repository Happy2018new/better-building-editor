"""Exercise the native probe's generated commands against real application state."""
from pathlib import Path
import hashlib
import json
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from run_snow_scene_lifecycle_r20 import BIND_SOURCE, MEMORY_LIBRARY, RESTORE_LIBRARY, STEPS, snow_control_checks
from projection import block_registry as registry
from projection.cell import make_cell
from projection.model import Document
from projection.session import Session
from test_complete_cell_workflows_r11 import WorkflowBridge


class SnowLifecycleProbeR20Tests(unittest.TestCase):
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

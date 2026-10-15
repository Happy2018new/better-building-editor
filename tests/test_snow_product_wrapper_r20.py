"""A failed native workflow must stay failed after its process terminates."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_snow_product_r20 as probe


class SnowProductWrapperR20Tests(unittest.TestCase):
    def test_finished_process_preserves_incomplete_workflow_and_successful_restore(self):
        with TemporaryDirectory(prefix='snow-wrapper-') as temporary:
            project = Path(temporary).resolve()
            output = project / 'output'
            launch = project / 'launch.json'
            launch.write_text(json.dumps({'files': {}}), encoding='utf8')
            session = dict(project=str(project), owner='test-snow', session_file='host-only',
                           game_pid=1, game_identity='game', mcdk_pid=2, mcdk_identity='mcdk', mcp_url='host-only')

            def finish(*unused, **kwargs):
                (output / 'report.json').write_text(json.dumps(
                    dict(completed=False, passed=False, restored=True)), encoding='utf8')
                return SimpleNamespace(returncode=1)

            arguments = ['probe', '--session', 'host-only', '--owner', 'test-snow',
                '--project', str(project), '--launch-inputs', str(launch), '--output', str(output), '--phase', 'lifecycle']
            with patch.object(sys, 'argv', arguments), patch.object(probe, 'load_session', return_value=session), \
                    patch.object(probe, 'snapshot_sources', return_value={}), patch.object(probe, 'host_data', return_value={}), \
                    patch.object(probe.shutil, 'copyfile'), patch.object(probe.subprocess, 'run', side_effect=finish):
                self.assertEqual(1, probe.main())
            receipt = json.loads((output / 'receipt.json').read_bytes())
            self.assertTrue(receipt['process_completed'])
            self.assertFalse(receipt['completed'])
            self.assertFalse(receipt['passed'])
            self.assertTrue(receipt['restored'])
            self.assertEqual(hashlib.sha256((output / 'report.json').read_bytes()).hexdigest(), receipt['report_sha256'])


if __name__ == '__main__':
    unittest.main()

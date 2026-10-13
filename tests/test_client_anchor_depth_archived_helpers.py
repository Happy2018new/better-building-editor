"""Cold offline depth entry in an ordinary checkout with no sibling helpers."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArchivedHelpers(unittest.TestCase):
    def test_no_siblings_and_current_tools_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'checkout'
            project.mkdir()
            for relative in ('tools', 'behavior_pack', '.agents/skills/pyreact-debugging/scripts'):
                for source in (ROOT / relative).rglob('*.py'):
                    if '__pycache__' in source.parts:
                        continue
                    target = project / source.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            for relative in ('docs/evidence/client-anchor-world-ui-r14-v1',
                             'docs/evidence/client-anchor-depth-r15-v1/candidate-bundle'):
                shutil.copytree(ROOT / relative, project / relative)
            relative = Path('docs/evidence/client-anchor-depth-r15-v1/owner-source-snapshots/source-011.bin')
            (project / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, project / relative)
            test_directory = project / 'tests'
            test_directory.mkdir()
            for source in (ROOT / 'tests').glob('test_client_anchor_depth*_r1*.py'):
                shutil.copyfile(source, test_directory / source.name)
            subprocess.run(['git', 'init', '-q', str(project)], check=True, capture_output=True)
            self.assertFalse((project.parent / 'r11-entities').exists())
            code = '''import hashlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
import verify_snow_plant_visibility as current
import execute_client_anchor_depth_candidate_r15 as runtime
helpers=runtime.dependencies()
assert sys.modules['verify_snow_plant_visibility'] is current
assert helpers['verify_snow_plant_visibility'] is not current
assert helpers['probe_client_anchor_paper_doll'].base is helpers['probe_native_item_paper_doll']
for name,module in helpers.items():
 p=Path(module.__file__)
 assert p.parent==runtime.HELPERS
 assert hashlib.sha256(p.read_bytes()).hexdigest()==runtime.PINS[name]
assert not any('r11-entities' in p for p in sys.path)
suite=unittest.defaultTestLoader.discover('tests',pattern='test_client_anchor_depth*_r1*.py')
result=unittest.TextTestRunner().run(suite)
assert result.testsRun==21 and result.wasSuccessful()
'''
            result = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', code],
                                    cwd=project, capture_output=True, text=True, encoding='utf8', timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

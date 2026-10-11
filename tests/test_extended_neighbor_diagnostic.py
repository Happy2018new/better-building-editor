"""Extended diagnostics reuse strict static contracts and explicit supports."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExtendedNeighborDiagnosticTests(unittest.TestCase):
    def test_every_case_binds_fixed_views_supports_and_full_missing_contracts(self):
        script = '''import sys
sys.path.insert(0,'tools')
import verify_extended_neighbor_world_visuals as extended
from projection.debug_blueprints import material
from projection.debug_neighborhood_blueprints import VISUAL_CASE
assert extended.world.world_case is extended.suite.static_world_case
assert extended.world.native.FIXTURE==VISUAL_CASE['fixture']
assert set(extended.world.native.VIEWS)=={'side','top'}
for row in VISUAL_CASE['cases']:
 delta=(7,85,-27)
 translate=lambda pos:tuple(pos[i]+delta[i] for i in range(3))
 cells=[(translate(pos),material(name,properties)) for pos,name,properties in row['blocks']]
 expected=[(translate(pos),material(name,properties)) for pos,name,properties in row['supports']]
 assert extended.supports(cells)==expected,row
 assert extended.world.native.view_offset(row['keep'],row['occupied'],row['camera']['view'])==row['camera']['offset']
 changed=list(cells)
 changed[0]=(changed[0][0],('minecraft:air',0))
 try:extended.supports(changed)
 except ValueError:pass
 else:raise AssertionError('Changed source accepted')
assert 'scaffolding_column' in extended.world.native.CROP_FIXTURE
'''
        result = subprocess.run([sys.executable, '-X', 'utf8', '-c', script], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_new_blueprint_is_python2_compatible(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Local game-compatible Python 2 interpreter is unavailable')
        source = (ROOT / 'behavior_pack/modern_projection/projection/debug_neighborhood_blueprints.py').read_bytes()
        result = subprocess.run([str(pypy), '-c', 'compile(%r,"blueprint","exec")' % source],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

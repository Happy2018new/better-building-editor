"""The seed diagnostic must reject shifts and preserve native tuple keys."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_dripstone_direct_seed as diagnostic
from verify_dripstone_native_boxes import holdout_samples, matrix


class DirectSeedDiagnosticTests(unittest.TestCase):
    def test_calibration_rejects_failed_foreign_and_stale_provenance(self):
        session = {'session_file': str(diagnostic.ROOT / '.runtime/test-session.json'),
                   'project': str(diagnostic.ROOT), 'id': 'owned', 'game_identity': '123'}
        good = {'completed': True, 'passed': True, 'session_file': session['session_file'],
                'instance_id': 'owned', 'game_identity': '123', 'restored': True}
        self.assertEqual(diagnostic.validate_calibration(good, session)['game_identity'], '123')
        for changes in ({'completed': False}, {'passed': False}, {'restored': False},
                        {'session_file': str(diagnostic.ROOT / '.runtime/foreign-session.json')},
                        {'instance_id': 'other'}, {'game_identity': '999'}):
            with self.assertRaises(AssertionError):
                diagnostic.validate_calibration(dict(good, **changes), session)

    def test_holdout_covers_signed_chunk_edges_without_overlapping_supports(self):
        plan = holdout_samples()
        cells, supports, rows = matrix(plan)
        self.assertEqual(len(plan), 92)
        self.assertEqual(len(cells), 184)
        self.assertEqual(len(rows), len(cells))
        self.assertFalse(set(pos for pos, value in cells).intersection(pos for pos, value in supports))
        roots = set(root for identity, root in plan)
        for coordinate in (-33, -32, -31, -17, -16, -15, -1, 0, 1, 15, 16, 17, 31, 32, 33):
            for y in (-47, -31):
                self.assertIn((coordinate, y, 6), roots)
                self.assertIn((6, y, coordinate), roots)

    def test_comparison_rejects_shift_and_excess_color_error(self):
        baseline = Image.new('RGB', (100, 100))
        ImageDraw.Draw(baseline).rectangle((40, 10, 49, 89), fill=(140, 110, 80))
        shifted = Image.new('RGB', baseline.size)
        ImageDraw.Draw(shifted).rectangle((46, 10, 55, 89), fill=(140, 110, 80))
        recolored = Image.new('RGB', baseline.size)
        ImageDraw.Draw(recolored).rectangle((40, 10, 49, 89), fill=(170, 110, 80))
        mask = Image.new('L', baseline.size, 255)
        same = diagnostic.compare(baseline, baseline, mask, 16, 160)
        shift = diagnostic.compare(baseline, shifted, mask, 16, 160)
        color = diagnostic.compare(baseline, recolored, mask, 16, 160)
        self.assertTrue(same['passed'], same)
        self.assertFalse(shift['passed'], shift)
        self.assertFalse(color['passed'], color)
        self.assertEqual(shift['translation'], (0, 0))
        self.assertEqual(shift['limits']['shape_recall'], .93)
        self.assertEqual(shift['limits']['color_channel_error'], 20)

    def test_empty_native_baseline_never_accepts(self):
        blank = Image.new('RGB', (100, 100))
        result = diagnostic.compare(blank, blank, Image.new('L', blank.size, 255), 16, 160)
        self.assertFalse(result['valid_baseline'], result)
        self.assertFalse(result['passed'], result)

    def test_python2_native_payload_and_tuple_key_transport(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Local game-compatible Python 2 interpreter is unavailable')
        positions = [(6, -38, 6), (6, -37, 6), (6, -36, 6), (6, -35, 6)]
        generate = diagnostic.GENERATE % (positions, 'test_seed', diagnostic.PATHS)
        payloads = [generate, diagnostic.ATTACH % 'direct_world', diagnostic.VISIBILITY % 0.,
                    diagnostic.CLEANUP, diagnostic.CAMERA % ((6, -37, 6),),
                    diagnostic.ROIS % (positions, (6.5, -36., 6.5))]
        mock = '''import json,sys
class Palette(object):
 def __init__(self,data=None):self.data=data or {'volume':(1,4,1),'common':{('minecraft:stone',0):[0,3]},'states':{('minecraft:stone',0):{u'key':True}}}
 def SerializeBlockPalette(self):return self.data
 def DeserializeBlockPalette(self,data):self.data=data;return True
class Factory(object):
 def CreateBlockGeometry(self,level):return self
 def CombineBlockFromPosListToGeometry(self,positions,name,mode,void):return Palette()
 def CombineBlockPaletteToGeometry(self,palette,name,mode):return name
 def CreateBlock(self,level):return self
 def GetBlockPaletteBetweenPos(self,low,high,void):return Palette()
 def GetBlankBlockPalette(self):return Palette()
 def CreateClientEntityByTypeStr(self,name,origin,rotation):return 'test_actor'
class Bridge(object):
 factory=Factory();system=factory;level='test_level'
class Api(object):
 def GetMinecraftVersion(self):return 'test_runtime'
b=Bridge();api=Api()
'''
        script = '\n'.join('compile(%r,%r,"exec")' % (code, 'payload_' + str(index))
                           for index, code in enumerate(payloads))
        script += '\n' + mock + '\n' + generate + '\nprint(_result)'
        completed = subprocess.run([str(pypy), '-c', script], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertTrue(result['roundtrip_equal'])
        self.assertEqual(result['origin'], [6, -38, 6])
        self.assertEqual(result['offset'], [-.5, 0., -.5])
        self.assertEqual(result['direct_palette'], result['captured_palette'])
        self.assertEqual(result['captured_palette'], result['roundtrip_palette'])
        common = next(value for key, value in result['captured_palette']['items']
                      if key.get('value') == 'common')
        self.assertEqual(common['items'][0][0]['type'], 'tuple')


if __name__ == '__main__':
    unittest.main()

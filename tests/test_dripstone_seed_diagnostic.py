"""The seed diagnostic must reject shifts and preserve native tuple keys."""
import json
import copy
from pathlib import Path
import subprocess
import sys
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_dripstone_direct_seed as diagnostic
from verify_dripstone_native_boxes import holdout_samples, matrix, verify_scene_boxes


class DirectSeedDiagnosticTests(unittest.TestCase):
    def native_client(self, server):
        client = copy.deepcopy(server)
        for row in client['rows']:
            row['value'] = [row['value']['name'], row['value']['aux']]
        return client

    def test_equal_missing_or_invalid_native_boxes_never_accept(self):
        pos = (6, -37, 6)
        valid = {'min': (6.3125, -37, 6.3125), 'max': (6.6875, -36, 6.6875)}
        expected = {pos: ('minecraft:pointed_dripstone', 4)}
        for box in (None, {}, {'min': valid['min']},
                    {'min': valid['min'], 'max': valid['min']},
                    {'min': (float('nan'), -37, 6.3125), 'max': valid['max']}):
            row = {'pos': pos, 'value': {'name': 'minecraft:pointed_dripstone', 'aux': 4},
                   'clip': box, 'collision': box}
            source = {'rows': [row]}
            with self.subTest(box=box), self.assertRaises(AssertionError):
                verify_scene_boxes(source, self.native_client(source), expected)
        row = {'pos': pos, 'value': {'name': 'minecraft:pointed_dripstone', 'aux': 4},
               'clip': valid, 'collision': valid}
        source = {'rows': [row]}
        self.assertTrue(verify_scene_boxes(source, self.native_client(source), expected)['all_boxes_valid'])

    def test_scene_verification_rejects_stale_aux_mismatched_boxes_and_nonunit_stone(self):
        pos = (6, -38, 6)
        row = {'pos': pos, 'value': {'name': 'minecraft:stone', 'aux': 0},
               'clip': {'min': pos, 'max': (7, -37, 7)}}
        row['collision'] = dict(row['clip'])
        source = {'rows': [row]}
        expected = {pos: ('minecraft:stone', 0)}
        client = self.native_client(source)
        self.assertTrue(verify_scene_boxes(source, client, expected)['stone_unit_boxes'])
        stale = copy.deepcopy(client)
        stale['rows'][0]['value'][1] = 1
        with self.assertRaises(AssertionError):
            verify_scene_boxes(source, stale, expected)
        mismatch = copy.deepcopy(client)
        mismatch['rows'][0]['collision']['min'] = (6.1, -38, 6)
        with self.assertRaises(AssertionError):
            verify_scene_boxes(source, mismatch, expected)
        nonunit = copy.deepcopy(source)
        nonunit['rows'][0]['clip']['max'] = (6.9, -37, 7)
        nonunit['rows'][0]['collision'] = dict(nonunit['rows'][0]['clip'])
        with self.assertRaises(AssertionError):
            verify_scene_boxes(nonunit, self.native_client(nonunit), expected)

    def test_scene_verification_rejects_wrong_native_shapes_and_duplicate_positions(self):
        pos = (6, -38, 6)
        row = {'pos': pos, 'value': {'name': 'minecraft:stone', 'aux': 0},
               'clip': {'min': pos, 'max': (7, -37, 7)}}
        row['collision'] = dict(row['clip'])
        source = {'rows': [row]}
        expected = {pos: ('minecraft:stone', 0)}
        client = self.native_client(source)
        for value in (None, 'minecraft:stone', ['minecraft:stone'],
                      ['minecraft:stone', 0, 1], {'name': 'minecraft:stone', 'aux': 0}):
            changed = copy.deepcopy(client)
            changed['rows'][0]['value'] = value
            with self.subTest(value=value), self.assertRaises(AssertionError):
                verify_scene_boxes(source, changed, expected)
        with self.assertRaises(AssertionError):
            verify_scene_boxes({'rows': source['rows'] * 2}, client, expected)
        with self.assertRaises(AssertionError):
            verify_scene_boxes(source, {'rows': client['rows'] * 2}, expected)

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

    def test_static_paths_preserve_public_moss_cells_tip_state_and_top_support(self):
        for identity, keep_y in (('hanging_moss', 87), ('hanging_moss_cross_chunk', 88)):
            cells, supports, keep, occupied = diagnostic.static_fixture_plan(identity)
            with self.subTest(identity=identity):
                self.assertEqual(len(cells), 5)
                self.assertEqual({pos for pos, value in cells}, {(6, y, 6) for y in range(86, 91)})
                values = dict(cells)
                self.assertEqual(values[(6, 86, 6)], ('minecraft:pale_hanging_moss', 1))
                self.assertTrue(all(values[(6, y, 6)] == ('minecraft:pale_hanging_moss', 0)
                                    for y in range(87, 91)))
                self.assertEqual(supports, [((6, 91, 6), ('minecraft:stone', 0))])
                self.assertEqual(keep, (6, keep_y, 6))
                self.assertEqual(occupied, (6, keep_y - 1, 6))

    def test_static_verification_accepts_native_server_dict_and_client_pair(self):
        expected = {(6, 86, 6): ('minecraft:pale_hanging_moss', 1)}
        server = {'rows': [{'pos': [6, 86, 6], 'value': {'name': 'minecraft:pale_hanging_moss', 'aux': 1}}]}
        client = {'rows': [{'pos': [6, 86, 6], 'value': ['minecraft:pale_hanging_moss', 1]}]}
        self.assertTrue(diagnostic.verify_static_values(server, client, expected)['original_names_and_aux_equal'])
        for invalid in ({'rows': []},
                        {'rows': client['rows'] * 2},
                        {'rows': [{'pos': [6, 86, 6], 'value': ['minecraft:pale_hanging_moss', 0]}]}):
            with self.assertRaises(AssertionError):
                diagnostic.verify_static_values(server, invalid, expected)

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
        payloads = [generate, diagnostic.ATTACH % 'direct_world', diagnostic.VISIBILITY % True,
                    diagnostic.CLEANUP, diagnostic.CAMERA % ((6, -37, 6),),
                    diagnostic.ROIS % (positions, (6.5, -36., 6.5)),
                    diagnostic.STATIC_CAPABILITY % ([], [])]
        mock = '''import json,sys
class Palette(object):
 def __init__(self,data=None):self.data=data or {'volume':(1,1,4),'common':{('minecraft:stone',0):[0,3]},'states':{('minecraft:stone',0):{u'key':True}}}
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
        self.assertEqual(result['volume'], [1, 1, 4])
        self.assertEqual(result['offset'], [-.5, 0., -.5])
        self.assertEqual(result['direct_palette'], result['captured_palette'])
        self.assertEqual(result['captured_palette'], result['roundtrip_palette'])
        common = next(value for key, value in result['captured_palette']['items']
                      if key.get('value') == 'common')
        self.assertEqual(common['items'][0][0]['type'], 'tuple')


if __name__ == '__main__':
    unittest.main()

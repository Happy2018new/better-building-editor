"""Reject misleading frame-block evidence bindings and altered native block NBT."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import archive_frame_block_evidence_r21 as archive


def native_row():
    original = {'Name': {'__type__': 8, '__value__': 'minecraft:quartz_block'},
        'Damage': {'__type__': 2, '__value__': 0}, 'Count': {'__type__': 1, '__value__': 1},
        'Block': {'name': {'__type__': 8, '__value__': 'minecraft:quartz_block'},
                  'states': {'pillar_axis': {'__type__': 8, '__value__': 'y'}}}}
    actual = copy.deepcopy(original)
    actual['tag'] = {'ench': [{'id': {'__type__': 2, '__value__': 9},
                              'lvl': {'__type__': 2, '__value__': 3}}]}
    return {'source': {'plain_native_item': original}, 'typed_nbt': {'Item': actual},
            'item_api': {'enchantData': [[9, 3]]}}, {'root': {'Item': copy.deepcopy(actual)},
                                                 'enchantments': [[9, 3]]}


def nbt_fixture():
    server, client = native_row()
    probe = {'completed': True, 'passed': True, 'restored': True, 'cleanup_errors': [],
             'fill': {'observed': [server]}, 'client': client}
    cases = [{'source': {'item': ['minecraft:quartz_block', 0]},
              'native_reference': {'fill': {'observed': [copy.deepcopy(server)]},
                                   'client': copy.deepcopy(client)}} for _ in range(3)]
    return probe, cases


class FrameBlockEvidence(unittest.TestCase):
    def test_native_block_must_survive_both_server_and_client_readback(self):
        probe, cases = nbt_fixture()
        self.assertTrue(archive.validate_nbt(probe, cases)['native_block_preserved'])
        cases[1]['native_reference']['client']['root']['Item']['Block']['states']['pillar_axis']['__value__'] = 'x'
        with self.assertRaises(AssertionError):
            archive.validate_nbt(probe, cases)

    def test_pixel_glint_is_not_accepted_by_nbt_readback(self):
        probe, cases = nbt_fixture()
        self.assertFalse(archive.validate_nbt(probe, cases)['pixel_glint_motion_accepted'])
        probe['fill']['observed'][0]['item_api']['enchantData'] = []
        with self.assertRaises(AssertionError):
            archive.validate_nbt(probe, cases)

    def test_redaction_preserves_foreground_guard_identity_and_session_binding(self):
        session = {'id': 'owned', 'owner': 'test', 'session_file': 'session:owned'}
        raw = {'session': {'token': 'secret', 'mcp_url': 'private'}, 'session_file': 'private',
               'guard_before': {'foreground': {'hwnd': 4, 'pid': 8, 'title': 'private', 'identity': 'other'}},
               'capture': {'path': 'private.png', 'token': 'secret'}}
        result = archive.sanitize(raw, session, {'private.png': 'captures/test.png'})
        self.assertNotIn('secret', json.dumps(result))
        self.assertEqual(session, result['session'])
        self.assertEqual('session:owned', result['session_file'])
        self.assertEqual({'hwnd': 4, 'pid': 8}, result['guard_before']['foreground'])
        self.assertEqual('captures/test.png', result['capture']['path'])

    def test_wer_reused_pid_does_not_match_another_process_creation(self):
        template = ('<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">'
            '<System><EventID>1000</EventID></System><EventData>'
            '<Data Name="ProcessId">0x3b28</Data><Data Name="ProcessCreationTime">{}</Data>'
            '<Data Name="IntegratorReportId">exact-report</Data></EventData></Event>')
        process = {'pid': 15144, 'identity': '134365611080856581'}
        right = template.format(hex(int(process['identity'])))
        wrong = template.format(hex(int(process['identity']) + 1))
        self.assertEqual([right], archive.matching_wer([wrong, right], process))

    def test_modified_or_unindexed_pixels_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            pixel = bundle / 'pixel.png'
            pixel.write_bytes(b'original')
            report = bundle / 'report.json'
            report.write_text('{"launch_sources": {}}', encoding='ascii')
            manifest = {'files': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (pixel, report)}, 'source_subset': {}}
            archive.write_json(bundle / 'manifest.json', manifest)
            archive.verify_files(bundle)
            pixel.write_bytes(b'changed')
            with self.assertRaises(AssertionError):
                archive.verify_files(bundle)
            pixel.write_bytes(b'original')
            (bundle / 'unindexed.png').write_bytes(b'new')
            with self.assertRaises(AssertionError):
                archive.verify_files(bundle)
            with self.assertRaises(ValueError):
                archive.contained(bundle, '../escape.png')


if __name__ == '__main__':
    unittest.main()

"""The unattended recovery must reject other dialogs and unrelated processes."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dismiss_owned_disabled_skin_assert import known_disabled_skin_assertion
from watch_owned_disabled_skin_assert_r20 import assigned, eligible


class DisabledSkinWatchTests(unittest.TestCase):
    def test_only_explicit_assignment_prefixes_extend_to_next_cold_instance(self):
        self.assertTrue(assigned('portal-r20-native-v4', ['portal-r20-native-*']))
        self.assertFalse(assigned('user-game', ['portal-r20-native-*']))
        self.assertFalse(assigned('portal-r19-native-v4', ['portal-r20-native-*']))
        self.assertFalse(assigned('user-game', ['*']))
        self.assertFalse(assigned(None, ['portal-r20-native-*']))

    def test_only_the_specific_engine_assertion_matches(self):
        text = ('The disabled skin popup has been displayed but the level data has no disabled cosmetics\n'
                'DisabledSkinScreenController::onEntered(void)\nDisabledSkinScreenController.cpp @ 47')
        self.assertTrue(known_disabled_skin_assertion({'text': text}))
        self.assertFalse(known_disabled_skin_assertion({'text': text.replace('@ 47', '@ 48')}))
        self.assertFalse(known_disabled_skin_assertion({'text': text.replace('no disabled', 'disabled')}))
        self.assertFalse(known_disabled_skin_assertion({'text': 'Assertion failed in another renderer'}))

    def test_only_explicitly_owned_live_project_instances_are_eligible(self):
        project_root = (ROOT / '.runtime/projects').resolve()
        record = {'owner': 'shield-r20-v1', 'state': 'starting',
                  'project': str(project_root / 'shield-r20-v1'),
                  'game_pid': 11, 'game_identity': 'game-a', 'mcdk_pid': 12, 'mcdk_identity': 'mcdk-a'}
        identities = {11: 'game-a', 12: 'mcdk-a'}
        check = lambda item: eligible(item, ['shield-r20-v1'], project_root, identities.get)
        self.assertTrue(check(record))
        for change in ({'owner': 'user-game'}, {'state': 'stopped'},
                       {'project': str(ROOT)}, {'project': str(project_root) + '-other/clone'},
                       {'game_identity': 'game-reused'}, {'mcdk_identity': 'old-mcdk'},
                       {'game_pid': None}):
            self.assertFalse(check(dict(record, **change)), change)


if __name__ == '__main__':
    unittest.main()

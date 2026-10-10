"""Snow gallery completeness is checked against native observations, not itself."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_snow_blueprints import check


class SnowBlueprintEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        version = cls.manifest['game_version'].removeprefix('NEMC ')
        cls.snapshot = json.loads((ROOT/('tools/data/native_snow_states_nemc_'+version+'.json')).read_text(encoding='utf8'))

    def test_all_native_plants_and_heights_are_public(self):
        result = check(self.snapshot, self.manifest)
        self.assertEqual((29, 232), (result['plants'], result['cases']))

    def test_missing_height_cannot_pass(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['rows'].pop()
        with self.assertRaisesRegex(ValueError, 'do not cover'):
            check(snapshot, self.manifest)

    def test_failed_delayed_readback_cannot_pass(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['rows'][0]['delayed']['back'][0] = 'minecraft:air'
        with self.assertRaisesRegex(ValueError, 'readback differs'):
            check(snapshot, self.manifest)

    def test_unrestored_native_fixture_cannot_pass(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['restored'] = False
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            check(snapshot, self.manifest)


if __name__ == '__main__':
    unittest.main()

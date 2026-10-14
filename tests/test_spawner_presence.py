import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, foreground, rebase
from projection.debug_blueprints import build, material
from projection.debug_spawner_blueprints import CASE_IDS, POSITIONS, observations, source_document
from projection.spawner_presence import EMPTY, PRESENT, UNKNOWN, presence
from projection.visible_actor import compose_actor


class SpawnerPresenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = dict((row['id'], row) for row in observations())

    def test_native_egg_samples_cover_both_families_and_preserve_typed_data(self):
        for row in self.rows.values():
            nbt = row['after_delayed']
            original = copy.deepcopy(nbt)
            expected = EMPTY if row['egg'] is None else PRESENT
            value = material(row['name'], row['states'])
            for actor in (nbt, compose_actor({}, nbt)):
                self.assertEqual(expected, presence(value, actor), row['id'])
            self.assertEqual(original, nbt)
            self.assertNotIn('__repr__', json.dumps(nbt))

    def test_partial_invalid_and_wrong_family_payloads_stay_unknown(self):
        for name, row_id in (('mob_spawner', 'mob_spawner_pig_spawn_egg'),
                             ('trial_spawner', 'trial_spawner_pig_spawn_egg')):
            for payload in (None, {}, {'id': {'__type__': 8, '__value__': 'Chest'}},
                            {'__modern_projection_actor__': 99, 'render': {}, 'nbt': {}},
                            {'id': {'__type__': 3, '__value__': 42}}):
                self.assertEqual(UNKNOWN, presence(material(name), payload))
            nbt = copy.deepcopy(self.rows[row_id]['after_delayed'])
            nbt['id']['__type__'] = 3
            self.assertEqual(UNKNOWN, presence(material(name), nbt))

    def test_custom_identifiers_are_configured_without_an_entity_allowlist(self):
        nbt = copy.deepcopy(self.rows['mob_spawner_empty']['after_delayed'])
        for value in ('example:custom_creature', b'example:custom_creature'):
            nbt['EntityIdentifier']['__value__'] = value
            self.assertEqual(PRESENT, presence(material('mob_spawner'), nbt))
        for value in ('pig', ':pig', 'minecraft:', 'minecraft:pig sheep',
                      'minecraft:pig:extra', b'\xff:pig', 123, False):
            nbt['EntityIdentifier']['__value__'] = value
            self.assertEqual(UNKNOWN, presence(material('mob_spawner'), nbt), value)

    def test_current_mobs_and_spawn_timers_do_not_define_configuration(self):
        nbt = copy.deepcopy(self.rows['trial_spawner_empty']['after_delayed'])
        nbt['current_mobs'] = ['not_a_configured_creature']
        nbt['cooldown_end_at']['__value__'] = 999999
        self.assertEqual(EMPTY, presence(material('trial_spawner'), nbt))
        del nbt['normal_config']['ticks_between_spawn']
        self.assertEqual(UNKNOWN, presence(material('trial_spawner'), nbt))

    def test_malformed_trial_weight_identifier_and_config_are_unknown(self):
        source = self.rows['trial_spawner_pig_spawn_egg']['after_delayed']
        for change in ('negative', 'bool', 'wrong_tag', 'missing_id', 'bad_list', 'contradiction'):
            nbt = copy.deepcopy(source)
            if change == 'negative':
                nbt['spawn_data']['Weight']['__value__'] = -1
            elif change == 'bool':
                nbt['spawn_data']['Weight']['__value__'] = True
            elif change == 'wrong_tag':
                nbt['spawn_data']['TypeId']['__type__'] = 3
            elif change == 'missing_id':
                del nbt['normal_config']['spawn_potentials'][0]['data']['entity']['id']
            elif change == 'bad_list':
                nbt['normal_config']['spawn_potentials'] = {}
            else:
                nbt['normal_config']['spawn_potentials'] = []
            self.assertEqual(UNKNOWN, presence(material('trial_spawner'), nbt), change)

    def test_ominous_material_selects_ominous_configuration(self):
        nbt = copy.deepcopy(self.rows['trial_spawner_pig_spawn_egg']['after_delayed'])
        nbt['normal_config']['spawn_potentials'] = []
        self.assertEqual(UNKNOWN, presence(material('trial_spawner'), nbt))
        self.assertEqual(PRESENT, presence(material('trial_spawner', {'ominous': True}), nbt))

    def test_unrelated_nbt_and_blocks_do_not_get_markers(self):
        self.assertIsNone(presence(material('chest'), self.rows['mob_spawner_empty']['after_delayed']))

    def test_public_cases_rebase_native_nbt_and_preserve_unknown(self):
        doc = build('test.entities.spawners')
        for identity, position in zip(CASE_IDS, POSITIONS):
            cell = doc.get(position)
            expected = UNKNOWN if identity.endswith('unknown') else EMPTY if identity.endswith('empty') else PRESENT
            self.assertEqual(expected, presence(foreground(cell), actor_data(cell)), identity)
            if not identity.endswith('unknown'):
                root = actor_data(cell)['nbt']
                self.assertEqual(position, tuple(root[axis]['__value__'] for axis in ('x', 'y', 'z')))

    def test_isolated_pixel_cases_preserve_public_cells_and_native_payloads(self):
        gallery = build('test.entities.spawners')
        before = copy.deepcopy(gallery.to_data())
        for identity, position in zip(CASE_IDS, POSITIONS):
            document = source_document(identity)
            delta = tuple(3 - position[axis] for axis in range(3))
            self.assertEqual((8, 8, 8), document.size)
            self.assertEqual(rebase(gallery.get(position), delta), document.get((3, 3, 3)))
            self.assertEqual(2, len(document.blocks))
            if not identity.endswith('unknown'):
                root = actor_data(document.get((3, 3, 3)))['nbt']
                self.assertEqual((3, 3, 3), tuple(root[axis]['__value__'] for axis in ('x', 'y', 'z')))
        self.assertEqual(before, gallery.to_data())
        with self.assertRaises(ValueError):
            source_document('arbitrary_fixture')


if __name__ == '__main__':
    unittest.main()

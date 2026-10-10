"""Decorated-pot visual directions follow state operations, preserving artwork."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.native_pot import native_pot_actor
from projection.state_transform import transform
from projection.geometry_palette import prepare_palette
from projection.visible_actor import compose_actor


class NativePotTests(unittest.TestCase):
    def test_every_observed_native_direction_matches_exact_renderer(self):
        data=json.loads((ROOT/'tools/data/native_pot_poses_nemc_3.9.0.401155.json').read_text())
        for row in data['observations']:
            self.assertEqual(row['actor'],native_pot_actor(tuple(row['material']),None))

    def test_rotations_and_mirrors_refresh_direction_and_keep_all_shred_names(self):
        source={'direction':0,'decoratedPotShredNamesSize':4,
                'decoratedPotShredNames0':'angler_pottery_sherd',
                'decoratedPotShredNames1':'archer_pottery_sherd',
                'decoratedPotShredNames2':'arms_up_pottery_sherd',
                'decoratedPotShredNames3':'blade_pottery_sherd','foreign':{'x':7}}
        before=copy.deepcopy(source)
        for aux in registry.aux_values('minecraft:decorated_pot'):
            for operation in ('rotate_y90','rotate_y180','rotate_y270','mirror_x','mirror_y','mirror_z'):
                value=transform(('minecraft:decorated_pot',aux),operation)
                result=native_pot_actor(value,source)
                self.assertEqual(registry.states(value)['direction'],result['direction'])
                for key in source:
                    if key!='direction':self.assertEqual(source[key],result[key])
                result['foreign']['x']=8
                self.assertEqual(before,source)

    def test_byte_direction_key_and_unknown_material_are_preserved(self):
        result=native_pot_actor(('minecraft:decorated_pot',2),{b'direction':0})
        self.assertEqual(registry.states(('minecraft:decorated_pot',2))['direction'],result[b'direction'])
        self.assertNotIn('direction',result)
        self.assertIsNone(native_pot_actor(('minecraft:stone',0),{}))

    def test_production_palette_refreshes_pose_without_altering_artwork(self):
        material = ('minecraft:decorated_pot', 2)
        renderer = {'direction': 0, 'decoratedPotShredNames0': 'angler_pottery_sherd'}
        source = {'volume': (1, 1, 1), 'common': {material: [0]},
                  'actor': {material[0]: {0: compose_actor(renderer, None)}}}
        before = copy.deepcopy(source)
        actual = prepare_palette(source)['actor'][material[0]][0]
        self.assertEqual(registry.states(material)['direction'], actual['direction'])
        self.assertEqual('angler_pottery_sherd', actual['decoratedPotShredNames0'])
        self.assertEqual(before, source)

    def test_other_registry_requires_new_observations(self):
        with patch.object(registry,'fingerprint',return_value='future'):
            with self.assertRaisesRegex(ValueError,'observations'):
                native_pot_actor(('minecraft:decorated_pot',0),None)


if __name__=='__main__':
    unittest.main()

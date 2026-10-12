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
from projection.cell import actor_data, foreground
from projection.debug_blueprints import build, VISUAL_CASES
from projection.entity_render import native_actor
from projection import native_pot_data, native_pot_sherd_data


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

    def test_pose_and_sherd_sources_are_independently_version_guarded(self):
        actor = compose_actor({'direction': 0, 'foreign': {'value': 7}}, None)
        before = copy.deepcopy(actor)
        for source in (native_pot_data, native_pot_sherd_data):
            for field, changed in (('SCHEMA_VERSION', 2), ('SOURCE_VERSION', 'NEMC next'),
                                   ('PALETTE_SHA256', '0' * 64)):
                with self.subTest(source=source.__name__, field=field):
                    with patch.object(source, field, changed):
                        with self.assertRaisesRegex(ValueError, 'observations'):
                            native_pot_actor(('minecraft:decorated_pot', 0), None, actor)
                    self.assertEqual(before, actor)

    def test_full_nbt_alone_rebuilds_each_observed_nondefault_renderer(self):
        data = json.loads((ROOT / 'tools/data/native_pot_sherds_nemc_3.9.0.401155.json').read_text())
        for row in data['rows']:
            actor = compose_actor({}, copy.deepcopy(row['nbt']))
            before = copy.deepcopy(actor)
            material = ('minecraft:decorated_pot', row['aux'])
            self.assertEqual(row['client']['actor'], native_pot_actor(material, {}, actor))
            source = {'volume': (1, 1, 1), 'common': {material: [0]},
                      'actor': {material[0]: {0: actor}}}
            self.assertEqual(row['client']['actor'], prepare_palette(source)['actor'][material[0]][0])
            self.assertEqual(before, actor)

    def test_invalid_sherd_payload_keeps_client_artwork_without_partial_overwrite(self):
        material = ('minecraft:decorated_pot', 0)
        renderer = {'decoratedPotShredNames0': 'minecraft:angler_pottery_sherd'}
        for sherds in ([], [{'__type__': 3, '__value__': 'minecraft:brick'}] * 4,
                       [{'__type__': 8, '__value__': 'minecraft:brick'}] * 3 + [None]):
            actor = compose_actor(renderer, {'id': {'__type__': 8, '__value__': 'DecoratedPot'},
                                             'sherds': sherds})
            before = copy.deepcopy(actor)
            result = native_pot_actor(material, renderer, actor)
            self.assertEqual('minecraft:angler_pottery_sherd', result['decoratedPotShredNames0'])
            self.assertEqual('', result['decoratedPotShredNames1'])
            self.assertEqual(before, actor)

    def test_public_pottery_cases_use_full_nbt_without_cached_renderer_fields(self):
        from projection.debug_pot_blueprints import SHERDS
        case = VISUAL_CASES['pot_artwork']
        document = build(case['fixture'])
        self.assertEqual(4, len(case['cases']))
        for row in case['cases']:
            value = document.get(row['position'])
            renderer = native_actor(foreground(value), actor_data(value))
            self.assertEqual(row['direction'], renderer['direction'])
            self.assertEqual(list(SHERDS), [renderer['decoratedPotShredNames' + str(index)]
                                          for index in range(4)])


if __name__=='__main__':
    unittest.main()

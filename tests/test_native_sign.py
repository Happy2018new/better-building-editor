"""Native sign pose observations and NBT text/style keep independent sources."""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.native_sign import native_sign_actor
from projection.native_sign_data import TEMPLATES
from projection.visible_actor import compose_actor
from projection.geometry_palette import prepare_palette


def tag(kind,value):
    return {'__type__':kind,'__value__':value}


class NativeSignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads((ROOT/'tools/data/native_signs_nemc_3.9.0.401155.json').read_text())

    def test_every_observed_pose_matches_native_actor(self):
        for row in self.evidence['poses']:
            with self.subTest(material=row['material']):
                self.assertEqual(row['actor'],native_sign_actor(tuple(row['material']),None,None))

    def test_every_observed_two_sided_style_matches_and_never_mutates_nbt(self):
        for row in self.evidence['styles']:
            actor=copy.deepcopy(row['nbt'])
            before=copy.deepcopy(actor)
            self.assertEqual(row['actor'],native_sign_actor(tuple(row['material']),actor,None))
            self.assertEqual(before,actor)

    def test_production_palette_applies_observed_two_sided_text(self):
        for row in self.evidence['styles']:
            material = tuple(row['material'])
            source = {'volume': (1, 1, 1), 'common': {material: [0]},
                      'actor': {material[0]: {0: compose_actor({}, row['nbt'])}}}
            before = copy.deepcopy(source)
            rendered = prepare_palette(source)
            self.assertEqual(row['actor'], rendered['actor'][material[0]][0])
            self.assertEqual(before, source)

    def test_all_species_states_produce_known_native_pose_fields(self):
        count=0
        for name in TEMPLATES:
            for aux in registry.aux_values(name):
                state=registry.states((name,aux))
                actor=native_sign_actor((name,aux),None,None)
                self.assertEqual(TEMPLATES[name]['signType'],actor['signType'])
                if 'ground_sign_direction' in state:self.assertEqual(state['ground_sign_direction'],actor['signStandingRotation'])
                if 'facing_direction' in state:self.assertEqual(state['facing_direction'],actor['facingDirection'])
                if 'hanging' in state:
                    self.assertEqual(not state['hanging'],actor['signHangingSignBit'])
                    self.assertEqual(state['hanging'] and state['attached_bit'],actor['signAttachedSignBit'])
                count+=1
        self.assertEqual(4872,count)

    def test_byte_keys_unknown_render_fields_and_nested_tags_are_preserved(self):
        nbt={b'id':tag(8,b'Sign'),b'FrontText':{b'Text':tag(8,b'Hello'),b'unknown':tag(10,{b'x':tag(3,8)})}}
        renderer={b'signRealText':b'old',b'foreign':{'x':4}}
        source=compose_actor(renderer,nbt)
        before=copy.deepcopy(source)
        result=native_sign_actor(('minecraft:standing_sign',5),source,renderer)
        self.assertEqual(b'Hello',result[b'signRealText'])
        self.assertNotIn('signRealText',result)
        self.assertEqual({'x':4},result[b'foreign'])
        result[b'foreign']['x']=8
        self.assertEqual(before,source)

    def test_invalid_known_tags_do_not_overwrite_visible_values(self):
        renderer={'signRealText':'old','signColor':17,'signGlowing':True}
        nbt={'id':tag(8,'Sign'),'FrontText':{'Text':tag(3,1),
             'SignTextColor':tag(3,2147483648),'IgnoreLighting':tag(1,2)}}
        result=native_sign_actor(('minecraft:standing_sign',0),nbt,renderer)
        for key in renderer:self.assertEqual(renderer[key],result[key])

    def test_unknown_entities_cannot_change_sign_text(self):
        renderer={'signRealText':'keep'}
        nbt={'id':tag(8,'FutureSign'),'FrontText':{'Text':tag(8,'unknown')}}
        self.assertEqual('keep',native_sign_actor(('minecraft:standing_sign',0),nbt,renderer)['signRealText'])
        self.assertIsNone(native_sign_actor(('minecraft:stone',0),nbt,renderer))

    def test_other_registry_requires_a_new_observation(self):
        with patch.object(registry,'fingerprint',return_value='future'):
            with self.assertRaisesRegex(ValueError,'observations'):
                native_sign_actor(('minecraft:standing_sign',0),None,None)


if __name__=='__main__':
    unittest.main()

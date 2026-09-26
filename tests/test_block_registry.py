"""Native states, compatibility boundaries and generated data coverage."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack/modern_projection'))
from projection import block_registry as registry


class BlockRegistryTests(unittest.TestCase):
    def test_every_shipped_record_is_valid_and_typed(self):
        count=0
        for name in registry.BLOCKS:
            for aux in registry.aux_values(name):
                value=(name,aux)
                self.assertEqual(value,registry.canonical(value))
                states=registry.states(value)
                self.assertIsInstance(states,dict)
                self.assertTrue(all(type(v) in (str,int,bool) for v in states.values()))
                count+=1
        self.assertEqual(15839,count)
        self.assertEqual(1321,len(registry.BLOCKS))

    def test_source_file_matches_every_name_aux_and_typed_state(self):
        path=Path('C:/Users/Happy2018new/AppData/Roaming/MinecraftPE_Netease/logs/block_palette.json')
        if not path.exists():self.skipTest('Native source export is external; shipped coverage is tested separately')
        raw=path.read_bytes()
        self.assertEqual(registry.SOURCE_SHA256,hashlib.sha256(raw).hexdigest())
        for row in json.loads(raw)['blocks']:
            expected={s['name']:bool(s['value']) if s['type']=='byte' else s['value'] for s in row['states']}
            actual=registry.states((row['name'],row['data']))
            self.assertEqual(expected,actual)
            self.assertEqual({k:type(v) for k,v in expected.items()},{k:type(v) for k,v in actual.items()})

    def test_legacy_colors_wood_axes_slab_half_and_modern_priority(self):
        self.assertEqual(('minecraft:cyan_stained_glass',0),registry.canonical(('minecraft:stained_glass',9)))
        for family in ('stained_glass','stained_glass_pane','wool','concrete','concrete_powder','carpet'):
            resolved=[registry.canonical(('minecraft:'+family,i)) for i in range(16)]
            self.assertEqual(16,len(set(resolved)))
        for aux,axis in ((1,'y'),(5,'x'),(9,'z')):
            self.assertEqual({'pillar_axis':axis},registry.states(('minecraft:log',aux)))
        for aux in range(6):
            self.assertEqual('bottom',registry.states(('minecraft:wooden_slab',aux))['minecraft:vertical_half'])
            self.assertEqual('top',registry.states(('minecraft:wooden_slab',aux+8))['minecraft:vertical_half'])
            self.assertIn('_double_slab',registry.canonical(('minecraft:double_wooden_slab',aux))[0])
        self.assertEqual(('minecraft:chipped_anvil',1),registry.canonical(('minecraft:anvil',5)))
        self.assertEqual(('minecraft:quartz_block',1),registry.canonical(('minecraft:quartz_block',1)))
        self.assertEqual({'pillar_axis':'x'},registry.states(('minecraft:quartz_block',1)))
        self.assertEqual({'upside_down_bit':True,'weirdo_direction':1},registry.states(('minecraft:oak_stairs',5)))
        self.assertEqual(('custom:future',7),registry.canonical(('custom:future',7)))
        self.assertIsNone(registry.states(('custom:future',7)))
        with self.assertRaises(ValueError):registry.canonical(('minecraft:cyan_stained_glass',32767))

    def test_catalogue_and_aux_steps_only_offer_native_values(self):
        catalogue=registry.catalogue_values()
        self.assertEqual(1321,len(catalogue))
        self.assertNotIn(('minecraft:stained_glass',9),catalogue)
        self.assertIn(('minecraft:cyan_stained_glass',0),catalogue)
        self.assertEqual(('minecraft:oak_log',2),registry.next_aux(('minecraft:oak_log',1),1))
        self.assertEqual(('minecraft:oak_log',2),registry.next_aux(('minecraft:oak_log',2),1))

    def test_aux_input_rejects_nonexistent_modern_states(self):
        from projection.materials import with_aux
        self.assertEqual(('minecraft:oak_log',2),with_aux(('minecraft:oak_log',0),'2'))
        with self.assertRaises(ValueError):with_aux(('minecraft:cyan_stained_glass',0),'9')
        with self.assertRaises(ValueError):with_aux(('minecraft:stone',0),'1')
        self.assertEqual(('custom:future',9),with_aux(('custom:future',0),'9'))

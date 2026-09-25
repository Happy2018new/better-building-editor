"""Static contracts for the two staff attachables and the bounded aura actor."""
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class AstralStaffTests(unittest.TestCase):
    def test_both_items_have_bound_staff_geometry_and_animated_gems(self):
        for kind in ('terminal', 'survey_wand'):
            attachable = json.loads((ROOT / ('resource_pack/attachables/modern_projection_%s.json' % kind)).read_text(encoding='utf8'))
            desc = attachable['minecraft:attachable']['description']
            self.assertEqual('geometry.modern_projection_' + kind, desc['geometry']['default'])
            self.assertIn('gem', desc['materials'])
            animation = json.loads((ROOT / ('resource_pack/animations/modern_projection_%s.animation.json' % kind)).read_text(encoding='utf8'))
            bones = animation['animations']['animation.modern_projection_%s.holding' % kind]['bones']
            self.assertGreaterEqual(len([name for name in bones if name.startswith('gem')]), 7)
            self.assertTrue(any('q.life_time' in str(value) for value in bones.values()))

    def test_staff_custom_material_shaders_resolve(self):
        material = json.loads((ROOT / 'resource_pack/materials/entity.material').read_text(encoding='utf8'))['materials']
        by_name = dict((key.split(':')[0],value) for key,value in material.items())
        for kind in ('terminal','survey_wand'):
            desc=json.loads((ROOT/('resource_pack/attachables/modern_projection_%s.json'%kind)).read_text())['minecraft:attachable']['description']
            self.assertIn(desc['materials']['gem'],by_name)
        for key,value in material.items():
            if 'staff' in key:
                for field in ('vertexShader','fragmentShader'):
                    if field in value:
                        self.assertTrue((ROOT/'resource_pack'/value[field]).is_file())

    def test_aura_has_six_effect_ranges_and_shader_materials(self):
        geometry = json.loads((ROOT / 'resource_pack/models/entity/modern_projection_staff_aura.geo.json').read_text(encoding='utf8'))
        bones = geometry['minecraft:geometry'][0]['bones']
        self.assertEqual(['root', 'crystals', 'glow'], [bone['name'] for bone in bones])
        self.assertLessEqual(sum(len(b.get('cubes',[])) for b in bones),768)
        behavior = json.loads((ROOT / 'behavior_pack/entities/modern_projection_staff_aura.json').read_text(encoding='utf8'))
        self.assertFalse(behavior['minecraft:entity']['components']['minecraft:physics']['has_collision'])


sys.path.insert(0,str(ROOT/'behavior_pack'))
from HelloScript.projection.staff_aura import StaffAura
from HelloScript.projection.tool_items import TERMINAL, SURVEY_WAND


class AuraLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.live=set()
        self.uploads=[]
        self.pos=(1.,64.,2.)
        self.callbacks=[]
        self.clock=patch('HelloScript.projection.staff_aura.time.time',return_value=10.)
        self.now=self.clock.start()
        self.addCleanup(self.clock.stop)
        def spawn(kind,pos,rot):
            entity='aura'+str(len(self.live))
            self.live.add(entity)
            return entity
        def uniform(slot,value):
            self.uploads.append(value)
            return True
        self.bridge=types.SimpleNamespace(player='player',session=types.SimpleNamespace(reduced_motion=False),
            system=types.SimpleNamespace(CreateClientEntityByTypeStr=spawn,DestroyClientEntity=self.live.remove),
            factory=types.SimpleNamespace(
                CreatePos=lambda entity:types.SimpleNamespace(GetFootPos=lambda:self.pos,SetPosForClientEntity=lambda pos:True),
                CreateModel=lambda entity:types.SimpleNamespace(SetEntityShadowShow=lambda value:True),
                CreateActorRender=lambda entity:types.SimpleNamespace(SetEntityExtraUniforms=uniform)),
            later=lambda delay,callback:self.callbacks.append(callback))
        self.aura=StaffAura(self.bridge)

    def test_switch_staff_reuses_actor_and_empty_hand_cleans_up(self):
        self.aura.update(TERMINAL)
        actor=self.aura.entity
        self.now.return_value=12.
        self.aura.update(TERMINAL)
        self.uploads[:]=[]
        for unused in range(30):self.aura.update(TERMINAL)
        self.assertFalse(self.uploads)
        self.pos=(2.,64.,3.)
        self.aura.update(SURVEY_WAND)
        self.assertEqual(actor,self.aura.entity)
        self.assertEqual(self.pos,self.aura.position)
        self.assertEqual(1,len(self.live))
        self.aura.update(None)
        for callback in self.callbacks:callback()
        self.assertFalse(self.live)
        self.assertIsNone(self.aura.uniform)

    def test_menu_and_dimension_cleanup_do_not_respawn_from_delayed_callback(self):
        self.aura.update(TERMINAL)
        self.aura.update(TERMINAL,False)
        for callback in self.callbacks:callback()
        self.assertFalse(self.live)
        self.aura.update(TERMINAL)
        self.aura.clear()
        self.aura.clear()
        self.assertFalse(self.live)

    def test_reduced_motion_freezes_shader_clock(self):
        self.bridge.session.reduced_motion=True
        self.aura.update(TERMINAL)
        self.assertEqual(0.,self.uploads[-1][2])


if __name__ == '__main__':
    unittest.main()

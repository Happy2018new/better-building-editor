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
            self.assertIn('grip', desc['materials'])
            self.assertIn('motes', desc['materials'])
            animation = json.loads((ROOT / ('resource_pack/animations/modern_projection_%s.animation.json' % kind)).read_text(encoding='utf8'))
            bones = animation['animations']['animation.modern_projection_%s.holding' % kind]['bones']
            self.assertGreaterEqual(len([name for name in bones if name.startswith('gem')]), 7)
            self.assertIn('motes', bones)
            self.assertIn('q.life_time', str(bones['motes']))
            geometry = json.loads((ROOT / ('resource_pack/models/entity/modern_projection_%s.geo.json' % kind)).read_text(encoding='utf8'))
            model_bones = {bone['name']: bone for bone in geometry['minecraft:geometry'][0]['bones']}
            self.assertIn('grip', model_bones)
            motes = model_bones['motes']['cubes']
            self.assertGreaterEqual(len(motes), 40)
            self.assertGreater(max(c['origin'][1] for c in motes) - min(c['origin'][1] for c in motes), 20)
            self.assertTrue(any('q.life_time' in str(value) for value in bones.values()))

    def test_terminal_has_no_extra_blue_head_blocks(self):
        def body(kind):
            path=ROOT/('resource_pack/models/entity/modern_projection_%s.geo.json'%kind)
            return json.loads(path.read_text())['minecraft:geometry'][0]['bones'][0]['cubes']
        self.assertEqual(body('survey_wand'),body('terminal'))
        for kind in ('terminal','survey_wand'):
            path=ROOT/('resource_pack/animations/modern_projection_%s.animation.json'%kind)
            bones=json.loads(path.read_text())['animations']['animation.modern_projection_%s.holding'%kind]['bones']
            staff=bones['staff']
            self.assertEqual('c.is_first_person ? 18.0 : 24.0',staff['position'][1])
            self.assertEqual('c.is_first_person ? 27.0 : 75.0',staff['rotation'][0])
            self.assertEqual('c.is_first_person ? -159.0 : 0.0',staff['rotation'][2])
            self.assertEqual('c.is_first_person ? 0.62 : 0.85',staff['scale'])

    def test_staff_custom_material_shaders_resolve(self):
        material = json.loads((ROOT / 'resource_pack/materials/entity.material').read_text(encoding='utf8'))['materials']
        by_name = dict((key.split(':')[0],value) for key,value in material.items())
        for kind in ('terminal','survey_wand'):
            desc=json.loads((ROOT/('resource_pack/attachables/modern_projection_%s.json'%kind)).read_text())['minecraft:attachable']['description']
            self.assertIn(desc['materials']['gem'],by_name)
            self.assertIn(desc['materials']['grip'],by_name)
            self.assertIn(desc['materials']['motes'],by_name)
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
from modern_projection.projection.staff_aura import StaffAura, NearbyStaffAuras
from modern_projection.projection.tool_items import TERMINAL, SURVEY_WAND


class AuraLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.live=set()
        self.uploads=[]
        self.positions=[]
        self.perspective=1
        self.pos=(1.,64.,2.)
        self.callbacks=[]
        self.clock=patch('modern_projection.projection.staff_aura.time.time',return_value=10.)
        self.now=self.clock.start()
        self.addCleanup(self.clock.stop)
        def spawn(kind,pos,rot):
            entity='aura'+str(len(self.live))
            self.live.add(entity)
            return entity
        def uniform(slot,value):
            self.uploads.append((slot,value))
            return True
        self.bridge=types.SimpleNamespace(player='player',session=types.SimpleNamespace(reduced_motion=False),
            system=types.SimpleNamespace(CreateClientEntityByTypeStr=spawn,DestroyClientEntity=self.live.remove),
            factory=types.SimpleNamespace(
                CreatePos=lambda entity:types.SimpleNamespace(GetFootPos=lambda:self.pos,SetPosForClientEntity=lambda pos:self.positions.append(pos) or True),
                CreateModel=lambda entity:types.SimpleNamespace(SetEntityShadowShow=lambda value:True),
                CreateActorRender=lambda entity:types.SimpleNamespace(SetEntityExtraUniforms=uniform)),
            later=lambda delay,callback:self.callbacks.append(callback))
        self.bridge.factory.CreatePlayerView=lambda entity:types.SimpleNamespace(GetPerspective=lambda:self.perspective)
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
        self.assertEqual(0.,dict(self.uploads)[3][2])
        self.now.return_value=12.15
        self.aura.update(SURVEY_WAND)
        self.assertGreater(self.aura.position[0],1.)
        self.assertLessEqual(self.aura.position[0],self.pos[0])
        self.assertNotEqual(self.aura.layout_from,self.aura.layout_to)
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
        self.assertEqual(0.,dict(self.uploads)[1][2])

    def test_motion_trail_decays_and_teleport_does_not_streak(self):
        self.aura.update(TERMINAL)
        self.now.return_value=10.05
        self.pos=(1.2,64.,2.)
        self.aura.update(TERMINAL)
        self.now.return_value=10.1
        self.aura.update(TERMINAL)
        self.assertGreater(dict(self.uploads)[2][3],0.)
        self.now.return_value=10.15
        self.pos=(40.,64.,2.)
        self.aura.update(TERMINAL)
        self.assertEqual(self.pos,self.aura.position)
        self.assertEqual(0.,dict(self.uploads)[2][3])

    def test_stepped_foot_samples_form_a_continuous_path(self):
        self.aura.update(TERMINAL)
        visual = []
        for frame in range(1, 22):
            self.now.return_value = 10. + frame * .025
            self.pos = (1. + (frame // 2) * .13, 64., 2.)
            self.aura.update(TERMINAL)
            visual.append(self.aura.position[0])
        steps = [visual[i] - visual[i - 1] for i in range(1, len(visual))]
        self.assertGreater(visual[-1], 1.8)
        self.assertTrue(all(step >= 0. for step in steps))
        self.assertLess(max(steps), .10)

    def test_running_turn_has_bounded_inertia_and_settles(self):
        self.aura.update(TERMINAL)
        for frame in range(1, 21):
            self.now.return_value = 10. + frame * .05
            self.pos = (1. + frame * .2, 64., 2.)
            self.aura.update(TERMINAL)
        self.assertLess(self.aura.position[0], self.pos[0])
        self.assertLessEqual(self.pos[0] - self.aura.position[0], .801)
        before_turn = self.aura.position[0]
        self.now.return_value = 11.05
        self.pos = (4.8, 64., 2.)
        self.aura.update(TERMINAL)
        self.assertGreater(self.aura.position[0], before_turn)
        for frame in range(2, 32):
            self.now.return_value = 11. + frame * .05
            self.aura.update(TERMINAL)
        self.assertAlmostEqual(self.pos[0], self.aura.position[0], places=4)
        self.assertLess(self.aura.motion_uniform[3], .01)

    def test_perspective_changes_hide_only_owners_trails(self):
        remote = StaffAura(self.bridge, 'other_player')
        self.addCleanup(remote.clear)
        for perspective, visible in ((0, 0.), (1, 1.), (2, 1.), (0, 0.)):
            self.perspective=perspective
            self.aura.update(TERMINAL)
            remote.update(SURVEY_WAND)
            self.assertEqual(visible,self.aura.uniform[3])
            self.assertEqual(1.,remote.uniform[3])

    def test_nearby_staff_holders_switch_leave_and_unload(self):
        manager=NearbyStaffAuras(self.bridge)
        self.addCleanup(manager.clear)
        manager.sync({'player':TERMINAL,'other_player':SURVEY_WAND})
        manager.update()
        self.assertEqual(['other_player'],list(manager.auras))
        actor=manager.auras['other_player'].entity
        manager.sync({'player':TERMINAL,'other_player':TERMINAL})
        manager.update()
        self.assertEqual(actor,manager.auras['other_player'].entity)
        self.assertEqual(TERMINAL,manager.auras['other_player'].carried)
        # A render tick where an entity unloads must clear its visual at once,
        # even before the slower equipment scan runs.
        self.pos=None
        manager.update()
        self.assertFalse(self.live)
        manager.sync({'player':TERMINAL})
        self.assertFalse(manager.auras)
        self.pos=(1.,64.,2.)
        manager.sync({'other_player':SURVEY_WAND})
        manager.update()
        self.assertEqual(1,len(self.live))
        manager.sync({'other_player':'minecraft:stick'})
        self.assertFalse(self.live)
        self.assertFalse(manager.auras)


if __name__ == '__main__':
    unittest.main()

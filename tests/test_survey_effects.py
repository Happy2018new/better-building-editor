"""Survey VFX stay bounded, local and stable while the camera moves."""
import sys
import json
import math
import struct
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'behavior_pack'))
from HelloScript.projection.survey_effects import SurveyEffects

ROOT = Path(__file__).resolve().parents[1]


class SurveyAssetTests(unittest.TestCase):
    def test_encoded_particles_survive_axis_mirroring_and_mobile_half_precision(self):
        for kind, count in [('stars',3072),('strike',320)]:
            path=ROOT/('resource_pack/models/entity/modern_projection_survey_'+kind+'.geo.json')
            cubes=json.loads(path.read_text())['minecraft:geometry'][0]['bones'][0]['cubes']
            self.assertEqual(count,len(cubes))
            for expected,cube in enumerate(cubes):
                for sign_x,sign_y in [(1,1),(-1,1),(1,-1),(-1,-1)]:
                    for corner_x,corner_y in [(0,0),(0,1),(1,0),(1,1)]:
                        p=[(cube['origin'][axis]+corner)*sign for axis,corner,sign in
                           [(0,corner_x,sign_x),(1,corner_y,sign_y)]]
                        p=[struct.unpack('e',struct.pack('e',value))[0] for value in p]
                        address=[math.floor((abs(value)+1.)/4.) for value in p]
                        self.assertEqual(expected,address[0]+address[1]*64)
                        self.assertEqual([1.,1.],[abs((value-math.copysign(1.,value)*cell*4.)*2.)
                            for value,cell in zip(p,address)])

    def test_private_effect_resources_have_no_collision_and_resolve_materials(self):
        materials=json.loads((ROOT/'resource_pack/materials/entity.material').read_text())['materials']
        for kind in ('wire','veil','stars','strike'):
            name='modern_projection_survey_'+kind
            bp=json.loads((ROOT/('behavior_pack/entities/'+name+'.json')).read_text())['minecraft:entity']
            self.assertFalse(bp['components']['minecraft:physics']['has_collision'])
            self.assertFalse(bp['components']['minecraft:physics']['has_gravity'])
            self.assertFalse(bp['description']['is_spawnable'])
            rp=json.loads((ROOT/('resource_pack/entity/'+name+'.entity.json')).read_text())['minecraft:client_entity']['description']
            self.assertEqual(bp['description']['identifier'],rp['identifier'])
            self.assertTrue(any(key.split(':')[0]==rp['materials']['default'] for key in materials))


class SurveyEffectTests(unittest.TestCase):
    def setUp(self):
        self.live = set()
        self.next_id = 0
        self.uniforms = {}
        self.positions = {}
        self.callbacks = []
        def create(kind, pos, rotation):
            self.next_id += 1
            self.live.add(self.next_id)
            return self.next_id
        def uniforms(entity, slot, value):
            self.uniforms[(entity,slot)] = value
            return True
        def move(entity, pos):
            self.positions[entity] = pos
            return True
        bridge = types.SimpleNamespace(system=types.SimpleNamespace(
            CreateClientEntityByTypeStr=create,DestroyClientEntity=self.live.remove),
            factory=types.SimpleNamespace(
                CreateModel=lambda entity:types.SimpleNamespace(SetEntityShadowShow=lambda value:True),
                CreateActorRender=lambda entity:types.SimpleNamespace(SetEntityExtraUniforms=lambda slot,value:uniforms(entity,slot,value)),
                CreatePos=lambda entity:types.SimpleNamespace(SetPosForClientEntity=lambda pos:move(entity,pos))),
            later=lambda delay,callback:self.callbacks.append(callback))
        self.effect = SurveyEffects(bridge)

    def test_large_box_moves_culling_anchor_without_rebuilding_or_moving_visual_bounds(self):
        self.effect.replace((10,64,20),(64,128,64))
        ids = set(self.live)
        self.effect.follow((1.,2.,3.))
        self.effect.replace((10,64,20),(64,128,64))
        self.assertEqual(ids,self.live)
        for entity in ids:
            self.assertEqual((64.,128.,64.,1.),self.uniforms[(entity,1)])
            self.assertEqual((41.,126.,49.,1.),self.uniforms[(entity,2)])
        self.effect.clear()
        for callback in self.callbacks: callback()
        self.assertFalse(self.live)

    def test_fast_clicks_bound_actors_and_release_every_comet(self):
        self.effect.replace((0,0,0),(1,1,1))
        with patch('HelloScript.projection.survey_effects.time.time',return_value=10.):
            for unused in range(20): self.effect.strike((1,2,3))
        self.assertEqual(6,len(self.live))
        with patch('HelloScript.projection.survey_effects.time.time',return_value=12.):
            self.effect.follow((0.,0.,0.))
        self.assertEqual(3,len(self.live))
        self.effect.clear()
        self.assertFalse(self.live)


if __name__=='__main__': unittest.main()

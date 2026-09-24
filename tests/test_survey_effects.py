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
from HelloScript.projection.survey_effects import SurveyEffects, WireEffects
from HelloScript.projection.outline_settings import defaults, normalize

ROOT = Path(__file__).resolve().parents[1]


class SurveyAssetTests(unittest.TestCase):
    def test_luminous_rails_share_rainbow_geometry_and_depth_pass(self):
        materials=json.loads((ROOT/'resource_pack/materials/entity.material').read_text())['materials']
        rainbow=materials['modern_projection_outline:entity_static']
        wire=materials['modern_projection_survey_wire:entity_static']
        self.assertEqual(rainbow['+states'],wire['+states'])
        self.assertEqual(rainbow['vertexShader'],wire['vertexShader'])
        for name in ('outline','survey_wire'):
            entity=json.loads((ROOT/('resource_pack/entity/modern_projection_'+name+'.entity.json')).read_text())
            self.assertEqual('geometry.modern_projection.outline',entity['minecraft:client_entity']['description']['geometry']['default'])

    def test_encoded_particles_survive_axis_mirroring_and_mobile_half_precision(self):
        for kind, count in [('wire',576),('guide',576),('stars',2560),('strike',512)]:
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
        for kind in ('wire','guide','stars','strike'):
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
            self.assertEqual((64.,128.,64.),self.uniforms[(entity,1)][:3])
            self.assertGreater(self.uniforms[(entity,1)][3], .6)
            self.assertEqual((41.,126.,49.,1.),self.uniforms[(entity,2)])
        self.effect.clear()
        for callback in self.callbacks: callback()
        self.assertFalse(self.live)

    def test_projection_flow_speed_does_not_change_orbit_and_keeps_actor_ids(self):
        self.effect = WireEffects(self.effect.bridge)
        self.effect.replace((10,64,20),(64,128,64))
        self.effect.follow((0.,0.,8.))
        ids = set(self.live)
        options = defaults()['golden']
        options['speed'] = 4.
        self.effect.configure_style('golden', options)
        for callback in self.callbacks: callback()
        self.assertEqual(ids, self.live)
        for entity in ids:
            self.assertGreater(self.uniforms[(entity,1)][3],1.5)
            self.assertEqual(1., self.uniforms[(entity,3)][3])
        with self.assertRaises(ValueError): SurveyEffects(self.effect.bridge).configure_style('starry', options)

    def test_two_markers_persist_and_reselect_only_replaces_changed_slot(self):
        self.effect.replace((0,0,0),(4,5,4))
        self.effect.sync_points([(0,0,0),(3,4,3)])
        first,second = self.effect.points
        with patch('HelloScript.projection.survey_effects.time.time',return_value=10**12):
            self.effect.follow((0.,0.,8.))
        self.assertEqual(5,len(self.live))
        for unused in range(20): self.effect.sync_points([(0,0,0),(3,4,3)])
        self.assertIs(first,self.effect.points[0])
        self.assertIs(second,self.effect.points[1])
        self.effect.sync_points([(0,0,0),(2,3,2)])
        self.assertIs(first,self.effect.points[0])
        self.assertNotIn(second['id'],self.live)
        self.assertEqual(5,len(self.live))
        self.effect.sync_points([(0,0,0),None])
        self.assertEqual(4,len(self.live))
        self.effect.clear()
        for callback in self.callbacks: callback()
        self.assertFalse(self.live)

    def test_steady_box_does_not_upload_animation_uniforms_every_frame(self):
        with patch('HelloScript.projection.survey_effects.time.time',return_value=10.):
            self.effect.replace((0,0,0),(4,5,4))
        with patch('HelloScript.projection.survey_effects.time.time',return_value=12.):
            self.effect.follow((0.,0.,8.),(0.,0.,12.))
        self.uniforms.clear()
        with patch('HelloScript.projection.survey_effects.time.time',return_value=13.):
            self.effect.follow((0.,0.,8.),(0.,0.,12.))
        self.assertFalse(self.uniforms)

    def test_camera_motion_keeps_selected_block_and_hit_face_fixed(self):
        self.effect.follow((0.,0.,8.),(0.,0.,12.))
        self.effect.replace((0,0,0),(4,5,4))
        self.effect.sync_points([(0,0,0),(3,4,3)])
        points=[(record['id'],record['centre'],record['face']) for record in self.effect.points]
        self.effect.follow((0.,0.,-8.),(0.,0.,-12.))
        self.assertEqual(points,[(record['id'],record['centre'],record['face']) for record in self.effect.points])
        for record in self.effect._records():
            self.assertEqual(tuple(record['centre'][i]-[0.,0.,-8.][i] for i in range(3))+(1.,),
                             self.uniforms[(record['id'],2)])

    def test_native_clicked_face_overrides_camera_for_all_six_sides(self):
        self.effect.follow((0.,0.,8.),(0.,0.,12.))
        self.effect.replace((0,0,0),(1,1,1))
        self.effect.sync_points([(0,0,0),None],[0,None])
        marker = self.effect.points[0]
        for native_face, shader_face in enumerate((2,3,4,5,0,1)):
            self.effect.sync_points([(0,0,0),None],[native_face,None])
            self.assertIs(marker,self.effect.points[0])
            self.assertEqual(shader_face,marker['face'])
            self.assertEqual(float(shader_face),self.uniforms[(marker['id'],4)][3])
        self.effect.follow((0.,0.,-8.),(0.,0.,-12.))
        self.assertEqual(1,marker['face'])

    def test_coincident_corners_share_one_marker_and_only_clicked_point_reenters(self):
        with patch('HelloScript.projection.survey_effects.time.time', return_value=10.):
            self.effect.replace((0,0,0),(1,1,1))
            self.effect.sync_points([(0,0,0),(0,0,0)])
        self.assertEqual(4, len(self.live))
        self.assertIsNone(self.effect.points[1])
        with patch('HelloScript.projection.survey_effects.time.time', return_value=12.):
            self.effect.pulse_point(1)
        self.assertEqual(12., self.effect.points[0]['started'])
        self.effect.sync_points([(0,0,0),(2,2,2)])
        first = self.effect.points[0]
        with patch('HelloScript.projection.survey_effects.time.time', return_value=20.):
            self.effect.pulse_point(1)
        self.assertEqual(12., first['started'])
        self.assertEqual(20., self.effect.points[1]['started'])
        self.assertEqual(5, len(self.live))

    def test_coincident_point_uses_latest_face_without_moving_legacy_marker(self):
        self.effect.sync_points([(0,0,0),(0,0,0)], [0,5])
        marker=self.effect.points[0]
        self.assertEqual(1,marker['face'])
        self.effect.follow((-12.,0.,0.),(-15.,0.,0.))
        self.effect.sync_points([(0,0,0),None])
        self.assertIs(marker,self.effect.points[0])
        self.assertEqual(1,marker['face'])

    def test_new_selection_samples_current_camera(self):
        self.effect.camera=(-10.,-10.,-10.)
        self.effect.bridge.level='test'
        self.effect.bridge.factory.CreateCamera=lambda level:types.SimpleNamespace(GetPosition=lambda:(10.,10.,10.))
        self.effect.replace((0,0,0),(4,5,4))
        self.assertEqual((10.,10.,10.),self.effect.camera)

    def test_delayed_native_registration_preserves_finished_entrance(self):
        with patch('HelloScript.projection.survey_effects.time.time',return_value=10.):
            self.effect.replace((0,0,0),(4,5,4))
        with patch('HelloScript.projection.survey_effects.time.time',return_value=12.):
            self.effect.follow((0.,0.,8.))
        for callback in self.callbacks:callback()
        for entity in self.live:
            self.assertEqual((1.,1.,.1,1.),self.uniforms[(entity,3)])


class OutlinePreferenceTests(unittest.TestCase):
    def test_malformed_values_do_not_poison_other_styles(self):
        options=normalize({'golden':{'speed':float('nan'),'density':float('inf'),'brightness':True},
                           'starry':{'speed':2.5},'rainbow':None})
        self.assertEqual(defaults()['golden'],options['golden'])
        self.assertEqual(2.5,options['starry']['speed'])
        self.assertEqual(3.,options['rainbow']['speed'])
        options['starry']['width']=2.
        self.assertEqual(1.,options['golden']['width'])


if __name__=='__main__': unittest.main()

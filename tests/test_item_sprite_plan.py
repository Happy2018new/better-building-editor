"""NBT, all frame poses and owned item publication without game execution."""
import copy
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests'))
from projection.cell import make_cell
from projection.item_sprite_plan import (iter_render_steps, sprite_content, validate_uniforms,
                                         with_preview_distance, WORLD_TAG)
from projection.item_sprite_profile import candidate_profile, production_profile
from projection.item_sprite_render import SkeletonItemRenderer, WorldItemRenderer
from projection.item_sprite_projection import ItemProjection, projection_plan
from projection.item_sprite_preview import ItemPreview
from projection.model import Document
from tests.test_static_frame_items import actor, frame
from tests.test_liquid_render import Doll, Model, Runtime
import generate_flat_item_proxies as flat
import generate_item_sprite_resources as resources


def enchanted(angle=0.):
    return actor(angle,user_data={'ench':{'__type__':9,'__value__':[
        {'id':{'__type__':2,'__value__':9},'lvl':{'__type__':2,'__value__':3}}]}})


def groups(document, **kwargs):
    return tuple(group for group in iter_render_steps(document,candidate_profile(),**kwargs) if group is not None)


class ItemPlanTests(unittest.TestCase):
    def test_candidate_has_separate_model_paths_and_production_remains_gated(self):
        self.assertIsNone(production_profile())
        for row in candidate_profile().items.values():
            self.assertNotEqual(row['ui_model'],row['world_model'])
            self.assertEqual('flat_icon',row['family'])

    def test_all48_pose_codes_and_both_enchantment_states_preserve_typed_payloads(self):
        for facing in range(6):
            for rotation in range(8):
                for nbt in (actor(rotation*45.),enchanted(rotation*45.)):
                    doc=Document((4,4,4),{(3,2,1):make_cell(frame(facing),nbt=nbt)})
                    saved=copy.deepcopy(doc.to_data())
                    value=groups(doc)[0]
                    self.assertEqual(value.uniforms,validate_uniforms(value.uniforms))
                    code=int(value.uniforms[0][0])
                    self.assertEqual(39,code%64)
                    self.assertEqual(facing,code//64%8)
                    self.assertEqual(rotation,code//512%8)
                    self.assertEqual(nbt==enchanted(rotation*45.),bool(code//4096))
                    self.assertEqual(saved,doc.to_data())

    def test_origin_zero_facing_zero_rotation_zero_stays_visible_by_slot_count(self):
        group=groups(Document((1,1,1),{(0,0,0):make_cell(frame(0),nbt=actor())}))[0]
        self.assertEqual((0.,)*4,group.uniforms[0])
        self.assertEqual(1.,group.uniforms[3][1])
        self.assertEqual(group.uniforms,validate_uniforms(group.uniforms))

    def test_unknown_visual_tags_maps_and_block_items_never_flatten(self):
        for nbt in (actor(item='minecraft:stone'),actor(item='minecraft:filled_map'),
                    actor(user_data={'custom':{'__type__':3,'__value__':1}}),actor(22.5)):
            original=copy.deepcopy(nbt)
            self.assertIsNone(sprite_content(frame(),nbt,candidate_profile().items))
            self.assertEqual(original,nbt)

    def test_full_missing_cutaway_and_layer_masks_remove_body_and_glint_together(self):
        doc=Document((2,3,1),{(0,1,0):make_cell(frame(),nbt=enchanted()),
                              (1,2,0):make_cell(frame(),nbt=actor())})
        original=copy.deepcopy(doc.to_data())
        self.assertEqual(2,groups(doc)[0].uniforms[3][1])
        one=groups(doc,visible=lambda pos:pos[1]==1)[0]
        self.assertEqual(1,one.uniforms[3][1])
        self.assertEqual(1,int(one.uniforms[0][0])//4096)
        self.assertEqual((),groups(doc,visible=lambda pos:False))
        self.assertEqual(original,doc.to_data())

    def test_model_batch_budget_rejects_instead_of_dropping_tail_items(self):
        profile=candidate_profile()
        profile.max_groups=1
        doc=Document((8,1,1),{(x,0,0):make_cell(frame(),nbt=actor()) for x in range(8)})
        with self.assertRaisesRegex(ValueError,'budget'):
            list(iter_render_steps(doc,profile))

    def test_forged_tags_and_invalid_slot_or_facing_are_rejected_before_native_calls(self):
        group=groups(Document((1,1,1),{(0,0,0):make_cell(frame(),nbt=actor())}))[0]
        for row,index,value in ((3,0,39686.),(3,1,0.),(3,1,5.),(3,3,float('nan')),
                                (0,0,6.*64),(1,0,1.)):
            bad=[list(row) for row in group.uniforms]
            bad[row][index]=value
            with self.assertRaises(ValueError):
                validate_uniforms(tuple(tuple(row) for row in bad))

    def test_ui_packet_keeps_sprite_validity_and_enchantment_fields(self):
        group=groups(Document((1,1,1),{(0,0,0):make_cell(frame(),nbt=enchanted())}))[0]
        ui=with_preview_distance(group,-.5)
        self.assertEqual(group.uniforms[:3],ui.uniforms[:3])
        self.assertEqual(group.uniforms[3][1:],ui.uniforms[3][1:])
        self.assertEqual(135,int(ui.uniforms[3][0])%256)
        self.assertEqual(ui.uniforms,validate_uniforms(ui.uniforms))

    def test_native_targets_reject_foreign_volume_and_invalid_indices(self):
        doc=Document((2,1,1),{(0,0,0):make_cell(frame(),nbt=actor())})
        for volume, indices in (((1,1,2),(0,)),((0,2,1),(0,)),((1,2,1),(-1,)),
                                ((1,2,1),(2,)),((1,2,1),(True,)),((1,2,1),(.5,))):
            targets={'volume':volume,'common':{frame():indices}}
            with self.assertRaises(ValueError):
                projection_plan(doc,candidate_profile(),targets,lambda pos:True,.5)

    def test_non_frame_and_hidden_cells_yield_before_scanning_the_complete_document(self):
        class CountingStore(object):
            def __init__(self):self.reads=0
            def items(self):
                for x in range(4096):
                    self.reads+=1
                    yield (x,0,0),('minecraft:stone',0)
        for visible in (None,lambda pos:False):
            store=CountingStore()
            iterator=iter_render_steps(SimpleNamespace(blocks=store),candidate_profile(),visible)
            self.assertIsNone(next(iterator))
            self.assertEqual(1,store.reads)
            for unused in range(63):self.assertIsNone(next(iterator))
            self.assertEqual(64,store.reads)


class ItemLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.doc=Document((2,1,1),{(0,0,0):make_cell(frame(),nbt=enchanted()),
                                  (1,0,0):make_cell(frame(),nbt=actor())})

    def test_ui_uses_item_validator_and_masks_before_asynchronous_publication(self):
        dolls,model,shown=(Doll(),Doll()),Model(),{}
        owner=SkeletonItemRenderer(dolls,model,shown.__setitem__)
        group=with_preview_distance(groups(self.doc)[0],-.5)
        self.assertFalse(owner.update(group,(.15,-55.,0.,0.),0.))
        dolls[1].model_id=44
        for now in (.03,.06,.09):
            owner.update(group,(.15,-55.,0.,0.),now)
        self.assertEqual(group.uniforms[3],model.calls[-1][2])
        self.assertFalse(shown[0])
        self.assertTrue(shown[1])
        owner.update(None,None,.12)
        self.assertFalse(any(shown.values()))
        owner.close()

    def test_world_refuses_ui_packet_and_preserves_plain_enchant_occupancy_snapshot(self):
        runtime=Runtime()
        runtime.session=SimpleNamespace(opacity=.4)
        owner=ItemProjection(runtime,self.doc,(10,64,20),candidate_profile(),0)
        occupied=bytearray(self.doc.volume)
        occupied[0]=2
        owner.request(occupied=occupied,deferred=True)
        occupied[:]=bytearray(self.doc.volume)
        for now in range(20):
            with patch('projection.liquid_projection.time.time',return_value=now*.1):
                if owner.advance():break
        self.assertTrue(owner.ready)
        self.assertTrue(all(runtime.hidden(identity) for identity in runtime.models))
        self.assertEqual(1,tuple(owner.renderer.staging.values())[0]['group'].uniforms[3][1])
        self.assertTrue(owner.prepare_publication(owner.revision))
        owner.finalize_publication(owner.revision)
        self.assertTrue(all(not runtime.hidden(identity) for identity in runtime.models))
        wrong=with_preview_distance(groups(self.doc,world=True)[0],0.)
        with self.assertRaisesRegex(ValueError,'UI depth'):
            owner.renderer.begin((wrong,),(10,64,20),2.)
        self.assertTrue(owner.close())
        self.assertFalse(runtime.models)

    def test_target_only_world_plan_has_no_neighbor_items(self):
        from projection.item_sprite_projection import projection_plan
        targets=self.doc.palette_data(lambda pos:pos==(1,0,0))
        prepared=tuple(row for row in projection_plan(self.doc,candidate_profile(),targets,lambda pos:True,1.) if row)
        self.assertEqual(1.,prepared[0].uniforms[3][1])
        self.assertEqual(1,int(prepared[0].uniforms[0][0])%64)


class ItemResourceTests(unittest.TestCase):
    def test_existing_source_extrusion_is_reused_and_all_vertices_belong_to_four_slots(self):
        spec=json.loads(flat.source_path().read_text(encoding='utf8'))
        with Image.open(ROOT/spec['items'][0]['generated_texture']) as image:
            data=resources.mesh(image,spec['frame_pose'],'test')['mesh'][0]
        self.assertEqual({0,1,2,3},{int(row['pos'][0]//2) for row in data['vertices']})
        self.assertEqual(len(data['vertices'])//2,len(data['indices']))
        self.assertTrue(all(0.<=axis<=1. for row in data['vertices'] for axis in row['uvcoord']))

    def test_glint_has_no_outside_alpha_or_clock_wrap_discontinuity(self):
        for u,v in ((0.,0.),(.25,.75),(1.,1.)):
            def strength(time):
                phase=(time%7.)*2.*math.pi/7.
                return (.2+.45*(.5+.5*math.sin((u+v)*6.*math.pi+phase))**8+
                        .35*(.5+.5*math.sin((u-v)*4.*math.pi-phase))**8)
            self.assertAlmostEqual(strength(0.),strength(210.),places=12)
            self.assertNotAlmostEqual(strength(0.),strength(.8),places=4)
        self.assertIn('if(texel.a<0.5) discard;',resources.FRAGMENT)
        self.assertIn('itemEnchanted>0.5',resources.FRAGMENT)
        self.assertIn('float phase=mod(TIME,7.0)*',resources.FRAGMENT)

    def test_shaders_keep_packed_depth_and_fragment_varyings_at_matching_highp(self):
        output=resources.outputs()
        fragment=output['resource_pack/shaders/glsl/modern_projection_item_sprite.fragment'].decode('ascii')
        for name in ('modern_projection_item_sprite.vertex','modern_projection_item_sprite_world.vertex'):
            vertex=output['resource_pack/shaders/glsl/'+name].decode('ascii')
            self.assertLess(vertex.index('precision highp float;'),vertex.index('#include'))
            for declaration in ('varying highp vec2 itemUv;','varying highp float itemVisible;',
                                'varying highp float itemEnchanted;','varying highp float itemClip;'):
                self.assertIn(declaration,vertex)
                self.assertIn(declaration,fragment)
        self.assertLess(fragment.index('precision highp float;'),fragment.index('#include'))


if __name__=='__main__':
    unittest.main()

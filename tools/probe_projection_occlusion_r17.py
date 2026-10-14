"""Paired world-occlusion controls linked to public debug blueprint cells.

Requires a disposable project with prepare_depth_controls_r17.py installed
before cold launch. No desktop input or foreground activation is used.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT,save
from audit_native_coordinates_r15 import LOAD,PROJECT,STATUS
from probe_banner_product_r16 import BannerAudit
from probe_book_native_r16 import CANDIDATE_SETUP,CANDIDATE_RESTORE,book_sources
from probe_book_reference_r17 import SERVER
from verify_debug_blueprints import CLIENT
from context_test_environment import SETUP as ENV_SETUP,RESTORE as ENV_RESTORE
from prepare_depth_controls_r17 import resource_sources

PREPARE=SERVER+'''assert not hasattr(sys,'_depth_fixture_r17')
foot=factory.CreatePos(player).GetFootPos()
rotation=factory.CreateRot(player).GetRot()
base=(int(foot[0]),int(foot[1])+12,int(foot[2]))
focus=(base[0]+3,base[1]+1,base[2])
positions=[(base[0]+dx,base[1],base[2]+dz) for dx in (-1,0,1) for dz in (-1,0,1)]
back=[(focus[0]+2,focus[1]+dy,focus[2]) for dy in (-1,0,1,2)]
front=[(focus[0]-1,focus[1]+dy,focus[2]) for dy in (-1,0,1,2)]
saved={'foot':foot,'rotation':rotation,'base':base,'focus':focus,
       'back':back,'front':front,'journal':[]}
sys._depth_fixture_r17=saved
for pos in positions+back+front:
 block=info.GetBlockNew(pos,dimension)
 assert block['name']=='minecraft:air',(pos,block)
 saved['journal'].append({'pos':pos,'block':block})
for pos in positions:
 assert info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
destination=(base[0]+.5,base[1]+1.,base[2]+.5)
assert factory.CreatePos(player).SetFootPos(destination)
_result={'focus':focus,'base':base,'destination':destination}
'''

BACKDROP=SERVER+'''saved=sys._depth_fixture_r17
material,front=%r
if material=='minecraft:leaves':material='minecraft:oak_leaves'
if material=='minecraft:slab':material='minecraft:smooth_stone_slab'
leaf_aux=factory.CreateBlockState(api.GetLevelId()).GetBlockAuxValueFromStates(
 'minecraft:oak_leaves',{'persistent_bit':True,'update_bit':False})
assert leaf_aux>=0,leaf_aux
positions=saved['front'] if front else saved['back']
rows=[]
for pos in saved['back']+saved['front']:
 name=material if pos in positions else 'minecraft:air'
 block={'name':name,'aux':leaf_aux if name=='minecraft:oak_leaves' else 0}
 info.SetBlockNew(pos,block,0,dimension,True,False)
 assert info.GetBlockNew(pos,dimension)==block,(pos,block,info.GetBlockNew(pos,dimension))
 rows.append({'pos':pos,'actual':info.GetBlockNew(pos,dimension)})
_result=rows
'''

RESTORE=SERVER+'''saved=getattr(sys,'_depth_fixture_r17',None)
if saved is None:_result={'restored':True,'owned':False}
else:
 assert factory.CreatePos(player).SetFootPos(tuple(saved['foot']))
 assert factory.CreateRot(player).SetRot(tuple(saved['rotation']))
 for entry in reversed(saved['journal']):
  info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,False)
  assert info.GetBlockNew(entry['pos'],dimension)==entry['block']
 del sys._depth_fixture_r17
 _result={'restored':True,'blocks':len(saved['journal'])}
'''

PICK=CLIENT+'''hit=b.factory.CreateCamera(b.level).PickFacing()
material=None
if hit.get('type')=='Block':
 material=b.factory.CreateBlockInfo(b.level).GetBlock((hit['x'],hit['y'],hit['z']))
_result={'hit':hit,'material':material}
'''


def document(case,unlit=False,face_west=False):
    sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
    from projection.model import Document
    from projection.cell import rebase
    from projection.debug_blueprints import material
    if case in ('enchanting_table','lectern.book'):
        from probe_book_native_r16 import document as book
        return book(case)
    if case in ('end_gateway','end_portal'):
        from projection.debug_portal_blueprints import source_document
        source=source_document(case)
        fixture='test.dynamic.portals'
    elif case.startswith('cauldron.'):
        from projection.debug_cauldron_blueprints import source_document
        source=source_document(case.split('.')[1]);fixture='test.entities.cauldrons'
    elif case=='frame':
        from projection.debug_item_blueprints import orientation_document
        source=orientation_document('frame_f4_r0')
        doc=Document((8,8,8),name='Frame occlusion control')
        for pos in ((3,3,2),(4,3,2)):
            dest=(pos[0],pos[1],pos[2]+1)
            doc.set_cell(dest,rebase(source.get(pos),(0,0,1)))
        return doc.to_data(),{'fixture':'test.entities.item_orientations','case':'frame_f4_r0'}
    elif case.startswith(('campfire.','shelf.')):
        from projection.debug_item_blueprints import slot_document
        source=slot_document(case);fixture='test.entities.visible_item_slots'
        if unlit and case.startswith('campfire.'):
            from projection.cell import actor_data,foreground,make_cell
            from projection.block_registry import states
            cell=source.get((3,3,3));value=foreground(cell)
            properties=states(value);properties['extinguished']=True
            source.set_cell((3,3,3),make_cell(material(value[0],properties),nbt=actor_data(cell)))
    elif case.startswith('spawner.'):
        from projection.debug_spawner_blueprints import source_document
        source=source_document(case.split('.')[1]);fixture='test.entities.spawners'
    elif case in ('chest','standing_sign','standing_banner','purple_shulker_box'):
        from projection.debug_compatibility_blueprints import CASES,source_document
        name='minecraft:'+case
        fixture=next(identity for identity,rows in CASES.items() if any(row['id']==name for row in rows))
        source=source_document(fixture,name)
        if face_west and case in ('standing_sign','standing_banner'):
            from projection.cell import actor_data,foreground,make_cell
            from projection.block_registry import states
            cell=source.get((3,3,3));value=foreground(cell)
            properties=states(value);properties['ground_sign_direction']=4
            source.set_cell((3,3,3),make_cell(material(value[0],properties),nbt=actor_data(cell)))
    else:
        source=Document((8,8,8),name='Native occlusion control')
        source.set_cell((3,3,3),material(case))
        source.set_cell((3,2,3),material('stone'))
        return source.to_data(),{'fixture':None,'control':case}
    # Keep exactly one focus cell and its support for a consistent sightline.
    doc=Document((8,8,8),name=source.name,biome=source.biome)
    for pos in ((3,3,3),(3,2,3)):doc.set_cell(pos,source.get(pos))
    return doc.to_data(),{'fixture':fixture,'case':case,'diagnostic_extinguished':unlit,
                          'diagnostic_face_west':face_west}


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    audit=BannerAudit(args)
    report={'schema_version':1,'completed':False,'restored':False,'rows':{},
            'captures':{},'cleanup_errors':[],'product_qualified':False,
            'book_sources':book_sources(args.project)}
    report['installed_resources']=resource_sources(args.project)
    book_active=False
    environment_saved=False
    try:
        report['environment']=audit.execute('environment',ENV_SETUP,False);environment_saved=True
        prepared=audit.execute('prepare',PREPARE,False);report['prepared']=prepared
        time.sleep(1.5)
        focus=prepared['focus'];origin=tuple(v-3 for v in focus)
        audit.execute('save_profiles',CLIENT+'''assert not hasattr(sys,'_depth_profiles_r17')
sys._depth_profiles_r17=(s.portal_profile,s.item_profile,s.cauldron_profile)
_result=True
''')
        for case in args.case:
            book_active=case in ('enchanting_table','lectern.book')
            if book_active:audit.execute('book_setup',CANDIDATE_SETUP)
            data,source=document(case,args.unlit,args.face_west);report['rows'][case]={'source':source,'document':data}
            audit.execute('aim',SERVER+'''saved=sys._depth_fixture_r17
foot=factory.CreatePos(player).GetFootPos()
eye=(foot[0],foot[1]+1.62,foot[2])
focus=saved['focus']
target=tuple(focus[i]+(.5,%r,.5)[i] for i in range(3))
assert factory.CreateRot(player).SetRot(api.GetRotFromDir(tuple(target[i]-eye[i] for i in range(3))))
_result=True
''' % (args.aim_height if args.aim_height is not None else 1.04 if book_active else .5),False)
            for mode in args.mode:
                audit.execute('profiles_'+mode,CLIENT+'''from modern_projection.projection.item_sprite_profile import candidate_profile as item_profile
from modern_projection.projection.portal_profile import candidate_profile as portal_profile
from modern_projection.projection.book_profile import candidate_profile as book_profile
from modern_projection.projection.cauldron_profile import candidate_profile as cauldron_profile
import copy
mode,book=%r
prefix='r17_depth_'+mode+'_'
s.portal_profile=book_profile() if book else portal_profile()
for mapping in (s.portal_profile.models,s.portal_profile.world_models):
 for key,value in list(mapping.items()):mapping[key]=prefix+value
s.portal_profile.identity+=('depth_control',mode)
s.item_profile=item_profile('3.10.0.420447')
s.item_profile.items=copy.deepcopy(s.item_profile.items)
for record in s.item_profile.items.values():
 for key in ('ui_model','world_model'):record[key]=prefix+record[key]
s.cauldron_profile=cauldron_profile()
for mapping in (s.cauldron_profile.models,s.cauldron_profile.world_models):
 for key,value in list(mapping.items()):mapping[key]=prefix+value
s.cauldron_profile.identity+=('depth_control',mode)
_result=True
''' % ((mode,book_active),))
                audit.execute('load',LOAD % ('production',(),json.dumps(data)));audit.settle()
                project_code=(PROJECT % args.missing).replace('s.origin=(0,-57,0)','s.origin=%r' % (origin,)).replace('s.opacity=1.','s.opacity=%r' % args.opacity)
                audit.execute('project',project_code)
                audit.settle(True);time.sleep(1.)
                report['rows'][case+'_'+mode+'_companions']=audit.execute('companions',CLIENT+'''
owner=b.projection_liquid
companions=getattr(owner,'companions',(owner,)) if owner else ()
_result=[{'type':type(value).__name__,'ready':value.ready,'error':str(value.error or ''),
 'groups':[row['group'] for row in value.renderer.active.values()]} for value in companions]
''')
                for material in args.backdrop:
                    for front in ((False,True) if args.front else (False,)):
                        label='%s_%s_%s_%s' % (case,mode,material,'front' if front else 'back')
                        report['rows'][label]=audit.execute('backdrop',BACKDROP % (('minecraft:'+material,front),),False)
                        time.sleep(1.)
                        report['captures'][label]=audit.frame(label)
                        report['captures'][label]['pointed_block']=audit.execute('pick',PICK)
                        if material=='air':
                            time.sleep(.6)
                            report['captures'][label+'_repeat']=audit.frame(label+'_repeat')
                        save(args.output/'report.json',report)
                audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
            if book_active:
                audit.execute('book_restore',CANDIDATE_RESTORE);book_active=False
        report['completed']=True
    finally:
        cleanup=(('projection',CLIENT+'b.stop_projection()\n_result=True',True),
                 ('world',RESTORE,False),
                 ('book',CANDIDATE_RESTORE,True),
                 ('profiles',CLIENT+'''if hasattr(sys,'_depth_profiles_r17'):
 s.portal_profile,s.item_profile,s.cauldron_profile=sys._depth_profiles_r17
 del sys._depth_profiles_r17
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''',True))
        for label,code,client in cleanup:
            try:report[label+'_restoration']=audit.execute('restore_'+label,code,client)
            except Exception as error:report['cleanup_errors'].append(label+': '+str(error))
        if environment_saved:
            try:report['environment_restoration']=audit.execute('environment_restore',ENV_RESTORE,False)
            except Exception as error:report['cleanup_errors'].append('environment: '+str(error))
        report['restored']=not report['cleanup_errors']
        report['source_unchanged']=report['installed_resources']==resource_sources(args.project)
        save(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],'captures':len(report['captures'])}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--owner',required=True)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case',action='append',required=True)
    parser.add_argument('--mode',action='append',choices=('off','on'),default=None)
    parser.add_argument('--backdrop',action='append',choices=('air','leaves','stone','glass','slab'),default=None)
    parser.add_argument('--front',action='store_true');parser.add_argument('--missing',action='store_true')
    parser.add_argument('--opacity',type=float,default=1.)
    parser.add_argument('--aim-height',type=float)
    parser.add_argument('--unlit',action='store_true',help='Keep source contents; extinguish campfire for unobstructed item control.')
    parser.add_argument('--face-west',action='store_true',help='View standing sign/banner face instead of the thin edge.')
    args=parser.parse_args();args.mode=args.mode or ['off','on'];args.backdrop=args.backdrop or ['air','leaves','stone','glass']
    run(args)

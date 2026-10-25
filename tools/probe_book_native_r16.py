"""Observe public idle-table/lectern books before choosing an appearance adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT, save
from audit_native_coordinates_r15 import LOAD, PROJECT, STATUS, OCCUPY
from probe_banner_product_r16 import BannerAudit
from verify_debug_blueprints import CLIENT

CASES=('enchanting_table','lectern.empty','lectern.book')
MODEL_PREFIXES=('',)+tuple('r17_book_'+motion+mode+'_' for motion in ('','moving_')
                          for mode in ('double','back','front'))
OWNER_SOURCES=tuple('behavior_pack/modern_projection/projection/'+name+'.py' for name in (
    'book_profile','book_render_plan','book_preview','book_projection','scene','session','ui',
    'diagnostics','world_projection','projection_transform','projection_target','error_text',
    'projection_companions','liquid_preview','liquid_projection',
    'liquid_render','liquid_viewport','liquid_transport','occupancy','occupancy_shader'))
BODY_SOURCES=(
    'tools/generate_enchanting_body_r17.py',
    'tools/data/enchanting_body_candidate_r17.json',
    'behavior_pack/modern_projection/projection/render_context.py',
    'behavior_pack/modern_projection/projection/bridge.py',
    'behavior_pack/modern_projection/projection/geometry_palette.py',
    'behavior_pack/modern_projection/projection/occupancy_shader.py',
    'behavior_pack/modern_projection/projection/entity_render.py',
    'behavior_pack/modern_projection/projection/static_table.py',
    'behavior_pack/modern_projection/projection/static_table_data.py',
    'behavior_pack/netease_blocks/preview_enchanting_body.json',
    'resource_pack/models/netease_block/preview_enchanting_body.json',
    'resource_pack/textures/blocks/modern_projection_enchanting_body.png')
BOOK_STATUS=STATUS+'''row=json.loads(_result)
p=s.book_preview;c=s.book_controls
row['book']={'owned':p is not None and c is not None,
 'ready':p is not None and p.published==p.signature(),
 'pending':c.pending if c else True,
 'error':str((p.error if p else None) or (c.error if c else None) or s.book_error or ''),
 'groups':list(p.groups.values()) if p else []}
companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
row['book_world']=[{'class':type(value).__name__,'ready':value.ready,'error':str(value.error or ''),
 'models':[(repr(name),entry['group']) for name,entry in value.renderer.active.items()]} for value in owners
 if type(value).__name__=='BookProjection']
_result=json.dumps(row)
'''


def book_sources(project, model_prefix=''):
    """Fingerprint the installed candidate, not merely the host checkout."""
    contract=project/'tools/data/book_resource_contract_nemc310_v1.json'
    if not contract.is_file():
        return {'contract_present':False}
    data=json.loads(contract.read_bytes())
    paths=sorted(path for path in data['output_sha256']
                 if path not in ('resource_pack/materials/entity.material',
                                 'resource_pack/models/netease_models.json'))
    result={'contract_present':True,
            'contract_sha256':hashlib.sha256(contract.read_bytes()).hexdigest(),
            'files':{path:hashlib.sha256((project/path).read_bytes()).hexdigest() for path in paths}}
    registry=json.loads((project/'resource_pack/models/netease_models.json').read_bytes())
    materials=json.loads((project/'resource_pack/materials/entity.material').read_bytes())['materials']
    models={name:value for name,value in registry.items() if name.startswith(model_prefix+'modern_projection_book_')}
    if len(models)!=4:raise ValueError('Book control registration is incomplete')
    owned={value['material']+':entity_for_skeleton_alpha':materials[value['material']+':entity_for_skeleton_alpha']
           for value in models.values()}
    for value in owned.values():
        for key in ('vertexShader','fragmentShader'):
            path='resource_pack/'+value[key]
            result['files'][path]=hashlib.sha256((project/path).read_bytes()).hexdigest()
    result['models']=models;result['materials']=owned
    result['body_files']={path:hashlib.sha256((project/path).read_bytes()).hexdigest()
                          for path in BODY_SOURCES if (project/path).is_file()}
    result['owner_files']={path:hashlib.sha256((project/path).read_bytes()).hexdigest()
                           for path in OWNER_SOURCES if (project/path).is_file()}
    for path,key,nested in (
            ('resource_pack/blocks.json','modern_projection:preview_enchanting_body',None),
            ('resource_pack/textures/terrain_texture.json','modern_projection_enchanting_body','texture_data')):
        if (project/path).is_file():
            registry=json.loads((project/path).read_bytes())
            if nested:registry=registry[nested]
            result[path]=registry.get(key)
    return result
CANDIDATE_SETUP=CLIENT+'''from modern_projection.projection.book_profile import candidate_profile
from modern_projection.projection import static_table
assert not hasattr(sys,'_book_r16_saved')
assert not hasattr(sys,'_book_r18_body_saved')
sys._book_r16_saved=s.book_profile
sys._book_r18_body_saved=static_table.CANDIDATE_ENABLED
static_table.CANDIDATE_ENABLED=True
s.book_profile=candidate_profile()
s.emit('preview')
_result=True
'''
CANDIDATE_RESTORE=CLIENT+'''if hasattr(sys,'_book_r16_saved'):
 s.book_profile=sys._book_r16_saved
 del sys._book_r16_saved
 if hasattr(sys,'_book_r18_body_saved'):
  from modern_projection.projection import static_table
  static_table.CANDIDATE_ENABLED=sys._book_r18_body_saved
  del sys._book_r18_body_saved
 s.emit('preview')
_result=True
'''


def candidate_setup(model_prefix=''):
    if not model_prefix:return CANDIDATE_SETUP
    return CANDIDATE_SETUP+'''for table in (s.book_profile.models,s.book_profile.world_models):
 for key,value in tuple(table.items()):table[key]=%r+value
s.book_profile.identity=s.book_profile.identity+(%r,)
_result=True
''' % (model_prefix,model_prefix)


class BookAudit(BannerAudit):
    def settle(self,projection=False):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            state=self.execute('settle',BOOK_STATUS)
            native=state['projection'];book=state['book']
            if state['preview_error'] or native['error'] or native['failed'] or book['error']:
                raise ValueError('Book preparation failed: '+repr(state))
            if projection:
                ready=native['active'] and not native['preparing'] and native['ready']
                ready=ready and state['book_world'] and all(row['ready'] and not row['error'] for row in state['book_world'])
            else:
                ready=(state['ready'] and not state['pending'] and not state['tile_running'] and
                       not state['dirty'] and book['owned'] and book['ready'] and not book['pending'])
            if ready:
                time.sleep(.6)
                return self.execute('settled',BOOK_STATUS)
            time.sleep(.4)
        raise TimeoutError('Book native controls did not settle')

    def frame(self,label):
        row=BannerAudit.frame(self,label)
        receipt=self.execute(label+'_book_models',CLIENT+'''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
models=sorted(row['group'].model_name for owner in owners
 if owner.__class__.__name__=='BookProjection' for row in owner.renderer.active.values())
_result={'active':s.projection_active,'models':models,
 'profile':s.book_profile.identity if s.book_profile else None,
 'preview_owned':s.book_preview is not None and s.book_controls is not None,
 'preview_groups':len(s.book_preview.groups) if s.book_preview else 0,
 'world_opacity':[row['group'].uniforms[3][3] for owner in owners
  if owner.__class__.__name__=='BookProjection' for row in owner.renderer.active.values()]}
''')
        if receipt['active'] and 'lectern.empty' not in label and not label.endswith('_occupied'):
            expected=self.args.model_prefix+'modern_projection_book_'
            if not receipt['models'] or not all(name.startswith(expected) for name in receipt['models']):
                raise ValueError('Book raster control did not reach the active models: '+repr(receipt))
        row['book_models']=receipt
        return row


def editor_owner_matrix(audit,case,captures):
    for yaw,pitch,zoom in ((35.,75.,3.),(215.,25.,1.),(35.,25.,2.)):
        audit.execute('book_view',CLIENT+
            's.camera_view(%r,%r,%r)\ns.camera_depth=0.\ns.emit("view")\n_result=True' % (yaw,pitch,zoom))
        time.sleep(.6)
        label='editor_'+case+'_yaw%d_pitch%d_zoom%d' % (yaw,pitch,zoom)
        captures[label]=audit.frame(label)
    audit.view(35.,3.,0.)
    for mode,layer in (('section',2),('section',3),('single',3),('single',2),('full',3)):
        label='editor_'+case+'_'+mode+'_layer%d' % layer
        audit.execute(label,CLIENT+
            's.layer(%r)\ns.display_mode(%r)\n_result=True' % (layer,mode))
        audit.settle()
        captures[label]=audit.frame(label)
    for label in ('hidden','restored'):
        name='editor_'+case+'_'+label
        audit.execute(name,CLIENT+'s.toggle_layer("hide",3)\n_result=True')
        audit.settle()
        captures[name]=audit.frame(name)


def document(case):
    sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
    from projection.debug_compatibility_blueprints import source_document
    from projection.debug_item_blueprints import slot_document
    from projection.cell import actor_data,foreground
    from projection.entity_render import native_actor
    if case=='enchanting_table':
        doc=source_document('test.dynamic.special','enchanting_table.default')
        fixture='test.dynamic.special'
    else:
        doc=slot_document(case);fixture='test.entities.visible_item_slots'
    actor=actor_data(doc.get((3,3,3)))
    material=foreground(doc.get((3,3,3)))
    return doc.to_data(),{'fixture':fixture,'case':case,'source_actor':actor,
        'native_actor':native_actor(material,actor),'material':material,'position':(3,3,3)}


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    default=bool(getattr(args,'production_default',False))
    owned=args.candidate or default
    audit=BookAudit(args) if owned else BannerAudit(args)
    report={'schema_version':2,'engine':'3.10.0.420447','stage':'production_default' if default else ('candidate_adapter' if args.candidate else 'native_before_adapter'),
        'owner_path':'independent_book' if owned else 'native',
        'owner_matrix':bool(getattr(args,'owner_matrix',False)),
        'occupancy_matrix':owned and bool(getattr(args,'owner_matrix',False)),
        'production_default_requested':default,'profile_assignment_performed':bool(args.candidate),
        'completed':False,'restored':False,'rows':{},'captures':{},'cleanup_errors':[]}
    report['installed_sources']=book_sources(args.project,args.model_prefix)
    report['model_prefix']=args.model_prefix
    occupied=()
    try:
        if default:
            report['default_profile']=audit.execute('default_profile',CLIENT+'''from modern_projection.projection import book_qualification_data as q
assert s.book_profile is not None
_result={'identity':s.book_profile.identity,'qualified':q.PRODUCT_QUALIFIED,
 'stage':q.QUALIFICATION_STAGE,'qualification_sha256':q.QUALIFICATION_SHA256,
 'engine':q.QUALIFICATION_ENGINE_VERSION}
''')
        if args.candidate:
            report['candidate_setup']=audit.execute('candidate_setup',candidate_setup(args.model_prefix))
        for case in CASES:
            data,source=document(case)
            report['rows'][case]=source
            report['rows'][case]['source_document']=data
            report['rows'][case]['loaded']=audit.execute('load_'+case,LOAD % ('production',(),json.dumps(data)))
            report['rows'][case]['ready']=audit.settle()
            audit.view(35.,3.,0.)
            for yaw in (35.,215.):
                audit.view(yaw,3.)
                time.sleep(.5)
                label='editor_'+case+'_yaw%d' % yaw
                report['captures'][label]=audit.frame(label)
            if case=='enchanting_table':
                for sample in range(3):
                    time.sleep(.6);label='editor_'+case+'_motion%d' % sample
                    report['captures'][label]=audit.frame(label)
                if owned:
                    for depth in (9.,0.):
                        audit.view(35.,3.,depth);time.sleep(.5)
                        label='editor_'+case+'_depth'+str(depth)
                        report['captures'][label]=audit.frame(label)
                    for action,label in (('hide','hidden'),('hide','restored')):
                        audit.execute(label,CLIENT+'s.toggle_layer(%r,3)\n_result=True' % action)
                        audit.settle();report['captures']['editor_'+label]=audit.frame('editor_'+label)
            if owned and getattr(args,'owner_matrix',False) and case!='lectern.empty':
                editor_owner_matrix(audit,case,report['captures'])
            for missing in (False,True):
                code=(PROJECT % missing).replace('s.origin=(0,-57,0)',
                    'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
                audit.execute('project',code);audit.settle(True)
                audit.camera()
                prefix=('missing_' if missing else 'full_')+case
                for sample in range(3 if case=='enchanting_table' else 1):
                    time.sleep(.6);label=prefix+'_motion%d' % sample
                    report['captures'][label]=audit.frame(label)
                if owned and getattr(args,'owner_matrix',False):
                    for opacity in (.35,.7,1.):
                        label=prefix+'_opacity'+str(opacity)
                        audit.execute(label,CLIENT+
                            's.range_value("opacity",%r,False)\n_result=True' % opacity)
                        audit.settle(True)
                        report['captures'][label]=audit.frame(label)
                if report['occupancy_matrix'] and missing and case!='lectern.empty':
                    origin=audit.execute('book_origin',CLIENT+'_result=json.dumps(s.origin)')
                    occupied=(tuple(origin[axis]+3 for axis in range(3)),)
                    states={}
                    for restore,suffix,expected in ((False,'occupied',0),(True,'restored',1)):
                        label=prefix+'_'+suffix
                        states[suffix]=audit.execute(label,OCCUPY % (occupied,restore),False)
                        if restore:occupied=()
                        deadline=time.monotonic()+25.
                        while time.monotonic()<deadline:
                            state=audit.execute(label+'_owner',CLIENT+'''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
_result=json.dumps({'models':sum(len(value.renderer.active) for value in owners if type(value).__name__=='BookProjection'),
 'source_document':s.editor.document.to_data()})
''')
                            if state['models']==expected:break
                            time.sleep(.4)
                        else:raise TimeoutError('Book occupancy did not reach expected model count: '+label)
                        states[suffix+'_source_document']=state['source_document']
                        report['captures'][label]=audit.frame(label)
                    report['rows'][case]['occupancy']=states
                audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
            save(args.output/'report.json',report)
        report['completed']=True
    finally:
        if occupied:
            try:audit.execute('restore_occupancy_final',OCCUPY % (occupied,True),False)
            except Exception as error:report['cleanup_errors'].append('occupancy: '+str(error))
        try:
            audit.execute('cleanup',CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''');report['restored']=not report['cleanup_errors']
        except Exception as error:report['cleanup_errors'].append(str(error))
        if args.candidate:
            try:
                report['candidate_restoration']=audit.execute('restore_candidate',CANDIDATE_RESTORE)
            except Exception as error:
                report['cleanup_errors'].append(str(error));report['restored']=False
        report['source_unchanged']=report['installed_sources']==book_sources(args.project,args.model_prefix)
        save(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'captures':len(report['captures']),
        'restored':report['restored']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--owner',required=True)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',action='store_true')
    parser.add_argument('--production-default',action='store_true',
                        help='Use the fresh Session profile without assigning any candidate.')
    parser.add_argument('--owner-matrix',action='store_true',
                        help='Add editor section/single/hidden/pose and full/missing live-opacity captures.')
    parser.add_argument('--model-prefix',default='',choices=MODEL_PREFIXES)
    args=parser.parse_args()
    if args.candidate and args.production_default:parser.error('Choose one book profile path')
    if args.production_default and args.model_prefix:parser.error('Default books use final model names')
    run(args)


if __name__=='__main__':main()

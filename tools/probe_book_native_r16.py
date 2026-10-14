"""Observe public idle-table/lectern books before choosing an appearance adapter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from audit_native_visual_r15 import ROOT, save
from audit_native_coordinates_r15 import LOAD, PROJECT
from probe_banner_product_r16 import BannerAudit
from probe_portal_product_r16 import PORTAL_STATUS, PortalAudit
from verify_debug_blueprints import CLIENT

CASES=('enchanting_table','lectern.empty','lectern.book')
MODEL_PREFIXES=('',)+tuple('r17_book_'+motion+mode+'_' for motion in ('','moving_')
                          for mode in ('double','back','front'))


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
    return result
CANDIDATE_SETUP=CLIENT+'''import modern_projection.projection.scene as scene
import modern_projection.projection.portal_projection as portal_world
from modern_projection.projection.book_profile import candidate_profile
from modern_projection.projection.book_preview import BookPreview
from modern_projection.projection.book_projection import BookProjection
assert not hasattr(sys,'_book_r16_saved')
sys._book_r16_saved=(scene.PortalPreview,portal_world.PortalProjection,s.portal_profile)
scene.PortalPreview=BookPreview
portal_world.PortalProjection=BookProjection
s.portal_profile=candidate_profile()
_result=True
'''
CANDIDATE_RESTORE=CLIENT+'''if hasattr(sys,'_book_r16_saved'):
 import modern_projection.projection.scene as scene
 import modern_projection.projection.portal_projection as portal_world
 scene.PortalPreview,portal_world.PortalProjection,s.portal_profile=sys._book_r16_saved
 del sys._book_r16_saved
_result=True
'''


def candidate_setup(model_prefix=''):
    if not model_prefix:return CANDIDATE_SETUP
    return CANDIDATE_SETUP+'''for table in (s.portal_profile.models,s.portal_profile.world_models):
 for key,value in tuple(table.items()):table[key]=%r+value
s.portal_profile.identity=s.portal_profile.identity+(%r,)
_result=True
''' % (model_prefix,model_prefix)


class BookAudit(PortalAudit):
    def execute(self,label,code,client=True):
        if code==PORTAL_STATUS:
            code=code.replace("type(value).__name__=='PortalProjection'","type(value).__name__=='BookProjection'")
        return BannerAudit.execute(self,label,code,client)

    def frame(self,label):
        row=BannerAudit.frame(self,label)
        receipt=self.execute(label+'_book_models',CLIENT+'''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
models=sorted(row['group'].model_name for owner in owners
 if owner.__class__.__name__=='BookProjection' for row in owner.renderer.active.values())
_result={'active':s.projection_active,'models':models,
 'profile':s.portal_profile.identity if s.portal_profile else None}
''')
        if receipt['active'] and 'lectern.empty' not in label:
            expected=self.args.model_prefix+'modern_projection_book_'
            if not receipt['models'] or not all(name.startswith(expected) for name in receipt['models']):
                raise ValueError('Book raster control did not reach the active models: '+repr(receipt))
        row['book_models']=receipt
        return row


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
    audit=BookAudit(args) if args.candidate else BannerAudit(args)
    report={'schema_version':1,'engine':'3.10.0.420447','stage':'candidate_adapter' if args.candidate else 'native_before_adapter',
        'completed':False,'restored':False,'rows':{},'captures':{},'cleanup_errors':[]}
    report['installed_sources']=book_sources(args.project,args.model_prefix)
    report['model_prefix']=args.model_prefix
    try:
        if args.candidate:
            report['candidate_setup']=audit.execute('candidate_setup',candidate_setup(args.model_prefix))
        for case in CASES:
            data,source=document(case)
            report['rows'][case]=source
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
                if args.candidate:
                    for depth in (9.,0.):
                        audit.view(35.,3.,depth);time.sleep(.5)
                        label='editor_'+case+'_depth'+str(depth)
                        report['captures'][label]=audit.frame(label)
                    for action,label in (('hide','hidden'),('hide','restored')):
                        audit.execute(label,CLIENT+'s.toggle_layer(%r,3)\n_result=True' % action)
                        audit.settle();report['captures']['editor_'+label]=audit.frame('editor_'+label)
            for missing in (False,True):
                code=(PROJECT % missing).replace('s.origin=(0,-57,0)',
                    'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
                audit.execute('project',code);audit.settle(True)
                PortalAudit.camera(audit)
                prefix=('missing_' if missing else 'full_')+case
                for sample in range(3 if case=='enchanting_table' else 1):
                    time.sleep(.6);label=prefix+'_motion%d' % sample
                    report['captures'][label]=audit.frame(label)
                audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
            save(args.output/'report.json',report)
        report['completed']=True
    finally:
        try:
            audit.execute('cleanup',CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
_result=True
''');report['restored']=True
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
    parser.add_argument('--model-prefix',default='',choices=MODEL_PREFIXES)
    run(parser.parse_args())


if __name__=='__main__':main()

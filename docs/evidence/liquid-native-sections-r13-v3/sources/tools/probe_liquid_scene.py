"""Exercise the ordinary Workspace Scene with an explicit diagnostic liquid profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import probe_liquid_pose_channel as base
import verify_debug_blueprints as blueprints
from _session import load_session

PROFILE='''from modern_projection.projection import block_registry,liquid_shape_data,liquid_face_texture_data
from modern_projection.projection.liquid_profile import NativeLiquidProfile
assert not hasattr(sys,'_liquid_scene_saved_profile')
sys._liquid_scene_saved_profile=(hasattr(s,'liquid_profile'),getattr(s,'liquid_profile',None))
resources={'schema_version':2,'payload_version':2,'game_version':block_registry.source_version(),
 'palette_sha256':block_registry.fingerprint(),'shape_candidate_sha256':liquid_shape_data.CANDIDATE_SHA256,
 'face_texture_rows_sha256':liquid_face_texture_data.RESOURCE_ROWS_SHA256,
 'models':(('still_water_grey',None,'modern_projection_liquid_still_water_grey','modern_projection_liquid_still_water_grey_world'),
  ('flowing_water_grey','diagnostic_native_side_frame0','modern_projection_liquid_flowing_water_grey_frozen','modern_projection_liquid_flowing_water_grey_frozen_world')),
 'uv_rotations':(('still_water_grey',None,(0,)),('flowing_water_grey','diagnostic_native_side_frame0',(0,))),
 'side_templates':{'flowing_water_grey':('diagnostic_native_side_frame0',0)},
 'world_scale':(16.,)*3,'world_rotation':(0.,)*3,'max_groups':64}
def ui_pose(unit,pitch,yaw,size):return (unit/min(size),pitch-90.,0.,yaw)
def ui_offset(size):return (0.,min(size)/4.)
s.liquid_profile=NativeLiquidProfile(resources,ui_pose,ui_offset)
_result=json.dumps({'resources':resources,'source_profile_accepted':False,'flow_artwork':'unaccepted frozen diagnostic'})
'''
CASE='''from modern_projection.projection.debug_liquid_blueprints import source_document
identity,control=%r
document=source_document(identity,isolated=True,control=control)
sys._blueprint_qa_identity=identity+'_'+control
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document)
s.progress=None
s.view='3d'
s.page='workspace'
s.camera_view(35.,25.,4.6)
s.emit()
_result=json.dumps({'identity':identity,'control':control,'blocks':len(document.blocks),
 'cells':[(pos,value) for pos,value in sorted(document.blocks.items())]})
'''
STATE=blueprints.STATUS+'''
row=json.loads(_result)
from modern_projection.projection.diagnostics import inspect
row['diagnostics']=inspect(s,{})
preview=getattr(s,'liquid_preview',None)
controls=getattr(s,'liquid_controls',None)
row['liquid_groups']=[]
if preview is not None:
 for key,group in preview.groups.items():
  entry=controls.registry.get(key,{}) if controls is not None else {}
  renderer=entry.get('renderer')
  row['liquid_groups'].append({'key':repr(key),'model':group.model_name,'origin':group.origin,
   'uniforms':group.uniforms,'geometry':entry.get('geometry'),
   'model_ids':renderer.ids if renderer is not None else None,
   'front':renderer.front if renderer is not None else None,'error':renderer.error if renderer is not None else None})
_result=json.dumps(row)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--capture-exe',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),MCDEV_OWNER=args.owner)
    session=load_session(args.session,args.owner,live=True)
    if Path(session['project']).resolve()!=base.ROOT:parser.error('The session belongs to another project')
    report=dict(schema=1,completed=False,restored=False,captures={},states={},cleanup_errors=[],
                probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Ordinary Scene owner integration using explicit unaccepted frozen flow artwork',
                native_uv_accepted=False,native_alpha_accepted=False,production_editor_accepted=False)

    def record():base.write(args.output,report)

    with base.Client(timeout=45) as client:
        check=blueprints.BlueprintCheck(client,args.output,30.)
        installed=False
        try:
            report['setup']=check.run(blueprints.INSTALL_PROBE)
            installed=True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old workspace',lambda state:not state['open'] and not state['transition'],check.navigation)
            report['profile']=check.run(PROFILE)
            check.run('owner.open_workspace()\n_result=True')
            check.wait('workspace mounts',lambda state:state['open'] and not state['transition'],check.navigation)
            for control in ('supported_positive','liquid_only','empty'):
                report['states'][control]={'source':check.run(CASE % (('water_depth_0_foreground',control),))}
                def ready(state):
                    liquid=state['diagnostics']['liquid']
                    if state['preview_error'] or liquid['error']:raise RuntimeError('Scene liquid failure: '+repr(state))
                    return (state['current_source'] and state['all_parts_current'] and state['model_revision_current']
                        and not state['preview_pending'] and not state['running'] and not state['dirty']
                        and not state['mounting'] and not state['edit_active'] and not state['io_active']
                        and liquid['enabled'] and liquid['planReady'] and not liquid['controlsPending']
                        and bool(liquid['groups'])==(control!='empty'))
                report['states'][control]['ready']=check.wait('ordinary Scene '+control,ready,lambda:check.run(STATE))
                time.sleep(.3)
                report['captures'][control]=base.capture(args.session,args.owner,
                    args.output.with_name(args.output.stem+'_'+control+'.png'),args.capture_exe)
                record()
            report['completed']=True
        except Exception as error:
            report['error']='%s: %s' % (type(error).__name__,error)
            raise
        finally:
            if installed:
                try:
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close liquid workspace',lambda state:not state['open'] and not state['transition'],check.navigation)
                    restore='''if hasattr(sys,'_liquid_scene_saved_profile'):
 had_profile,old_profile=sys._liquid_scene_saved_profile
 if had_profile:s.liquid_profile=old_profile
 elif hasattr(s,'liquid_profile'):del s.liquid_profile
 del sys._liquid_scene_saved_profile
''' + blueprints.RESTORE
                    report['cleanup']=check.run(restore)
                    report['restored']=bool(report['cleanup'])
                except Exception as error:report['cleanup_errors'].append('%s: %s' % (type(error).__name__,error))
            record()
    print(json.dumps({'completed':report['completed'],'restored':report['restored'],'captures':len(report['captures'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__=='__main__':raise SystemExit(main())

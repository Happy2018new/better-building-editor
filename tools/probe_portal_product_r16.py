"""Inspect public End portal surfaces through ordinary editor/world owners."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from audit_native_visual_r15 import ROOT, save
from audit_native_coordinates_r15 import LOAD, PROJECT, STATUS, OCCUPY
from probe_banner_product_r16 import BannerAudit
from verify_debug_blueprints import CLIENT

MODULE='behavior_pack/modern_projection/projection/'
SOURCES=tuple(MODULE+name+'.py' for name in (
    'portal_profile','portal_render_plan','portal_preview','portal_projection','debug_portal_blueprints',
    'liquid_preview','liquid_projection','liquid_transport','liquid_viewport','liquid_render',
    'scene','session','world_projection','projection_transform','projection_target','error_text',
    'occupancy','geometry_palette','render_context','tiles'))
RESOURCES=('resource_pack/shaders/glsl/modern_projection_portal_geometry.vertex',
           'resource_pack/shaders/glsl/modern_projection_portal_geometry_world.vertex',
           'resource_pack/shaders/glsl/modern_projection_portal_starfield.fragment',
           'resource_pack/models/modern_projection/portal/skeleton.json',
           'resource_pack/models/modern_projection/portal/end_portal_mesh.json',
           'resource_pack/models/modern_projection/portal/end_gateway_mesh.json',
           'resource_pack/textures/models/modern_projection/portal/end_sky.png',
           'resource_pack/textures/models/modern_projection/portal/end_portal_colors.png')
PORTAL_STATUS=STATUS+'''row=json.loads(_result)
p=s.portal_preview;c=s.portal_controls
row['portal']={'owned':p is not None and c is not None,
 'ready':p is not None and p.published==p.signature(),
 'pending':c.pending if c else True,
 'error':str((p.error if p else None) or (c.error if c else None) or s.portal_error or ''),
 'groups':list(p.groups.values()) if p else []}
companion=b.projection_liquid
companions=getattr(companion,'companions',(companion,)) if companion else ()
row['portal_world']=[{'class':type(value).__name__,'ready':value.ready,'error':str(value.error or ''),
 'models':[(repr(name),entry['group']) for name,entry in value.renderer.active.items()]} for value in companions
 if type(value).__name__=='PortalProjection']
_result=json.dumps(row)
'''


def document(family, transform='identity'):
    import sys
    sys.path.insert(0,str(ROOT/'behavior_pack/modern_projection'))
    from projection.debug_portal_blueprints import source_document
    from projection.debug_blueprints import build
    from projection.model import Editor
    from projection.storage import Selection
    doc=build('test.dynamic.portals') if family=='gallery' else source_document(family)
    if transform!='identity':
        editor=Editor(doc)
        editor.selection=Selection(editor.document.blocks)
        editor._transform(transform)
        doc=editor.document
    return json.loads(json.dumps(doc.to_data()))


class PortalAudit(BannerAudit):
    def settle(self,projection=False):
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            state=self.execute('settle',PORTAL_STATUS)
            native=state['projection']
            if state['preview_error'] or native['error'] or native['failed'] or state['portal']['error']:
                raise ValueError('Portal preparation failed: '+repr(state))
            if projection:
                ready=native['active'] and not native['preparing'] and native['ready']
                ready=ready and state['portal_world'] and all(row['ready'] and not row['error'] for row in state['portal_world'])
            else:
                ready=(state['ready'] and not state['pending'] and not state['tile_running'] and
                       not state['dirty'] and state['portal']['owned'] and state['portal']['ready'] and
                       not state['portal']['pending'])
            if ready:
                time.sleep(.6)
                return self.execute('settled',PORTAL_STATUS)
            time.sleep(.4)
        raise TimeoutError('Portal native controls did not settle')

    def load(self,family,transform='identity'):
        data=document(family,transform)
        result=self.execute('load_'+family,LOAD % ('production',(),json.dumps(data)))
        self.view(35.,3.,0.)
        ready=self.settle()
        return {'loaded':result,'ready':ready,'saved_document':data}

    def camera(self):
        return self.execute('world_camera',CLIENT+'''cam=b.factory.CreateCamera(b.level)
target=tuple(s.origin[i]+(3.5,3.5,3.5)[i] for i in range(3))
position=tuple(s.origin[i]+(8.,9.,-4.)[i] for i in range(3))
rot=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
if api.GetTopUI()=='pause_screen':api.PopTopUI()
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})
''')


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ['MCDEV_ALLOW_USER_FOREGROUND']='1'
    audit=PortalAudit(args)
    report={'schema':1,'engine':'3.10.0.420447','fixture':'test.dynamic.portals',
        'candidate':not args.production,'completed':False,'restored':False,'cleanup_errors':[],
        'captures':{},'rows':{},'manual_pixel_acceptance':False,
        'source_sha256':{name:hashlib.sha256((args.project/name).read_bytes()).hexdigest() for name in SOURCES+RESOURCES}}
    occupied=()
    try:
        report['initial']=audit.execute('initial',PORTAL_STATUS)
        profile_code=CLIENT+'''sys._portal_r16_saved=(s.portal_profile,s.grid)
from modern_projection.projection.portal_profile import candidate_profile,production_profile
if %r:
 expected=production_profile(api.GetEngineVersion());assert expected is not None
 assert s.portal_profile is not None and s.portal_profile.identity==expected.identity
else:s.portal_profile=candidate_profile()
s.grid=False
_result=json.dumps({'profile':s.portal_profile.identity,'default_enabled':%r})
'''
        report['profile']=audit.execute('profile',profile_code % (args.production,args.production))
        for family in ('end_portal','end_gateway'):
            report['rows'][family]=audit.load(family)
            if args.stage=='editor':
                for yaw,pitch in ((35.,25.),(215.,25.),(35.,75.)):
                    audit.execute('view',CLIENT+'s.camera_view(%r,%r,3.)\ns.emit("view")\n_result=True' % (yaw,pitch))
                    time.sleep(.8)
                    label='editor_'+family+'_yaw%d_pitch%d' % (yaw,pitch)
                    report['captures'][label]=audit.frame(label)
                audit.view(35.,3.)
                for sample in range(3):
                    time.sleep(.35)
                    label='editor_'+family+'_motion%d' % sample
                    report['captures'][label]=audit.frame(label)
                for zoom in (1.,2.,3.):
                    audit.view(35.,zoom)
                    time.sleep(.6)
                    label='editor_'+family+'_zoom%d' % zoom
                    report['captures'][label]=audit.frame(label)
                for depth in (9.,0.):
                    audit.view(35.,3.,depth)
                    time.sleep(.6)
                    label='editor_'+family+'_depth'+str(depth)
                    report['captures'][label]=audit.frame(label)
                audit.execute('hide',CLIENT+'s.toggle_layer("hide",3)\n_result=True')
                report['rows'][family+'_hidden']=audit.settle()
                report['captures']['editor_'+family+'_hidden']=audit.frame('editor_'+family+'_hidden')
                audit.execute('restore',CLIENT+'s.toggle_layer("hide",3)\n_result=True')
                report['rows'][family+'_restored']=audit.settle()
                report['captures']['editor_'+family+'_restored']=audit.frame('editor_'+family+'_restored')
                for transform in ('rotate_y90','mirror_x'):
                    report['rows'][family+'_'+transform]=audit.load(family,transform)
                    time.sleep(.6)
                    label='editor_'+family+'_'+transform
                    report['captures'][label]=audit.frame(label)
            elif args.stage=='world':
                for missing in (False,True):
                    code=(PROJECT % missing).replace('s.origin=(0,-57,0)',
                        'foot=b.player_position.GetFootPos()\ns.origin=(int(foot[0]),int(foot[1])+32,int(foot[2]))')
                    audit.execute('project',code)
                    report['rows'][family+str(missing)]=audit.settle(True)
                    audit.camera()
                    label=('missing_' if missing else 'full_')+family
                    for sample in range(3):
                        time.sleep(.4)
                        report['captures'][label+'_motion%d' % sample]=audit.frame(label+'_motion%d' % sample)
                    if missing:
                        origin=audit.execute('origin',CLIENT+'_result=json.dumps(s.origin)')
                        occupied=(tuple(origin[i]+(3,3,3)[i] for i in range(3)),)
                        report['rows'][label+'_occupied']=audit.execute('occupy',OCCUPY % (occupied,False),False)
                        time.sleep(4.)
                        report['rows'][label+'_occupied_state']=audit.execute('occupied_state',PORTAL_STATUS)
                        report['captures'][label+'_occupied']=audit.frame(label+'_occupied')
                        report['rows'][label+'_restored']=audit.execute('restore',OCCUPY % (occupied,True),False)
                        occupied=()
                        time.sleep(4.)
                        report['rows'][label+'_restored_state']=audit.execute('restored_state',PORTAL_STATUS)
                        report['captures'][label+'_restored']=audit.frame(label+'_restored')
                    for opacity in (.45,0.,1.):
                        audit.execute('opacity',CLIENT+'s.range_value("opacity",%r,False)\n_result=True' % opacity)
                        time.sleep(.8)
                        report['captures'][label+'_opacity'+str(opacity)]=audit.frame(label+'_opacity'+str(opacity))
                    audit.execute('stop',CLIENT+'b.stop_projection()\n_result=True')
            else:
                raise ValueError('Unknown portal stage')
            save(args.output/'report.json',report)
        if args.stage=='editor':
            report['rows']['gallery']=audit.load('gallery')
            audit.view(35.,2.)
            time.sleep(1.)
            report['captures']['editor_gallery']=audit.frame('editor_gallery')
        report['completed']=True
    finally:
        if occupied:
            try:audit.execute('restore_final',OCCUPY % (occupied,True),False)
            except Exception as error:report['cleanup_errors'].append(str(error))
        try:
            audit.execute('cleanup',CLIENT+'''b.stop_projection()
if navigator.top is not None:navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos();cam.UnDepartCamera();cam.LockModCameraPitch(False);cam.LockModCameraYaw(False)
if hasattr(sys,'_portal_r16_saved'):
 s.portal_profile,s.grid=sys._portal_r16_saved;del sys._portal_r16_saved
_result=True
''')
            report['restored']=not report['cleanup_errors']
        except Exception as error:report['cleanup_errors'].append(str(error))
        report['source_unchanged']=all(hashlib.sha256((args.project/name).read_bytes()).hexdigest()==value
            for name,value in report['source_sha256'].items())
        save(args.output/'report.json',report)
    print(json.dumps({'completed':report['completed'],'captures':len(report['captures']),
                      'restored':report['restored'],'source_unchanged':report['source_unchanged']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stage',choices=('editor','world'),required=True)
    parser.add_argument('--production',action='store_true')
    run(parser.parse_args())


if __name__=='__main__':main()

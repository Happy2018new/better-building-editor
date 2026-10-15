"""Frozen candidate controls through the ordinary Scene and public world owner."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import textwrap
import time

import capture_pure_liquid_native_controls as native
import capture_frozen_liquid_controls as frozen
import probe_liquid_pose_channel as base
import probe_liquid_scene as scene
import probe_liquid_uniform_transport as transport
import verify_debug_blueprints as blueprints
import verify_debug_visuals as visuals
from camera_projection import project_points
from _session import load_session

SOURCE = '''from modern_projection.projection.cell import AIR,background,foreground,make_cell,encode
from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_liquid_blueprints import source_document
from modern_projection.projection.model import Document
assert not hasattr(sys,'_liquid_workspace_source')
def workspace_liquid_source(identity,control):
 if identity in ('source','pool'):
  key='water_depth_0_foreground' if identity=='source' else 'water_source_pool_foreground'
  return source_document(key,isolated=True,control=control)
 positions={'fence':(3,1,6),'fence_rear':(3,1,6),'pane':(13,1,6),'slab':(23,1,6)}
 keep=positions[identity]
 source=build('test.layers.water')
 original=source.get(keep)
 if control.endswith('_dark'):
  from modern_projection.projection import block_registry
  original=make_cell(('minecraft:dark_oak_fence',block_registry.DEFAULT_AUX['minecraft:dark_oak_fence']),background(original))
 assert background(original)[0]=='minecraft:water'
 document=Document((10,8,10),name=source.name,biome=source.biome)
 delta=tuple((3,3,3)[i]-keep[i] for i in range(3))
 support=tuple((keep[0]+x,keep[1]-1,keep[2]+z) for x in (-1,0,1) for z in (-1,0,1))
 if identity=='fence_rear':support=((keep[0],keep[1]-1,keep[2]),)
 if control in ('supported_positive','supported_negative','supported_positive_dark','supported_negative_dark'):
  for pos in support:document.set_cell(tuple(pos[i]+delta[i] for i in range(3)),source.get(pos))
 if control!='empty':
  value=(original if control in ('supported_positive','supported_positive_dark') else
   make_cell(foreground(original),AIR) if control in ('supported_negative','supported_negative_dark') else make_cell(AIR,background(original)))
  document.set_cell((3,3,3),value)
 if identity=='fence_rear' and control in ('supported_positive','supported_negative','supported_positive_dark','supported_negative_dark'):
  from modern_projection.projection import block_registry
  rear='minecraft:black_concrete' if control.endswith('_dark') else 'minecraft:gold_block'
  document.set_cell((3,3,2),(rear,block_registry.DEFAULT_AUX[rear]))
 return document
sys._liquid_workspace_source=workspace_liquid_source
'''
LOAD = '''identity,control=%r
from modern_projection.projection.cell import encode
document=sys._liquid_workspace_source(identity,control)
sys._blueprint_qa_identity='liquid_workspace_'+identity+'_'+control
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document)
s.progress=None
s.view='3d'
s.page='workspace'
s.camera_view(35.,25.,4.6)
if identity=='fence_rear':
 s.camera_view(0.,0.,3.)
 s.camera_pan=(.15,-.08)
s.emit()
_result=json.dumps({'identity':identity,'control':control,'blocks':len(document.blocks),
 'biome':document.biome,'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
STATE = scene.STATE + '''row=json.loads(_result)
from modern_projection.projection.cell import encode
row['biome']=s.editor.document.biome
row['camera_depth']=s.camera_depth_pose
row['depth_plane']=s.depth_plane()
row['camera_pan']=s.camera_pan
row['camera_pose']=s.camera_pose
row['groups_revision']=s.liquid_preview.revision if s.liquid_preview is not None else None
row['source_cells']=[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())]
row['liquid_control_requests']=[]
controls=s.liquid_controls
if controls is not None:
 for key,entry in sorted(controls.registry.items(),key=lambda item:repr(item[0])):
  renderer=entry.get('renderer')
  row['liquid_control_requests'].append({'key':repr(key),'geometry':entry.get('geometry'),
   'visible':renderer.visible if renderer is not None else None,
   'poses':renderer.poses if renderer is not None else None,
   'uniforms':renderer.uniforms if renderer is not None else None,
   'ready_request':entry.get('ready_request'),
   'doll_positions':[ref.current.GetGlobalPosition() if ref.current else None for ref in entry['dolls']],
   'doll_sizes':[ref.current.GetSize() if ref.current else None for ref in entry['dolls']]})
row['screen_size']=b.factory.CreateGame(b.level).GetScreenSize()
_result=json.dumps(row)
'''
WATER_OWNER_SELECT = '''liquid=next((companion for companion in getattr(owner,'companions',(owner,))
 if type(companion) in (LiquidProjection,ProductLiquidProjection)),None)
'''
WATER_OWNER = '''from modern_projection.projection.liquid_projection import LiquidProjection
from modern_projection.projection.liquid_product_projection import ProductLiquidProjection
owner=b.projection_liquid
''' + WATER_OWNER_SELECT

WORLD_STATE = WATER_OWNER + '''from modern_projection.projection.cell import encode
work=b.projection_work
tracker=b.projection_occupancy
renderer=liquid.renderer if liquid is not None else None
_result=json.dumps({'active':s.projection_active,'origin':s.origin,'opacity':s.opacity,
 'biome':s.editor.document.biome,'work_ready':work is not None and work.ready,
 'work_current':work is not None and work.serial==b.projection_serial and
  work.document.blocks==s.editor.document.blocks and work.document.biome==s.editor.document.biome,
 'work_error':work.error if work is not None else None,'missing':s.projection_missing,
 'body_entity':b.entity,'body_uniforms':work.shader.uniforms if work is not None else None,
 'body_parts':work.shader.parts if work is not None else None,
 'liquid_owned':work is not None and work.liquid is owner and liquid is not None,
 'liquid_ready':liquid is not None and liquid.ready,
 'liquid_error':str(liquid.error) if liquid is not None and liquid.error is not None else None,
 'liquid_source_current':liquid is not None and liquid.document.blocks==s.editor.document.blocks and
  liquid.document.biome==s.editor.document.biome,
 'liquid_groups':[{'key':repr(key),'id':record['model_id'],'group':record['group'],
  'visible':record['visible']} for key,record in sorted(renderer.active.items(),key=lambda item:repr(item[0]))]
  if renderer is not None else [],
 'staging':len(renderer.staging) if renderer is not None else None,
 'retired':len(renderer.retired) if renderer is not None else None,
 'cleanup_errors':renderer.cleanup_errors if renderer is not None else None,
 'occupancy':{'tracked':len(tracker.targets),'rendered_keep':tracker.rendered[tracker.index((3,3,3))],
  'state_keep':tracker.state[tracker.index((3,3,3))],'commits':tracker.commits,
  'changed':len(tracker.changed),'pending':tracker.pending_model is not None or tracker.attaching,
  'building':tracker.build is not None,'failed':tracker.failed} if tracker is not None else None,
 'source_cells':[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())]})
'''
WRITE = '''from modern_projection.server_system import WorldAdapter
from modern_projection.projection.cell import AIR,decode,encode
saved=sys._liquid_pose_world
adapter=WorldAdapter(saved['player'])
cells=json.loads(%r)
for pos in saved['workspace_cells']:
 assert adapter.write(tuple(pos),AIR),pos
saved['workspace_cells']=[]
rows=[]
for pos,value in cells:
 pos=tuple(pos)
 assert pos in saved['region'],pos
 saved['workspace_cells'].append(pos)
 assert adapter.write(pos,decode(value)),(pos,value)
 rows.append({'position':pos,'actual':encode(adapter.read(pos))})
_result=json.dumps(rows)
'''
FLOW = '''import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
freeze=%r
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
assert game.ForbidLiquidFlow(freeze)
saved['flow_frozen']=freeze
if freeze:saved['workspace_cells']=[]
_result=json.dumps({'forbidden':freeze,'returned':True,'baseline':'fresh isolated world'})
'''
CAMERA = '''target,offset=%r
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation((direction[0],direction[1]+180.,0.))
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'target':target,'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
'''

SCENE_ALPHA = '''alpha=%r
preview=s.liquid_preview
assert preview.iterator is None and preview.published==preview.signature()
for key,group in list(preview.groups.items()):
 value=group.uniforms[3]
 preview.groups[key]=group._replace(uniforms=group.uniforms[:3]+((value[0],alpha,value[2],value[3]),))
_result=True
'''
WORLD_ALPHA = WATER_OWNER + '''alpha=%r
assert liquid is not None
renderer=liquid.renderer
assert not renderer.staging and renderer.wanted is None
for record in renderer.active.values():
 group=record['group'];value=group.uniforms[3]
 value=(value[0],alpha,value[2],value[3])
 assert renderer.model.SetExtraUniformValue(record['model_id'],4,value)
 record['group']=group._replace(uniforms=group.uniforms[:3]+(value,))
_result=True
'''
ALPHA_PHASES = ((0.,'0'),(.25,'0_25'),(.45,'0_45'),(.75,'0_75'),(1.,'1'),(-1.,'default'))

QUALIFICATION_PREPARE = '''import json,math,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_liquid_pose_world')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
assert dimension==0 and foot and len(foot)==3
assert all(not math.isnan(value) and not math.isinf(value) for value in foot)
assert -64<=foot[1]<320 and abs(foot[0])<=1000000 and abs(foot[2])<=1000000
origin=(int(math.floor(foot[0]))+6,int(math.floor(foot[1]))+24,int(math.floor(foot[2]))+6)
info=factory.CreateBlockInfo(player)
region=[(origin[0]+x,origin[1]+y,origin[2]+z) for x in range(-2,4) for y in range(-2,4) for z in range(-2,4)]
assert all(-64<=pos[1]<320 for pos in region)
for pos in region:
 front=info.GetBlockNew(pos,dimension);back=info.GetLiquidBlock(pos,dimension)
 assert front and front.get('name')=='minecraft:air',(pos,front)
 assert back is None or back.get('name')=='minecraft:air',(pos,back)
sys._liquid_pose_world={'origin':origin,'region':region,'player':player,'dimension':dimension,'foot_before':foot,
 'workspace_cells':[]}
assert info.SetBlockNew(origin,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
placed=info.GetBlockNew(origin,dimension)
assert placed and placed.get('name')=='minecraft:stone',(origin,placed)
_result=json.dumps({'origin':origin,'player':player,'dimension':dimension,'region':region,'foot':foot,
 'placed':placed,'reserved_native_write_readback_passed':True,'position_write_attempted':False})
'''
QUALIFICATION_CLEAN_WORLD = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_liquid_pose_world',None)
rows=[]
if saved is not None:
 info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
 for pos in saved['region']:
  before=info.GetBlockNew(tuple(pos),saved['dimension'])
  if before.get('name')!='minecraft:air':
   assert info.SetBlockNew(tuple(pos),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
  after=info.GetBlockNew(tuple(pos),saved['dimension'])
  rows.append({'pos':pos,'after':after})
 assert all(row['after'].get('name')=='minecraft:air' for row in rows)
 del sys._liquid_pose_world
_result=json.dumps({'restored':True,'rows':rows,'position_write_attempted':False})
'''


def guarded_cleanup(code, journal):
    return ('import sys\nif hasattr(sys,%r):\n' % journal +
            ''.join(' ' + line + '\n' for line in code.splitlines()) +
            'else:\n _result=True\n')

TRANSPARENCY_REGIONS = {'submerged_body':((3.43,3.2,3.5),(3.57,3.5,3.5)),
                        'behind_block':((3.10,3.2,3.5),(3.25,3.5,3.5))}


def scene_transparency_regions(state):
    """Map declared logical interiors through native control layout, without pixels."""
    entries=[row for row in state['liquid_control_requests'] if row['poses'] and any(row['visible'])]
    if not entries or any(abs(value)>1e-4 for value in state['camera_pose'][:2]):
        raise ValueError('Transparency regions require ready native controls at the declared front view')
    row=entries[0]
    slot=row['visible'].index(True)
    position,size,pose=row['doll_positions'][slot],row['doll_sizes'][slot],row['poses'][slot]
    unit=pose[0]*min(size)
    center=(position[0]+size[0]/2.,position[1]+size[1]/2.-min(size)/4.)
    return {name:[[center[0]+(point[0]-2.)*unit,center[1]-(point[1]-2.)*unit]
                  for point in points] for name,points in TRANSPARENCY_REGIONS.items()}


def native_transparency_regions(camera, origin, vertical_fov):
    points={name:[tuple(origin[i]+point[i]-3. for i in range(3)) for point in region]
            for name,region in TRANSPARENCY_REGIONS.items()}
    return {name:project_points(region,camera['position'],camera['target'],camera['screen'],vertical_fov)
            for name,region in points.items()}


def alpha_ready(state, alpha, world=False):
    if world:
        return world_ready(state) and bool(state['liquid_groups']) and all(
            row['group'][3][3][1] == alpha for row in state['liquid_groups'])
    controls = state['liquid_control_requests']
    return scene_ready(state) and bool(controls) and all(row['visible'] and any(row['visible'])
        and row['uniforms'][row['visible'].index(True)].get('4', [None, None])[1] == alpha
        for row in controls)


def scene_ready(state):
    liquid = state['diagnostics']['liquid']
    if state['preview_error'] or liquid['error']:
        raise RuntimeError('Scene liquid failure: ' + repr(state))
    return (state['current_source'] and state['all_parts_current'] and state['model_revision_current']
            and not state['preview_pending'] and not state['running'] and not state['dirty']
            and not state['mounting'] and not state['edit_active'] and not state['io_active']
            and all(not part['pending'] for part in state['parts'])
            and liquid['enabled'] and liquid['planReady'] and not liquid['controlsPending'])


def world_ready(state):
    if state['work_error'] or state['liquid_error']:
        raise RuntimeError('Public liquid projection failure: ' + repr(state))
    return (state['active'] and state['work_ready'] and state['work_current'] and state['liquid_owned']
            and state['liquid_ready'] and state['liquid_source_current'] and not state['staging']
            and not state['retired'] and not state['cleanup_errors'])


def method_source(commit, path, class_name, method_name):
    source = subprocess.check_output(['git', 'show', commit+':'+path], cwd=str(base.ROOT)).decode('utf8')
    module = ast.parse(source)
    owner = next(item for item in module.body if isinstance(item, ast.ClassDef) and item.name == class_name)
    method = next(item for item in owner.body if isinstance(item, ast.FunctionDef) and item.name == method_name)
    return textwrap.dedent(ast.get_source_segment(source, method)), hashlib.sha256(source.encode('utf8')).hexdigest()


def opacity_patch(commit):
    methods = []
    for module, owner, method in (('bridge', 'ClientBridge', 'update_projection_opacity'),
                                   ('session', 'Session', 'range_value')):
        path = 'behavior_pack/modern_projection/projection/'+module+'.py'
        source, digest = method_source(commit, path, owner, method)
        methods.append({'module':module, 'owner':owner, 'method':method, 'source':source,
                        'path':path, 'source_sha256':digest})
    code = '''from modern_projection.projection import bridge as patch_bridge,session as patch_session
assert not hasattr(sys,'_liquid_workspace_opacity_methods')
sys._liquid_workspace_opacity_methods=[]
'''
    for row in methods:
        target = 'patch_'+row['module']+'.'+row['owner']
        code += "sys._liquid_workspace_opacity_methods.append((%s,%r,hasattr(%s,%r),getattr(%s,%r,None)))\n" % (
            target,row['method'],target,row['method'],target,row['method'])
        code += 'patch_namespace={}\nexec %r in patch_%s.__dict__,patch_namespace\n' % (row['source'],row['module'])
        code += 'setattr(%s,%r,patch_namespace[%r])\n' % (target,row['method'],row['method'])
    return code+'\n_result=True', {'commit':commit, 'methods':methods, 'scope':'Exact methods from committed source applied only to this owned diagnostic session'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--case', choices=('source', 'pool', 'fence', 'fence_rear', 'pane', 'slab'), action='append')
    parser.add_argument('--transparency-controls', action='store_true',
                        help='Fixed front view of public water-layer fence with independent rear gold block')
    parser.add_argument('--camera-calibration',type=Path,
                        help='Passed independent stone calibration from this owned native session')
    parser.add_argument('--scene-only', action='store_true')
    parser.add_argument('--scene-controls', action='store_true', help='Top-view depth and viewport-edge positive/negative controls')
    parser.add_argument('--opacity-commit', help='Exact reviewed bridge/session method commit for this diagnostic session')
    parser.add_argument('--max-handles', type=int, default=280000, help='Abort and restore before the native session handle cutoff')
    parser.add_argument('--deployment-profile', action='store_true', help='Use the generated disabled deployment candidate explicitly')
    parser.add_argument('--qualification-minimal', action='store_true', help='Twelve fixed-topology alpha PNGs across Scene/full/missing')
    parser.add_argument('--physical-readiness', type=Path, help='Passed read-only client/server feet and reserve receipt')
    args = parser.parse_args()
    if args.qualification_minimal and (not args.transparency_controls or not args.deployment_profile or args.scene_only):
        parser.error('Minimal qualification requires generated deployment plus three-route transparency controls')
    if args.qualification_minimal and not args.physical_readiness:
        parser.error('Minimal qualification requires passed physical world readiness')
    if args.transparency_controls and (args.case not in (None,['fence_rear']) or args.scene_controls):
        parser.error('Transparency controls require the declared fence_rear fixture and fixed camera')
    if args.transparency_controls and not args.scene_only and not args.camera_calibration:
        parser.error('World transparency controls require independent same-session camera calibration')
    if args.output.exists():
        parser.error('Choose a fresh evidence report')
    archive = args.output.with_suffix('.probe.py')
    if archive.exists():
        parser.error('Choose a fresh probe archive')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    if not session.get('noactivation', {}).get('window_noactivate'):
        parser.error('A guarded NOACTIVATE session is required')
    physical = None
    if args.physical_readiness:
        physical = json.loads(args.physical_readiness.read_bytes())
        binding = physical.get('session_binding', {})
        if (not all(physical.get(key) is True for key in ('passed', 'completed', 'read_only'))
                or physical.get('world_write_attempted') or physical.get('position_write_attempted')
                or any(binding.get(key) != session[key] for key in ('owner', 'session_file', 'game_pid', 'game_identity'))):
            parser.error('Physical readiness must be passed and bound to the exact owned session')
    contract = json.loads(args.contract.read_bytes())
    calibration=None
    if args.camera_calibration:
        calibration=json.loads(args.camera_calibration.read_bytes())
        if (not all(calibration.get(field) is True for field in ('passed','completed','restored'))
                or calibration.get('cleanup_errors')
                or Path(calibration.get('session_file','')).resolve() != Path(session['session_file']).resolve()):
            parser.error('Camera calibration must be passed, restored and bound to this exact owned session')
    report = dict(schema=1, completed=False, restored=False, cleanup_errors=[], captures={},
                  scene={}, world={}, native={}, measurements=[],
                  probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  contract_sha256=hashlib.sha256(args.contract.read_bytes()).hexdigest(),
                  source_sha256={name:hashlib.sha256((base.ROOT/name).read_bytes()).hexdigest() for name in (
                      'behavior_pack/modern_projection/projection/scene.py',
                      'behavior_pack/modern_projection/projection/world_projection.py',
                      'behavior_pack/modern_projection/projection/liquid_projection.py',
                      'behavior_pack/modern_projection/projection/liquid_render.py',
                      'behavior_pack/modern_projection/projection/debug_blueprints.py')},
                  session_binding={key:session[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')},
                  scope='Actual Workspace Scene and public WorldProjection with frozen candidate artwork; native references have flow disabled',
                  native_shape_accepted=False, native_uv_accepted=False, native_alpha_accepted=False,
                  production_editor_accepted=False, production_world_accepted=False, production_memory_accepted=False,
                  resource_contract=contract)
    if physical:
        report['physical_readiness'] = {'path':str(args.physical_readiness.resolve()),
            'sha256':hashlib.sha256(args.physical_readiness.read_bytes()).hexdigest(), 'binding':physical['session_binding']}
    archive.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(__file__,archive)
    report['probe_source'] = {'path':str(archive.resolve()),'sha256':report['probe_sha256']}
    report['launch_noactivation'] = session['noactivation']
    report['budget'] = {'max_handles':args.max_handles, 'observed_max_handles':0}
    cases = ('fence_rear',) if args.transparency_controls else tuple(args.case or ('source', 'pool', 'fence', 'slab'))
    alpha_phases = ((0., '0'), (.45, '0_45'), (1., '1'), (-1., 'default')) if args.qualification_minimal else ALPHA_PHASES
    if args.transparency_controls:
        report['transparency_plan'] = {
            'source':'public test.layers.water fence (3,1,6), translated to (3,3,3)',
            'rear_block':[3,3,2,'minecraft:gold_block'],
            'minimum_water_height':178/255., 'scene_camera':[0.,0.,3.,.15,-.08],
            'regions':TRANSPARENCY_REGIONS,
            'excluded':'waterline, above-water cap, support, crosshair',
            'native_alpha_accepted':False,
            'contrast_controls':{'bright':['minecraft:oak_fence','minecraft:gold_block'],
                                 'dark':['minecraft:dark_oak_fence','minecraft:black_concrete'],
                                 'requires_same_water_geometry':True},
            'scene_capture_settle_seconds':2.,
            'water_alpha_holdout':{'values':[row[0] for row in alpha_phases],
                'changes':'Fourth liquid uniform y only; source, body geometry, tint, camera and model IDs must remain fixed',
                'native_alpha_accepted':False},
            'scope':'Contribution controls only; native reference, tint/texture, opacity and ordering still require independent assessment'}
    controls = ('supported_positive', 'supported_negative', 'liquid_only', 'empty')
    if args.transparency_controls:
        controls += ('supported_positive_dark','supported_negative_dark')
    if args.qualification_minimal:
        controls = ('supported_positive',)
    record = lambda: base.write(args.output, report)

    def frame(label):
        sample = dict(transport.metrics(args.session,args.owner),label='before/'+label)
        report['measurements'].append(sample)
        report['budget']['observed_max_handles'] = max(report['budget']['observed_max_handles'],sample['handles'])
        if sample['handles'] >= args.max_handles:
            record()
            raise RuntimeError('Native handle budget reached before '+label)
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem+'_'+label+'.png'), args.capture_exe)
        record()

    with base.Client(timeout=45) as client:
        check = blueprints.BlueprintCheck(client, args.output, 45.)
        installed = world_saved = visual_saved = patched = environment_attempted = False
        try:
            report['measurements'].append(dict(transport.metrics(args.session, args.owner), label='before'))
            report['setup'] = check.run(blueprints.INSTALL_PROBE)
            installed = True
            if args.opacity_commit:
                code, report['opacity_patch'] = opacity_patch(args.opacity_commit)
                patched = True
                report['opacity_patch']['applied'] = check.run(code)
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old workspace', lambda row:not row['open'] and not row['transition'], check.navigation)
            profile = scene.PROFILE.replace("'modern_projection_liquid_still_water_grey'", "'modern_projection_liquid_still_water_grey_frozen'")
            profile = profile.replace("'modern_projection_liquid_still_water_grey_world'", "'modern_projection_liquid_still_water_grey_frozen_world'")
            if args.deployment_profile:
                profile = '''from modern_projection.projection.liquid_deployment import candidate_profile
assert not hasattr(sys,'_liquid_scene_saved_profile')
sys._liquid_scene_saved_profile=(hasattr(s,'liquid_profile'),getattr(s,'liquid_profile',None))
s.liquid_profile=candidate_profile(frozen=True)
_result=json.dumps({'production_qualified':False,'deployment_candidate':True,'frozen':True})
'''
            report['profile'] = check.run(profile)
            check.run(SOURCE+'\n_result=True')
            check.run('owner.open_workspace()\n_result=True')
            check.wait('workspace mounts', lambda row:row['open'] and not row['transition'], check.navigation)
            for identity in cases:
                rows = report['scene'][identity] = {}
                for control in controls:
                    row = rows[control] = {'source':check.run(LOAD % ((identity, control),))}
                    row['ready'] = check.wait('Scene '+identity+'/'+control,
                        lambda state:scene_ready(state) and (not args.transparency_controls or
                            max(abs(a-b) for a,b in zip(state['camera_pose'],(0.,0.,3.)))<1e-4),
                        lambda:check.run(STATE))
                    if args.transparency_controls and control=='supported_positive':
                        report['transparency_plan']['scene_engine_regions']=scene_transparency_regions(row['ready'])
                        report['transparency_plan']['scene_engine_screen']=row['ready']['screen_size']
                        record()
                    time.sleep(2. if args.transparency_controls else .25)
                    row['capture_state'] = check.wait('Scene settled '+identity+'/'+control,
                        scene_ready, lambda:check.run(STATE))
                    if not args.qualification_minimal:
                        frame('scene_'+identity+'_'+control)
                check.run(LOAD % ((identity, 'supported_positive'),))
                check.wait('Scene restore '+identity, scene_ready, lambda:check.run(STATE))
                if args.transparency_controls:
                    time.sleep(2.)
                    rows['water_alpha'] = {'baseline':check.run(STATE)}
                    for alpha,label in alpha_phases:
                        check.run(SCENE_ALPHA % alpha)
                        row = rows['water_alpha'][label] = {'requested':alpha}
                        row['ready'] = check.wait('Scene water alpha '+label,
                            lambda state:alpha_ready(state,alpha),lambda:check.run(STATE))
                        time.sleep(2.)
                        row['capture_state'] = check.run(STATE)
                        frame('scene_'+identity+'_water_alpha_'+label)
                rows['biomes'] = {}
                for biome in (() if args.transparency_controls else ('swampland', 'mangrove_swamp', 'plains')):
                    row = rows['biomes'][biome] = {'changed':check.run('s.set_biome(%r)\n_result=True' % biome)}
                    row['ready'] = check.wait('Scene biome '+biome, lambda state:scene_ready(state) and state['biome']==biome,
                                              lambda:check.run(STATE))
                    time.sleep(.25)
                    frame('scene_'+identity+'_biome_'+biome)
                if args.scene_controls:
                    rows['view_controls'] = {}
                    phases = (('depth_full',90.,0.,(.225,.33)), ('depth_hidden',90.,5.,(.225,.33)),
                              ('edge_left',25.,0.,(-.25,0.)), ('edge_right',25.,0.,(.7,0.)),
                              ('edge_offscreen',25.,0.,(2.,0.)), ('view_restored',25.,0.,(0.,0.)))
                    for phase,pitch,depth,pan in phases:
                        phase_rows = rows['view_controls'][phase] = {}
                        for control in ('supported_positive','supported_negative','empty'):
                            row = phase_rows[control] = {'source':check.run(LOAD % ((identity,control),))}
                            check.run('s.camera_view(0.,%r,4.6)\ns.camera_depth=%r\ns.camera_depth_pose=%r\n'
                                      's.camera_pan=%r\ns.emit()\n_result=True' % (pitch,depth,depth,pan))
                            row['ready'] = check.wait('Scene '+identity+'/'+phase+'/'+control,
                                lambda state:scene_ready(state) and abs(state['camera_depth']-depth)<.001,
                                lambda:check.run(STATE))
                            time.sleep(.25)
                            frame('scene_'+identity+'_'+phase+'_'+control)
            if not args.scene_only:
                check.run('navigator.pop()\n_result=True')
                check.wait('close Scene for native reference', lambda row:not row['open'] and not row['transition'], check.navigation)
                report['visual_saved'] = check.run(visuals.SAVE_VISUAL)
                visual_saved = True
                environment_attempted = True
                report['environment'] = base.run(client, base.ENVIRONMENT, True)
                world_saved = True
                report['reservation'] = base.run(client, QUALIFICATION_PREPARE if args.qualification_minimal
                                                else base.PREPARE % 'minecraft:stone', True)
                report['cleared_seed'] = base.run(client, base.CLEAR, True)
                report['flow_freeze'] = base.run(client, FLOW % True, True)
                report['near_player'] = ({'position_write_attempted':False,'scope':'Original player position retained'}
                                        if args.qualification_minimal else base.run(client, base.NEAR_PLAYER, True))
                time.sleep(1.)
                origin = tuple(report['reservation']['origin'])
                document_origin = tuple(axis-3 for axis in origin)
                target=tuple(origin[i]+(1.35 if i==1 and args.transparency_controls else .5)
                             for i in range(3))
                offset=(0.,0.,7.) if args.transparency_controls else (6.,5.,8.)
                report['camera'] = check.run(CAMERA % ((target, offset),))
                if args.transparency_controls:
                    report['transparency_plan']['camera_calibration']={'path':str(args.camera_calibration.resolve()),
                        'sha256':hashlib.sha256(args.camera_calibration.read_bytes()).hexdigest(),
                        'vertical_fov':calibration['vertical_fov']}
                    report['transparency_plan']['world_engine_regions']=native_transparency_regions(
                        report['camera'],origin,calibration['vertical_fov'])
                    report['transparency_plan']['world_engine_screen']=report['camera']['screen']
                    record()
                check.run('s.origin=%r\ns.opacity=%r\ns.projection_outline=False\n_result=True' %
                          (document_origin,1. if args.transparency_controls else .8))
                positions = report['reservation']['region']
                for identity in cases:
                    references = report['native'][identity] = {}
                    for control in (() if args.qualification_minimal else controls):
                        source = report['scene'][identity][control]['source']
                        cells = [(tuple(document_origin[i]+pos[i] for i in range(3)), value) for pos,value in source['cells']]
                        row = references[control] = {'requested':cells,'write':base.run(client, WRITE % native.wire(cells), True)}
                        time.sleep(.35)
                        row['before'] = {'server':base.run(client, native.snapshot_code(positions, True), True),
                                         'client':check.run(native.snapshot_code(positions))}
                        frame('native_'+identity+'_'+control)
                        row['after'] = {'server':base.run(client, native.snapshot_code(positions, True), True),
                                        'client':check.run(native.snapshot_code(positions))}
                        row['expected_native'] = frozen.native_reference(cells)
                        row['gates'] = {}
                        for side in ('server', 'client'):
                            gate = row['gates'][side] = native.native_changes(row['before'][side], row['after'][side], positions)
                            gate['before_matches'] = native.matches(row['before'][side], row['expected_native'], positions)
                            gate['after_matches'] = native.matches(row['after'][side], row['expected_native'], positions)
                            if not gate['unchanged'] or not gate['before_matches'] or not gate['after_matches']:
                                record()
                                raise RuntimeError('Frozen native reference changed: '+identity+'/'+control+'/'+side)
                        record()
                    report['native'][identity]['clear'] = base.run(client, WRITE % native.wire([]), True)
                    rows = report['world'][identity] = {}
                    for control in controls:
                        row = rows['full_'+control] = {'source':check.run(LOAD % ((identity, control),))}
                        check.run('s.projection_missing=False\nb.project()\n_result=True')
                        row['ready'] = check.wait('full projection '+identity+'/'+control, world_ready, lambda:check.run(WORLD_STATE))
                        time.sleep(.3)
                        if not args.qualification_minimal:
                            frame('world_'+identity+'_full_'+control)
                        if args.transparency_controls and control=='supported_positive':
                            holdout = rows['full_water_alpha'] = {'baseline':row['ready']}
                            for alpha,label in alpha_phases:
                                check.run(WORLD_ALPHA % alpha)
                                holdout[label] = check.wait('Full water alpha '+label,
                                    lambda state:alpha_ready(state,alpha,True),lambda:check.run(WORLD_STATE))
                                time.sleep(.3)
                                frame('world_'+identity+'_full_water_alpha_'+label)
                        check.run('b.stop_projection()\n_result=True')
                    row = rows['missing_empty_world'] = {'source':check.run(LOAD % ((identity, 'supported_positive'),))}
                    if args.transparency_controls:
                        for control in controls:
                            row = rows['missing_'+control] = {'source':check.run(LOAD % ((identity,control),))}
                            check.run('s.projection_missing=True\nb.project()\n_result=True')
                            row['ready'] = check.wait('missing transparency '+control,world_ready,lambda:check.run(WORLD_STATE))
                            time.sleep(.3)
                            if not args.qualification_minimal:
                                frame('world_'+identity+'_missing_'+control)
                            if control=='supported_positive':
                                holdout = rows['missing_water_alpha'] = {'baseline':row['ready']}
                                for alpha,label in alpha_phases:
                                    check.run(WORLD_ALPHA % alpha)
                                    holdout[label] = check.wait('Missing water alpha '+label,
                                        lambda state:alpha_ready(state,alpha,True),lambda:check.run(WORLD_STATE))
                                    time.sleep(.3)
                                    frame('world_'+identity+'_missing_water_alpha_'+label)
                            check.run('b.stop_projection()\n_result=True')
                        check.run(LOAD % ((identity,'supported_positive'),))
                    if args.qualification_minimal:
                        check.run('b.stop_projection()\n_result=True')
                        record()
                        continue
                    check.run('s.projection_missing=True\nb.project()\n_result=True')
                    row['ready'] = check.wait('missing empty world '+identity, world_ready, lambda:check.run(WORLD_STATE))
                    time.sleep(.3)
                    frame('world_'+identity+'_missing_empty_world')
                    source = report['scene'][identity]['supported_negative']['source']
                    cells = [(tuple(document_origin[i]+pos[i] for i in range(3)), value)
                             for pos,value in source['cells'] if tuple(pos)==(3,3,3)]
                    if not cells:
                        cells = [(origin, ['minecraft:stone', 0])]
                    row = rows['missing_occupied'] = {'write':base.run(client, WRITE % native.wire(cells), True)}
                    row['ready'] = check.wait('missing occupied '+identity,
                        lambda state:world_ready(state) and state['occupancy']['rendered_keep']==2
                        and not state['occupancy']['changed'] and not state['occupancy']['pending'], lambda:check.run(WORLD_STATE))
                    time.sleep(.3)
                    frame('world_'+identity+'_missing_occupied')
                    row = rows['missing_restored'] = {'write':base.run(client, WRITE % native.wire([]), True)}
                    row['ready'] = check.wait('missing restored '+identity,
                        lambda state:world_ready(state) and state['occupancy']['rendered_keep']!=2
                        and not state['occupancy']['changed'] and not state['occupancy']['pending'], lambda:check.run(WORLD_STATE))
                    time.sleep(.3)
                    frame('world_'+identity+'_missing_restored')
                    rows['opacity'] = {}
                    for opacity in (.4, .8):
                        check.run('s.range_value("opacity",%r,editor=False)\n_result=True' % opacity)
                        row = rows['opacity'][str(opacity)] = check.wait('live opacity '+str(opacity),
                            lambda state:world_ready(state) and state['opacity']==opacity and
                            all(group['group'][3][3][3]==opacity for group in state['liquid_groups']), lambda:check.run(WORLD_STATE))
                        time.sleep(.25)
                        frame('world_'+identity+'_opacity_'+str(opacity).replace('.', '_'))
                    rows['biomes'] = {}
                    for biome in (() if args.transparency_controls else ('swampland', 'mangrove_swamp', 'plains')):
                        check.run('s.set_biome(%r)\n_result=True' % biome)
                        row = rows['biomes'][biome] = check.wait('world biome '+biome,
                            lambda state:world_ready(state) and state['biome']==biome, lambda:check.run(WORLD_STATE))
                        time.sleep(.25)
                        frame('world_'+identity+'_biome_'+biome)
                    check.run('b.stop_projection()\n_result=True')
                    record()
            report['measurements'].append(dict(transport.metrics(args.session, args.owner), label='after'))
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            actions = [('projection', lambda:check.run('b.stop_projection()\n_result=True'))]
            if world_saved:
                actions.extend((('native_clear', lambda:base.run(client,
                                    guarded_cleanup(WRITE % native.wire([]), '_liquid_pose_world'), True)),
                                ('flow_restore', lambda:base.run(client,
                                    guarded_cleanup(FLOW % False, '_liquid_pose_world'), True)),
                                ('world_cleanup', lambda:base.run(client, QUALIFICATION_CLEAN_WORLD
                                    if args.qualification_minimal else base.CLEAN_WORLD, True))))
            if visual_saved:
                actions.append(('camera_restore', lambda:check.run(visuals.camera_restore_code(False))))
                actions.append(('visual_restore', lambda:check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\n'
                    's.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                    'del sys._blueprint_visual_saved\n_result=True')))
            if installed:
                def restore():
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close probe workspace', lambda row:not row['open'] and not row['transition'], check.navigation)
                    return check.run('''if hasattr(sys,'_liquid_scene_saved_profile'):
 had_profile,old_profile=sys._liquid_scene_saved_profile
 if had_profile:s.liquid_profile=old_profile
 elif hasattr(s,'liquid_profile'):del s.liquid_profile
 del sys._liquid_scene_saved_profile
if hasattr(sys,'_liquid_workspace_source'):del sys._liquid_workspace_source
''' + blueprints.RESTORE)
                actions.append(('workspace_restore', restore))
            if patched:
                actions.append(('opacity_patch_restore',lambda:check.run('''if hasattr(sys,'_liquid_workspace_opacity_methods'):
 for owner,method,present,old in sys._liquid_workspace_opacity_methods:
  if present:setattr(owner,method,old)
  else:delattr(owner,method)
 del sys._liquid_workspace_opacity_methods
_result=True''')))
            if environment_attempted:
                actions.append(('environment_restore', lambda:base.run(client,
                    guarded_cleanup(base.RESTORE_ENVIRONMENT, '_context_environment_saved'), True)))
            for label, action in actions:
                try:
                    report[label] = action()
                except Exception as error:
                    report['cleanup_errors'].append('%s: %s: %s' % (label, type(error).__name__, error))
                record()
            report['restored'] = not report['cleanup_errors']
            record()
    print(json.dumps({'completed':report['completed'], 'restored':report['restored'], 'captures':len(report['captures'])}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

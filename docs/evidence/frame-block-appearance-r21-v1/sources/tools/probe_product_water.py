"""Capture public water-style cases through ordinary Scene and world owners.

This host runner uses an already bound background session. It never starts,
activates or resizes a game, and keeps source documents intact during missing
projection. Product acceptance is separate from historical native parity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import capture_pure_liquid_native_controls as native
import probe_liquid_pose_channel as base
import probe_liquid_workspace as workspace
import verify_debug_blueprints as blueprints
import verify_debug_visuals as visuals
from check_native_dialogs import assertion_dialogs
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SAVE_HUD, RESTORE_HUD
from water_capture_contract import (camera_matches, calibrated_viewport_matches, scene_capture_state,
                                    stable_scene_predicate)
from _session import load_session

PROFILE = '''from modern_projection.projection.liquid_product_deployment import candidate_profile
assert not hasattr(sys,'_product_water_saved_profile')
sys._product_water_saved_profile=(s.liquid_profile,s.grid)
s.liquid_profile=candidate_profile(frozen=%r)
s.grid=False
_result=json.dumps({'style':s.liquid_profile.style_version,'rules_sha256':s.liquid_profile.rules_sha256,
 'frozen':%r,'native_parity_accepted':False})
'''

DEFAULT_PROFILE = '''from modern_projection.projection.liquid_product_deployment import production_profile
from modern_projection.projection.liquid_render_target_data import TARGET_ENGINE_VERSION
assert s.liquid_profile is not None
expected=production_profile(TARGET_ENGINE_VERSION)
assert expected is not None and type(s.liquid_profile) is type(expected)
assert s.liquid_profile.rules_sha256==expected.rules_sha256
assert s.liquid_profile.models==expected.models
assert not hasattr(sys,'_product_water_saved_profile')
sys._product_water_saved_profile=(s.liquid_profile,s.grid)
s.grid=False
_result=json.dumps({'style':s.liquid_profile.style_version,'rules_sha256':s.liquid_profile.rules_sha256,
 'frozen':False,'native_parity_accepted':False,'production_default':True,
 'profile_assignment_performed':False,'engine_version':TARGET_ENGINE_VERSION})
'''

INSTALL_TIMING = '''import time
from modern_projection.projection.liquid_preview import LiquidPreview
from modern_projection.projection.liquid_projection import LiquidProjection
from modern_projection.projection.liquid_viewport import LiquidControls
from modern_projection.projection.liquid_render import WorldLiquidRenderer,SkeletonLiquidRenderer
assert not hasattr(sys,'_product_water_timing')
sys._product_water_timing={'saved':[],'samples':{},'details':{'native_calls':{},'outliers':[]}}
def water_timing_install(cls,name):
 original=getattr(cls,name)
 key=cls.__name__+'.'+name
 sys._product_water_timing['saved'].append((cls,name,original))
 sys._product_water_timing['samples'][key]=[]
 def timed(self,*args,**kwargs):
  started=time.time()
  try:return original(self,*args,**kwargs)
  finally:
   elapsed=(time.time()-started)*1000.
   sys._product_water_timing['samples'][key].append(elapsed)
   if elapsed>16.7 and len(sys._product_water_timing['details']['outliers'])<128:
    row={'method':key,'elapsed_ms':elapsed,'started':started,
     'fixture':getattr(sys,'_blueprint_qa_identity',None)}
    if key=='LiquidControls.update':
     row['registry_entries']=len(self.registry)
     row['requested_groups']=len(args[0])
     row['pending_renderers']=sum(entry.get('renderer') is not None and
      entry['renderer'].pending is not None for entry in self.registry.values())
    sys._product_water_timing['details']['outliers'].append(row)
 setattr(cls,name,timed)
for cls,name in ((LiquidPreview,'advance'),(LiquidProjection,'advance'),
 (LiquidControls,'update'),(WorldLiquidRenderer,'advance')):
 water_timing_install(cls,name)
def water_native_timing_install(name):
 original=getattr(SkeletonLiquidRenderer,name)
 sys._product_water_timing['saved'].append((SkeletonLiquidRenderer,name,original))
 sys._product_water_timing['details']['native_calls'][name]={'calls':0,'maximum_ms':0.}
 def timed(self,*args,**kwargs):
  started=time.time()
  try:return original(self,*args,**kwargs)
  finally:
   elapsed=(time.time()-started)*1000.
   row=sys._product_water_timing['details']['native_calls'][name]
   row['calls']+=1;row['maximum_ms']=max(row['maximum_ms'],elapsed)
   if elapsed>16.7 and len(sys._product_water_timing['details']['outliers'])<128:
    group=args[1] if name=='_render_pose' else self.groups[args[0]]
    sys._product_water_timing['details']['outliers'].append({'method':name,
     'elapsed_ms':elapsed,'started':started,'fixture':getattr(sys,'_blueprint_qa_identity',None),
     'model':group.model_name if group is not None else None})
 setattr(SkeletonLiquidRenderer,name,timed)
for name in ('_render_pose','_payload'):water_native_timing_install(name)
world_create=WorldLiquidRenderer._create
world_create_key='WorldLiquidRenderer._create'
sys._product_water_timing['saved'].append((WorldLiquidRenderer,'_create',world_create))
sys._product_water_timing['details']['native_calls'][world_create_key]={'calls':0,'maximum_ms':0.}
def water_world_create_timed(self,group,now):
 started=time.time()
 try:return world_create(self,group,now)
 finally:
  elapsed=(time.time()-started)*1000.
  row=sys._product_water_timing['details']['native_calls'][world_create_key]
  row['calls']+=1;row['maximum_ms']=max(row['maximum_ms'],elapsed)
  if elapsed>16.7 and len(sys._product_water_timing['details']['outliers'])<128:
   sys._product_water_timing['details']['outliers'].append({'method':world_create_key,
    'elapsed_ms':elapsed,'started':started,'fixture':getattr(sys,'_blueprint_qa_identity',None),
    'model':group.model_name})
WorldLiquidRenderer._create=water_world_create_timed
_result=True
'''

TIMING_STATE = '''_result=json.dumps(sys._product_water_timing['samples'])'''
TIMING_DETAILS = '''_result=json.dumps(sys._product_water_timing['details'])'''

RESTORE_TIMING = '''if hasattr(sys,'_product_water_timing'):
 for cls,name,original in sys._product_water_timing['saved']:setattr(cls,name,original)
 del sys._product_water_timing
_result=True
'''

LOAD = '''from modern_projection.projection.debug_product_water_blueprints import source_document
from modern_projection.projection.cell import encode
identity,control,pose=%r
document=source_document(identity,control)
sys._blueprint_qa_identity='water_style_'+identity+'_'+control
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document)
s.progress=None;s.view='3d';s.page='workspace'
s.camera_view(*pose)
s.camera_pan=(.15,-.08) if pose[:2]==(0.,0.) else (0.,0.)
s.emit()
_result=json.dumps({'case':identity,'control':control,'biome':document.biome,
 'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''

SHAPES = '''row=json.loads(_result)
from modern_projection.projection.liquid_render_plan import LIQUID_NAMES,LiquidSurface
document=s.editor.document
provider=s.liquid_profile.provider_factory(document)
row['shapes']=[]
for pos,value in sorted(document.blocks.items()):
 for layer in (0,1):
  material=document.get_layer(pos,layer)
  if material[0] in LIQUID_NAMES:
   parts=provider.surface(document,pos,layer,material)
   if isinstance(parts,LiquidSurface):parts=(parts,)
   for shape in parts:
    row['shapes'].append({'position':shape.position,'layer':shape.layer,'heights':shape.heights,
     'faces':shape.faces,'texture':shape.texture_key,'flow_uv':shape.flow_uv})
row['scene_origin']=s.scene_origin;row['scene_size']=s.scene_size
_result=json.dumps(row)
'''
SCENE_STATE = workspace.STATE + SHAPES
WORLD_STATE = workspace.WORLD_STATE + SHAPES
WATER_GROUP_COUNT = workspace.WATER_OWNER + '_result=len(liquid.renderer.active)'

RESERVE = '''import json,math,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_liquid_pose_world')
factory=api.GetEngineCompFactory();player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
foot=factory.CreatePos(player).GetFootPos()
assert dimension==0 and foot and len(foot)==3
origin=(int(math.floor(foot[0]))+6,int(math.floor(foot[1]))+2,int(math.floor(foot[2]))+6)
info=factory.CreateBlockInfo(player)
region=[(origin[0]+x,origin[1]+y,origin[2]+z) for x in range(-2,4) for y in range(-2,4) for z in range(-2,4)]
for pos in region:
 front=info.GetBlockNew(pos,dimension);back=info.GetLiquidBlock(pos,dimension)
 assert front and front.get('name')=='minecraft:air',(pos,front)
 assert back is None or back.get('name')=='minecraft:air',(pos,back)
sys._liquid_pose_world={'origin':origin,'region':region,'player':player,'dimension':dimension,
 'foot_before':foot,'workspace_cells':[]}
_result=json.dumps({'origin':origin,'player':player,'dimension':dimension,'region':region,'foot':foot,
 'world_height_above_foot':2,'position_write_attempted':False})
'''

RESTORE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._liquid_pose_world
assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(saved['foot_before']))
actual=api.GetEngineCompFactory().CreatePos(saved['player']).GetFootPos()
assert actual and max(abs(actual[i]-saved['foot_before'][i]) for i in range(3))<.05,actual
_result=json.dumps({'restored':True,'foot':actual,'expected':saved['foot_before']})
'''

RESTORE_PROFILE = '''if hasattr(sys,'_product_water_saved_profile'):
 s.liquid_profile,s.grid=sys._product_water_saved_profile
 del sys._product_water_saved_profile
''' + blueprints.RESTORE
CAMERA_STATE = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
'''
CAMERA = workspace.CAMERA.replace("'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()",
                                "'position':position,'rotation':(direction[0],direction[1]+180.,0.)")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_sources(root):
    paths = [path for folder in ('behavior_pack', 'resource_pack') for path in (root / folder).rglob('*')
             if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')]
    paths += list((root / 'tools').glob('*.py'))
    paths += list((root / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
    return {path.relative_to(root).as_posix(): fingerprint(path) for path in sorted(paths)}


def snapshot_digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--launch-inputs', required=True, type=Path,
                        help='Exact source/resource snapshot saved immediately before this game launch')
    parser.add_argument('--route', action='append', choices=('editor', 'full', 'missing'))
    parser.add_argument('--case', action='append')
    parser.add_argument('--frozen', action='store_true')
    parser.add_argument('--production-default', action='store_true',
                        help='Require ordinary cold-start Session water without candidate assignment')
    parser.add_argument('--visibility-controls', action='store_true',
                        help='Hide all fixture water above the support layer and restore all three owners')
    parser.add_argument('--opaque-side-controls', action='store_true',
                        help='Measure pool UV repetition at alpha one, independently of its backdrop')
    parser.add_argument('--native-side-projection', action='store_true',
                        help='Use same-session WorldToScreenPoint samples validated against native stone pixels')
    parser.add_argument('--measure-budgets', action='store_true',
                        help='Measure game-thread owner calls without IPC or capture costs')
    parser.add_argument('--oblique-bodies', action='store_true',
                        help='Use the ordinary oblique editor pose for partial-solid bodies')
    parser.add_argument('--editor-zoom', type=float,
                        help='Explicit ordinary editor zoom for complete gallery observations')
    parser.add_argument('--reverse-view', action='store_true',
                        help='Observe the same unmodified public cells from the opposite side')
    parser.add_argument('--world-view-scale', type=float, default=1.,
                        help='Scale the declared camera distance without changing source geometry')
    parser.add_argument('--pool-view-scale', type=float,
                        help='Optional closer pool-only UV view, preserving all physical source geometry')
    parser.add_argument('--alpha-controls', action='store_true',
                        help='Frozen, fixed-geometry opacity endpoints and intermediate controls')
    parser.add_argument('--without-supports', action='store_true',
                        help='Remove public fixture support stones to exercise custom-only geometry')
    parser.add_argument('--controls', choices=('wet', 'all'), default='all')
    parser.add_argument('--extras', action='store_true', help='Animation, biome and missing occupancy transitions')
    parser.add_argument('--flow-burst-exe', type=Path,
                        help='Pinned persistent WGC helper for independent flow-direction samples')
    parser.add_argument('--flow-burst-sha256')
    parser.add_argument('--flow-burst-duration-ms', type=int, default=1200)
    parser.add_argument('--world-fixture-lift-y', type=int, default=0,
                        help='Lift the reserved world fixture, preserving all document geometry')
    parser.add_argument('--falling-skyward', action='store_true',
                        help='Observe the physical south falling face against sky for dense capture')
    parser.add_argument('--max-seconds', type=float, default=1200.)
    parser.add_argument('--max-handles', type=int, default=250000)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh evidence report')
    if bool(args.flow_burst_exe) != bool(args.flow_burst_sha256):
        parser.error('Flow burst helper and expected SHA256 must be provided together')
    if args.flow_burst_exe and args.frozen:
        parser.error('Flow direction needs animated water')
    if args.alpha_controls and not args.frozen:
        parser.error('Opacity controls require a frozen animation phase')
    if args.opaque_side_controls and not args.frozen:
        parser.error('Opaque side controls require a frozen animation phase')
    if args.native_side_projection and (not args.opaque_side_controls or not args.visibility_controls):
        parser.error('Native side projection requires independent opaque and visibility controls')
    if args.production_default and args.frozen:
        parser.error('The ordinary default entry uses animated production models')
    if not 0 <= args.world_fixture_lift_y <= 128:
        parser.error('World fixture lift must be within 0..128 blocks')
    if not .25 <= args.world_view_scale <= 1.:
        parser.error('World camera distance scale must be within .25..1')
    if args.pool_view_scale is not None and not .25 <= args.pool_view_scale <= 1.:
        parser.error('Pool camera distance scale must be within .25..1')
    if args.editor_zoom is not None and not .1 <= args.editor_zoom <= 16.:
        parser.error('Editor zoom must be within .1..16')
    if args.falling_skyward and args.world_fixture_lift_y < 8:
        parser.error('Skyward falling capture needs a fixture lift of at least 8 blocks')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT or not session.get('noactivation', {}).get('window_noactivate'):
        parser.error('Use a guarded session owned by this project')
    routes = tuple(args.route or ('editor', 'full', 'missing'))
    cases = tuple(args.case or ('source', 'low', 'flow_east', 'flow_south', 'flow_west',
                                'flow_north', 'pool', 'falling', 'wet_oak_fence'))
    controls = ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty') if args.controls == 'all' else ('wet',)
    launch_inputs = json.loads(args.launch_inputs.read_bytes())
    before_sources = snapshot_sources(base.ROOT)
    if launch_inputs.get('source_sha256') != before_sources:
        parser.error('Project source/resources changed since this game launch')
    calibration = None
    if set(routes) - {'editor'}:
        if not args.camera_calibration:
            parser.error('World captures need an independent same-session stone calibration')
        calibration = json.loads(args.camera_calibration.read_bytes())
        if (not all(calibration.get(key) is True for key in ('passed', 'completed', 'restored'))
                or calibration.get('cleanup_errors')
                or Path(calibration.get('session_file', '')).resolve() != Path(session['session_file']).resolve()):
            parser.error('Camera calibration must pass and restore in this exact session')
    report = {'schema': 1, 'completed': False, 'restored': False, 'cleanup_errors': [], 'captures': {},
              'rows': {}, 'extra_rows': {}, 'alpha_controls': {}, 'alpha_controls_requested': args.alpha_controls,
              'flow_bursts': {}, 'frozen': args.frozen,
              'routes': routes, 'cases': cases, 'controls': controls,
              'fixture_without_supports': args.without_supports,
              'production_default_requested': args.production_default,
              'visibility_controls_requested': args.visibility_controls,
              'opaque_side_controls_requested': args.opaque_side_controls,
              'native_side_projection_requested': args.native_side_projection,
              'owner_timing_requested': args.measure_budgets,
              'owned_native_assertion_checks': 0,
              'fixture_view': {'world_lift_y': args.world_fixture_lift_y,
                               'falling_skyward': args.falling_skyward,
                               'world_distance_scale': args.world_view_scale,
                               'pool_distance_scale': args.pool_view_scale,
                               'oblique_editor_bodies': args.oblique_bodies,
                               'editor_zoom': args.editor_zoom,
                               'reverse_view': args.reverse_view},
              'session_binding': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')},
              'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'product_style_accepted': False,
              'launch_source_sha256': launch_inputs['source_sha256'],
              'source_file_sha256_before': before_sources, 'source_file_sha256_after': None,
              'source_contract_sha256': snapshot_digest(before_sources), 'source_unchanged': False,
              'source_sha256': {name: fingerprint(base.ROOT / name) for name in (
                  'behavior_pack/modern_projection/projection/liquid_product_profile.py',
                  'behavior_pack/modern_projection/projection/liquid_product_resource_data.py',
                  'behavior_pack/modern_projection/projection/liquid_product_shape_data.py',
                  'behavior_pack/modern_projection/projection/debug_product_water_blueprints.py',
                  'behavior_pack/modern_projection/projection/scene.py',
                  'behavior_pack/modern_projection/projection/world_projection.py',
                  'tools/probe_product_water.py')}, 'measurements': []}
    if calibration:
        report['camera_calibration'] = {'path': str(args.camera_calibration.resolve()),
                                        'sha256': fingerprint(args.camera_calibration),
                                        'vertical_fov': calibration['vertical_fov'],
                                        'reported_fov': calibration['reported_fov'],
                                        'engine_screen': calibration['views'][0]['camera']['screen'],
                                        'capture_size': calibration['views'][0]['shown']['size']}
        if any(not calibrated_viewport_matches(view['camera'], report['camera_calibration'])
               or view['shown']['size'] != report['camera_calibration']['capture_size']
               for view in calibration['views']):
            parser.error('Camera calibration changed its FOV or viewport between controls')
    if args.native_side_projection:
        from water_native_projection import SCHEMA, UNITS, side_query_code, validate_calibration
        if set(routes) - {'editor'}:
            validate_calibration(calibration, report['session_binding'], report['source_contract_sha256'])
        report['native_side_projection'] = {'schema': SCHEMA, 'coordinate_units': UNITS, 'rows': {}}
    started = time.monotonic()
    record = lambda: base.write(args.output, report)

    def capture(label, row=None):
        if time.monotonic() - started > args.max_seconds:
            raise TimeoutError('Product-water capture budget expired')
        dialogs = [entry for entry in assertion_dialogs() if entry['pid'] == session['game_pid']]
        report['owned_native_assertion_checks'] += 1
        if dialogs:
            report['owned_native_assertions'] = dialogs
            record()
            raise RuntimeError('Owned game has a native assertion; its water captures are not qualification evidence')
        sample = dict(workspace.transport.metrics(args.session, args.owner), label=label)
        report['measurements'].append(sample)
        if sample['handles'] >= args.max_handles:
            raise RuntimeError('Native handle budget reached')
        if row is not None and row['route'] != 'editor':
            row['camera_before'] = check.run(CAMERA_STATE)
            if not camera_matches(row['camera_before'], row['camera_expected']):
                raise RuntimeError('Camera moved before water capture: ' + label)
        elif row is not None:
            row['scene_before'] = scene_capture_state(check.run(SCENE_STATE))
            if row['scene_before'] is None or row['scene_before'] != scene_capture_state(row['ready']):
                raise RuntimeError('Scene layout moved before water capture: ' + label)
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        if row is not None and row['route'] != 'editor':
            row['camera_after'] = check.run(CAMERA_STATE)
            if (not camera_matches(row['camera_after'], row['camera_expected'])
                    or not camera_matches(row['camera_after'], row['camera_before'])):
                raise RuntimeError('Camera moved during water capture: ' + label)
            report['captures'][label].update(camera_expected=row['camera_expected'],
                                            camera_before=row['camera_before'], camera_after=row['camera_after'])
            if not calibrated_viewport_matches(row['camera_after'], report['camera_calibration']):
                raise RuntimeError('World FOV/viewport changed from the stone calibration: ' + label)
            if [report['captures'][label]['width'], report['captures'][label]['height']] != report['camera_calibration']['capture_size']:
                raise RuntimeError('Native capture resolution changed from the stone calibration: ' + label)
        elif row is not None:
            row['scene_after'] = scene_capture_state(check.run(SCENE_STATE))
            report['captures'][label].update(scene_before=row['scene_before'], scene_after=row['scene_after'])
            if row['scene_before'] != row['scene_after']:
                raise RuntimeError('Scene layout moved during water capture: ' + label)
        record()

    def capture_flow_burst(label, row):
        from capture_native_burst import CaptureError, capture as native_burst
        if time.monotonic() - started > args.max_seconds:
            raise TimeoutError('Product-water flow burst budget expired')
        if row['route'] == 'editor':
            before = scene_capture_state(check.run(SCENE_STATE))
            if before is None or before != scene_capture_state(row['ready']):
                raise RuntimeError('Scene layout moved before flow burst: ' + label)
        else:
            before = check.run(CAMERA_STATE)
            if (not camera_matches(before, row['camera_expected'])
                    or not calibrated_viewport_matches(before, report['camera_calibration'])):
                raise RuntimeError('World camera moved before flow burst: ' + label)
        output = args.output.with_name(args.output.stem + '_' + label + '_burst')
        try:
            sample = native_burst(args.session, args.owner, output, args.flow_burst_exe,
                                  args.flow_burst_sha256, duration_ms=args.flow_burst_duration_ms,
                                  max_frames=240, max_gap_ms=150)
        except CaptureError as error:
            report['flow_bursts'][label] = {'row': row, 'before': before, 'after': None,
                                          'capture': error.report}
            record()
            raise
        after = (scene_capture_state(check.run(SCENE_STATE)) if row['route'] == 'editor'
                 else check.run(CAMERA_STATE))
        report['flow_bursts'][label] = {'row': row, 'before': before, 'after': after,
                                      'capture': sample}
        record()
        if before != after:
            raise RuntimeError('Physical face camera moved during flow burst: ' + label)
        if row['route'] != 'editor' and [sample['window']['width'], sample['window']['height']] != report['camera_calibration']['capture_size']:
            raise RuntimeError('Flow burst viewport differs from the same-session calibration')

    with base.Client(timeout=45) as client:
        check = blueprints.BlueprintCheck(client, args.output, 45.)
        installed = visual_saved = environment_attempted = world_saved = options_attempted = hud_attempted = timing_installed = False
        try:
            check.run(blueprints.INSTALL_PROBE)
            installed = True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old workspace', lambda value: not value['open'] and not value['transition'], check.navigation)
            report['profile'] = check.run(DEFAULT_PROFILE if args.production_default else PROFILE % (args.frozen, args.frozen))
            if args.measure_budgets:
                check.run(INSTALL_TIMING)
                timing_installed = True
            if set(routes) - {'editor'}:
                report['visual_saved'] = check.run(visuals.SAVE_VISUAL)
                visual_saved = True
                options_attempted = True
                report['capture_options'] = check.run(CAPTURE_OPTIONS)
                hud_attempted = True
                report['capture_hud'] = check.run(SAVE_HUD)
                environment_attempted = True
                report['environment'] = base.run(client, base.ENVIRONMENT, True)
                reserve = RESERVE.replace('int(math.floor(foot[1]))+2',
                    'int(math.floor(foot[1]))+%d' % (2 + args.world_fixture_lift_y))
                report['reservation'] = base.run(client, reserve, True)
                world_saved = True
                report['near_player'] = base.run(client, base.NEAR_PLAYER, True)
                expected_foot = report['near_player']['after']
                report['near_player']['replicated'] = check.wait('near-player fixture replication',
                    lambda value: value and max(abs(value[i] - expected_foot[i]) for i in range(3)) < .1,
                    lambda: check.run('_result=json.dumps(b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos())'))
                report['flow_frozen'] = base.run(client, workspace.FLOW % True, True)
                origin = tuple(report['reservation']['origin'])
                document_origin = tuple(axis - 3 for axis in origin)
                check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' % (document_origin,))

            for route in routes:
                if route == 'editor':
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('open Scene', lambda value: value['open'] and not value['transition'], check.navigation)
                elif check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close Scene', lambda value: not value['open'] and not value['transition'], check.navigation)
                for identity in cases:
                    wet_case = identity.startswith('wet_')
                    selected = controls if wet_case else tuple(value for value in controls if value in ('wet', 'dry'))
                    pose = (0., 0., 3.) if wet_case and not args.oblique_bodies else (35., 25., 4.6)
                    if identity == 'falling':
                        pose = pose[:2] + (3.,)
                    if identity in ('wet_oak_slab', 'wet_oak_stairs'):
                        pose = (-10., 10., 4.6)
                    if args.editor_zoom is not None:
                        pose = pose[:2] + (args.editor_zoom,)
                    if args.reverse_view:
                        pose = (pose[0] - 180., pose[1], pose[2])
                    for control in selected:
                        label = route + '_' + identity + '_' + control
                        load = LOAD
                        if args.without_supports:
                            load = load.replace("sys._blueprint_qa_identity=", "for pos,value in list(document.blocks.items()):\n"
                                " if value[0]=='minecraft:stone':document.set_cell(pos,('minecraft:air',0))\n"
                                "sys._blueprint_qa_identity=")
                        row = report['rows'][label] = {'route': route, 'case': identity, 'control': control,
                            'source': check.run(load % ((identity, control, pose),))}
                        if route == 'editor':
                            pan = (.15, -.08) if pose[:2] == (0., 0.) else (0., 0.)
                            row['ready'] = check.wait(label + ' settled native layout',
                                stable_scene_predicate(pose, pan, workspace.scene_ready), lambda: check.run(SCENE_STATE))
                        else:
                            check.run('s.projection_missing=%r\nb.project()\n_result=True' % (route == 'missing',))
                            row['ready'] = check.wait(label, workspace.world_ready, lambda: check.run(WORLD_STATE))
                            target = tuple(origin[i] + (.5 if i != 1 else 1.35 if wet_case else .5) for i in range(3))
                            offset = (0., 0., 12.) if wet_case else (6., 5., 8.)
                            if identity in ('wet_oak_slab', 'wet_oak_stairs'):
                                offset = (-2., 2., 12.)
                            if identity == 'falling' and args.falling_skyward:
                                offset = (0., -3., 6.)
                            scale = args.pool_view_scale if identity == 'pool' and args.pool_view_scale is not None else args.world_view_scale
                            offset = tuple(axis * scale for axis in offset)
                            if args.reverse_view:
                                offset = (-offset[0], offset[1], -offset[2])
                            row['camera_expected'] = check.run(CAMERA % ((target, offset),))
                            row['camera'] = check.wait(label + ' camera',
                                lambda value: camera_matches(value, row['camera_expected']), lambda: check.run(CAMERA_STATE))
                            row['camera']['target'] = row['camera_expected']['target']
                        time.sleep(.35)
                        capture(label, row)
                        if (args.native_side_projection and route != 'editor'
                                and identity == 'pool' and control == 'dry'):
                            opaque_label = route + '_pool_wet_side_opaque'
                            if opaque_label not in report['captures']:
                                raise RuntimeError('Native side sampling requires its earlier opaque PNG')
                            native_reading = {'before': check.run(side_query_code())}
                            native_reading.update(after=check.run(side_query_code()),
                                session_binding=report['session_binding'],
                                source_contract_sha256=report['source_contract_sha256'],
                                capture_sha256=report['captures'][opaque_label]['sha256'],
                                dry_capture_sha256=report['captures'][label]['sha256'],
                                capture_size=[report['captures'][opaque_label]['width'],
                                              report['captures'][opaque_label]['height']])
                            report['native_side_projection']['rows'][opaque_label] = native_reading
                            record()
                        if args.opaque_side_controls and identity == 'pool' and control == 'wet':
                            command = workspace.SCENE_ALPHA if route == 'editor' else workspace.WORLD_ALPHA
                            for alpha, phase in ((1., 'side_opaque'), (-1., 'side_default_restored')):
                                check.run(command % alpha + ('s.emit()\n_result=True' if route == 'editor' else ''))
                                state_command = SCENE_STATE if route == 'editor' else WORLD_STATE
                                ready = check.wait(label + ' ' + phase,
                                    lambda state: workspace.alpha_ready(state, alpha, route != 'editor'),
                                    lambda: check.run(state_command))
                                phase_row = dict(row, ready=ready, requested_alpha=alpha)
                                phase_label = label + '_' + phase
                                report['extra_rows'][phase_label] = phase_row
                                time.sleep(.35)
                                capture(phase_label, phase_row)
                        if args.visibility_controls and control == 'wet' and identity != 'drop_north':
                            previous_layer = check.run('_result=s.editor.layer')
                            check.run('s.editor.layer=2\ns.display_mode("section")\n_result=True')
                            if route != 'editor':
                                check.run('b.stop_projection()\nb.project()\n_result=True')
                            state_command = SCENE_STATE if route == 'editor' else WORLD_STATE
                            hidden = check.wait(label + ' section hides water',
                                workspace.scene_ready if route == 'editor' else workspace.world_ready,
                                lambda: check.run(state_command))
                            hidden_row = dict(row, ready=hidden)
                            hidden_row['water_groups'] = check.run('_result=len(s.liquid_preview.groups)' if route == 'editor'
                                else WATER_GROUP_COUNT)
                            if hidden_row['water_groups'] != 0:
                                raise RuntimeError('Section retained water above the support layer: ' + label)
                            report['extra_rows'][label + '_section'] = hidden_row
                            time.sleep(.35)
                            capture(label + '_section', hidden_row)
                            check.run('s.editor.layer=%r\ns.display_mode("full")\n_result=True' % previous_layer)
                            if route != 'editor':
                                check.run('b.stop_projection()\nb.project()\n_result=True')
                            restored = check.wait(label + ' section restores water',
                                workspace.scene_ready if route == 'editor' else workspace.world_ready,
                                lambda: check.run(state_command))
                            restored_row = dict(row, ready=restored)
                            restored_row['water_groups'] = check.run('_result=len(s.liquid_preview.groups)' if route == 'editor'
                                else WATER_GROUP_COUNT)
                            if restored_row['water_groups'] == 0:
                                raise RuntimeError('Section did not restore visible water: ' + label)
                            report['extra_rows'][label + '_section_restored'] = restored_row
                            time.sleep(.35)
                            capture(label + '_section_restored', restored_row)
                        if args.alpha_controls and control == 'wet' and wet_case:
                            baseline = check.run(SCENE_STATE if route == 'editor' else WORLD_STATE)
                            if (baseline['source_cells'] != row['ready']['source_cells']
                                    or baseline['shapes'] != row['ready']['shapes']):
                                raise RuntimeError('Alpha baseline changed source water geometry: ' + label)
                            holdout = report['alpha_controls'][label] = {'baseline': baseline, 'phases': {}}
                            command = workspace.SCENE_ALPHA if route == 'editor' else workspace.WORLD_ALPHA
                            for alpha, phase in workspace.ALPHA_PHASES:
                                check.run(command % alpha + ('s.emit()\n_result=True' if route == 'editor' else ''))
                                ready = check.wait(label + ' alpha ' + phase,
                                    lambda state: workspace.alpha_ready(state, alpha, route != 'editor'),
                                    lambda: check.run(SCENE_STATE if route == 'editor' else WORLD_STATE))
                                phase_row = dict(row, ready=ready)
                                phase_label = label + '_alpha_' + phase
                                time.sleep(.35)
                                capture(phase_label, phase_row)
                                holdout['phases'][phase] = dict(phase_row, requested_alpha=alpha,
                                                              capture_label=phase_label)
                            record()
                        if (control == 'wet' and args.flow_burst_exe
                                and (identity.startswith('flow_') or identity == 'falling')):
                            capture_flow_burst(label, row)
                        if control == 'wet' and args.extras:
                            row['temporal_initial'] = report['captures'][label]
                            time.sleep(.55)
                            capture(label + '_later', row)
                            if identity in ('source', 'wet_oak_fence'):
                                for biome in ('swampland', 'mangrove_swamp', 'plains'):
                                    check.run('s.set_biome(%r)\n_result=True' % biome)
                                    if route != 'editor':
                                        check.run('b.stop_projection()\nb.project()\n_result=True')
                                    state_command = SCENE_STATE if route == 'editor' else WORLD_STATE
                                    ready = check.wait(
                                        route + ' biome',
                                        lambda state: (workspace.scene_ready(state) if route == 'editor'
                                                       else workspace.world_ready(state)) and state['biome'] == biome,
                                        lambda: check.run(state_command))
                                    extra_row = report['extra_rows'][label + '_biome_' + biome] = dict(row, ready=ready)
                                    capture(label + '_biome_' + biome, extra_row)
                            elif identity == 'pool' and route == 'missing':
                                occupied = [(origin, row['source']['cells'][next(index for index, item in enumerate(row['source']['cells'])
                                             if tuple(item[0]) == (3, 3, 3))][1])]
                                report['extra_rows'][label + '_occupied_write'] = base.run(client,
                                    workspace.WRITE % native.wire(occupied), True)
                                report['extra_rows'][label + '_occupied'] = check.wait('occupied pool',
                                    lambda state: workspace.world_ready(state) and state['occupancy']['rendered_keep'] == 2
                                    and not state['occupancy']['pending'] and not state['occupancy']['changed'],
                                    lambda: check.run(WORLD_STATE))
                                capture(label + '_occupied', row)
                                report['extra_rows'][label + '_clear_write'] = base.run(client,
                                    workspace.WRITE % native.wire([]), True)
                                report['extra_rows'][label + '_restored'] = check.wait('restored pool',
                                    lambda state: workspace.world_ready(state) and state['occupancy']['rendered_keep'] != 2
                                    and not state['occupancy']['pending'] and not state['occupancy']['changed'],
                                    lambda: check.run(WORLD_STATE))
                                capture(label + '_restored', row)
                        if route != 'editor':
                            check.run('b.stop_projection()\n_result=True')
                            row['stopped'] = check.run('''_result=json.dumps({'active':s.projection_active,
 'liquid':b.projection_liquid is not None,'retired':len(b.projection_retired_liquids),
 'world_actors':len(b.projection_entities)+int(bool(b.entity))})''')
                record()
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            record()
            raise
        finally:
            actions = [('projection_stop', lambda: check.run('b.stop_projection()\n_result=True'))]
            if timing_installed:
                try:
                    report['owner_timing_ms'] = check.run(TIMING_STATE)
                    report['owner_timing_details'] = check.run(TIMING_DETAILS)
                except Exception as error:
                    report['cleanup_errors'].append('timing_state: ' + type(error).__name__ + ': ' + str(error))
                actions.append(('timing_restore', lambda: check.run(RESTORE_TIMING)))
            if world_saved:
                actions.extend((('world_clear', lambda: base.run(client, workspace.WRITE % native.wire([]), True)),
                                ('flow_restore', lambda: base.run(client, workspace.FLOW % False, True)),
                                ('player_restore', lambda: base.run(client, RESTORE_PLAYER, True)),
                                ('world_cleanup', lambda: base.run(client, workspace.QUALIFICATION_CLEAN_WORLD, True))))
            if visual_saved:
                actions.extend((('camera_restore', lambda: check.run(visuals.camera_restore_code(False))),
                                ('visual_restore', lambda: check.run('''saved=sys._blueprint_visual_saved
s.origin=saved['origin'];s.opacity=saved['opacity'];s.projection_missing=saved['missing'];s.projection_outline=saved['outline']
del sys._blueprint_visual_saved
_result=True'''))))
            if installed:
                def restore_workspace():
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close product-water Scene', lambda value: not value['open'] and not value['transition'], check.navigation)
                    return check.run(RESTORE_PROFILE)
                actions.append(('workspace_restore', restore_workspace))
            if environment_attempted:
                actions.append(('environment_restore', lambda: base.run(client,
                    workspace.guarded_cleanup(base.RESTORE_ENVIRONMENT, '_context_environment_saved'), True)))
            if hud_attempted:
                actions.append(('hud_restore', lambda: check.run(
                    workspace.guarded_cleanup(RESTORE_HUD, '_sign_visual_hud_saved'))))
            if options_attempted:
                actions.append(('capture_options_restore', lambda: check.run(
                    workspace.guarded_cleanup(RESTORE_OPTIONS, '_neighbor_visual_options_saved'))))
            for name, action in actions:
                try:
                    report[name] = action()
                except Exception as error:
                    report['cleanup_errors'].append(name + ': ' + type(error).__name__ + ': ' + str(error))
                record()
            report['restored'] = not report['cleanup_errors']
            report['source_file_sha256_after'] = snapshot_sources(base.ROOT)
            report['source_unchanged'] = before_sources == report['source_file_sha256_after']
            if not report['source_unchanged']:
                report['cleanup_errors'].append('Project source/resources changed during the capture')
                report['restored'] = False
            report['elapsed_seconds'] = time.monotonic() - started
            record()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'elapsed_seconds')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

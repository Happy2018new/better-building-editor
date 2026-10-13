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
from _session import load_session

PROFILE = '''from modern_projection.projection.liquid_product_deployment import candidate_profile
assert not hasattr(sys,'_product_water_saved_profile')
sys._product_water_saved_profile=(s.liquid_profile,s.grid)
s.liquid_profile=candidate_profile(frozen=%r)
s.grid=False
_result=json.dumps({'style':s.liquid_profile.style_version,'rules_sha256':s.liquid_profile.rules_sha256,
 'frozen':%r,'native_parity_accepted':False})
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

RESTORE_PROFILE = '''if hasattr(sys,'_product_water_saved_profile'):
 s.liquid_profile,s.grid=sys._product_water_saved_profile
 del sys._product_water_saved_profile
''' + blueprints.RESTORE


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--route', action='append', choices=('editor', 'full', 'missing'))
    parser.add_argument('--case', action='append')
    parser.add_argument('--frozen', action='store_true')
    parser.add_argument('--controls', choices=('wet', 'all'), default='all')
    parser.add_argument('--extras', action='store_true', help='Animation, biome and missing occupancy transitions')
    parser.add_argument('--max-seconds', type=float, default=1200.)
    parser.add_argument('--max-handles', type=int, default=250000)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh evidence report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT or not session.get('noactivation', {}).get('window_noactivate'):
        parser.error('Use a guarded session owned by this project')
    routes = tuple(args.route or ('editor', 'full', 'missing'))
    cases = tuple(args.case or ('source', 'low', 'flow_east', 'flow_south', 'flow_west',
                                'flow_north', 'pool', 'falling', 'wet_oak_fence'))
    controls = ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty') if args.controls == 'all' else ('wet',)
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
              'rows': {}, 'extra_rows': {}, 'frozen': args.frozen, 'routes': routes, 'cases': cases, 'controls': controls,
              'session_binding': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')},
              'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'product_style_accepted': False,
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
                                        'vertical_fov': calibration['vertical_fov']}
    started = time.monotonic()
    record = lambda: base.write(args.output, report)

    def capture(label):
        if time.monotonic() - started > args.max_seconds:
            raise TimeoutError('Product-water capture budget expired')
        sample = dict(workspace.transport.metrics(args.session, args.owner), label=label)
        report['measurements'].append(sample)
        if sample['handles'] >= args.max_handles:
            raise RuntimeError('Native handle budget reached')
        report['captures'][label] = base.capture(args.session, args.owner,
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.capture_exe)
        record()

    with base.Client(timeout=45) as client:
        check = blueprints.BlueprintCheck(client, args.output, 45.)
        installed = visual_saved = environment_attempted = world_saved = False
        try:
            check.run(blueprints.INSTALL_PROBE)
            installed = True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old workspace', lambda value: not value['open'] and not value['transition'], check.navigation)
            report['profile'] = check.run(PROFILE % (args.frozen, args.frozen))
            if set(routes) - {'editor'}:
                report['visual_saved'] = check.run(visuals.SAVE_VISUAL)
                visual_saved = True
                environment_attempted = True
                report['environment'] = base.run(client, base.ENVIRONMENT, True)
                report['reservation'] = base.run(client, RESERVE, True)
                world_saved = True
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
                    pose = (0., 0., 3.) if wet_case else (35., 25., 4.6)
                    for control in selected:
                        label = route + '_' + identity + '_' + control
                        row = report['rows'][label] = {'route': route, 'case': identity, 'control': control,
                            'source': check.run(LOAD % ((identity, control, pose),))}
                        if route == 'editor':
                            row['ready'] = check.wait(label, workspace.scene_ready, lambda: check.run(SCENE_STATE))
                        else:
                            check.run('s.projection_missing=%r\nb.project()\n_result=True' % (route == 'missing',))
                            row['ready'] = check.wait(label, workspace.world_ready, lambda: check.run(WORLD_STATE))
                            target = tuple(origin[i] + (.5 if i != 1 else 1.35 if wet_case else .5) for i in range(3))
                            offset = (0., 0., 12.) if wet_case else (6., 5., 8.)
                            row['camera'] = check.run(workspace.CAMERA % ((target, offset),))
                        time.sleep(.35)
                        capture(label)
                        if control == 'wet' and args.extras:
                            row['temporal_initial'] = report['captures'][label]
                            time.sleep(.55)
                            capture(label + '_later')
                            if route == 'editor' and identity in ('source', 'wet_oak_fence'):
                                for biome in ('swampland', 'mangrove_swamp', 'plains'):
                                    check.run('s.set_biome(%r)\n_result=True' % biome)
                                    report['extra_rows'][label + '_biome_' + biome] = check.wait(
                                        'Scene biome', lambda state: workspace.scene_ready(state) and state['biome'] == biome,
                                        lambda: check.run(SCENE_STATE))
                                    capture(label + '_biome_' + biome)
                            elif identity == 'pool' and route == 'missing':
                                occupied = [(origin, row['source']['cells'][next(index for index, item in enumerate(row['source']['cells'])
                                             if tuple(item[0]) == (3, 3, 3))][1])]
                                report['extra_rows'][label + '_occupied_write'] = base.run(client,
                                    workspace.WRITE % native.wire(occupied), True)
                                report['extra_rows'][label + '_occupied'] = check.wait('occupied pool',
                                    lambda state: workspace.world_ready(state) and state['occupancy']['rendered_keep'] == 2
                                    and not state['occupancy']['pending'] and not state['occupancy']['changed'],
                                    lambda: check.run(WORLD_STATE))
                                capture(label + '_occupied')
                                report['extra_rows'][label + '_clear_write'] = base.run(client,
                                    workspace.WRITE % native.wire([]), True)
                                report['extra_rows'][label + '_restored'] = check.wait('restored pool',
                                    lambda state: workspace.world_ready(state) and state['occupancy']['rendered_keep'] != 2
                                    and not state['occupancy']['pending'] and not state['occupancy']['changed'],
                                    lambda: check.run(WORLD_STATE))
                                capture(label + '_restored')
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
            if world_saved:
                actions.extend((('world_clear', lambda: base.run(client, workspace.WRITE % native.wire([]), True)),
                                ('flow_restore', lambda: base.run(client, workspace.FLOW % False, True)),
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
            for name, action in actions:
                try:
                    report[name] = action()
                except Exception as error:
                    report['cleanup_errors'].append(name + ': ' + type(error).__name__ + ': ' + str(error))
                record()
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic() - started
            record()
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'elapsed_seconds')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

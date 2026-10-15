"""Capture public cauldron fixtures through ordinary editor and projection owners.

Runs only on an already owner-bound background instance. Actual pixels remain
separate from submission and lifetime checks; every failure is retained.
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
import probe_product_water as water
import verify_debug_blueprints as blueprints
import verify_debug_visuals as visuals
from _session import load_session
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SAVE_HUD, RESTORE_HUD

PROFILE = '''from modern_projection.projection.cauldron_profile import candidate_profile
assert not hasattr(sys,'_product_cauldron_saved')
sys._product_cauldron_saved=(s.cauldron_profile,s.grid,s.liquid_profile,s.item_profile)
s.cauldron_profile=candidate_profile();s.grid=False
# Keep this fixture's one companion independently observable.
s.liquid_profile=None;s.item_profile=None
_result=json.dumps({'identity':s.cauldron_profile.identity,'default_enabled':False})
'''
PRODUCTION_PROFILE = '''from modern_projection.projection.cauldron_deployment import production_profile
assert not hasattr(sys,'_product_cauldron_saved')
sys._product_cauldron_saved=(s.cauldron_profile,s.grid,s.liquid_profile,s.item_profile)
expected=production_profile('3.10.0.420447')
assert s.cauldron_profile is not None and s.cauldron_profile.identity==expected.identity
s.grid=False
_result=json.dumps({'identity':s.cauldron_profile.identity,'default_enabled':True})
'''
LOAD = '''from modern_projection.projection.debug_cauldron_blueprints import source_document,VISUAL_CASE
from modern_projection.projection.cell import encode
identity,control=%r
document=source_document(identity,control)
sys._blueprint_qa_identity='cauldrons_'+identity+'_'+control
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document);s.progress=None;s.view='3d';s.page='workspace'
s.camera_view(*VISUAL_CASE['camera']['editor']);s.camera_pan=(0.,0.);s.emit()
_result=json.dumps({'identity':identity,'control':control,'biome':document.biome,
 'camera':VISUAL_CASE['camera'],
 'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
GALLERY_LOAD = '''from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_cauldron_blueprints import METADATA,VISUAL_CASE,CASES
from modern_projection.projection.cell import encode
document=build(METADATA[0])
sys._blueprint_qa_identity='cauldrons_gallery_filled'
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document);s.progress=None;s.view='3d';s.page='workspace'
pitch,yaw,zoom=VISUAL_CASE['camera']['editor']
camera=(pitch,yaw,zoom*max(VISUAL_CASE['size'])/max(document.size))
s.camera_view(*camera);s.camera_pan=(0.,0.);s.emit()
_result=json.dumps({'identity':'gallery','control':'filled','biome':document.biome,
 'camera':{'editor':camera},'expected_cauldron_groups':len(CASES),
 'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
COMPATIBILITY_LOAD = '''from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_compatibility_blueprints import VISUAL_CASES
from modern_projection.projection.cell import encode
identity=%r
document=build(identity)
sys._blueprint_qa_identity=identity
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document);s.progress=None;s.view='3d';s.page='workspace'
case=VISUAL_CASES[identity]
pitch,yaw,zoom=case['camera']['editor']
camera=(pitch,yaw,zoom*max(case['size'])/max(document.size))
s.camera_view(*camera);s.camera_pan=(0.,0.);s.emit()
_result=json.dumps({'identity':identity,'control':'filled','biome':document.biome,
 'camera':{'editor':camera},'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
SCENE_STATE = blueprints.STATUS + '''row=json.loads(_result)
p=s.cauldron_preview;c=s.cauldron_controls
row['cauldron']={'owned':p is not None and c is not None,
 'ready':p is not None and p.published==p.signature(),
 'pending':c.pending if c is not None else True,
 'error':str(p.error or c.error or s.cauldron_error) if p is not None and c is not None else '',
 'groups':list(p.groups.values()) if p is not None else [],
 'requests':[]}
if c is not None:
 for key,entry in sorted(c.registry.items(),key=lambda row:repr(row[0])):
  renderer=entry.get('renderer')
  row['cauldron']['requests'].append({'key':repr(key),'geometry':entry.get('geometry'),
   'visible':renderer.visible if renderer else None,'poses':renderer.poses if renderer else None,
   'uniforms':renderer.uniforms if renderer else None,
   'positions':[ref.current.GetGlobalPosition() if ref.current else None for ref in entry['dolls']],
   'sizes':[ref.current.GetSize() if ref.current else None for ref in entry['dolls']]})
row['pose']=s.camera_pose;row['pan']=s.camera_pan;row['scene_origin']=s.scene_origin
row['scene_size']=s.scene_size;row['screen']=b.factory.CreateGame(b.level).GetScreenSize()
row['display']={'mode':s.current_display_mode(),'layer':s.editor.layer,
 'hidden':sorted(s.editor.hidden_layers)}
row['biome']=s.editor.document.biome
row['source']=[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())]
_result=json.dumps(row)
'''
WORLD_STATE = workspace.WORLD_STATE
CAMERA_POINTS = '''cam=b.factory.CreateCamera(b.level)
origin=%r
points=[]
for x in (0.,.125,.5,.875,1.):
 for y in (0.,.25,.5,.75,1.):
  for z in (0.,.125,.5,.875,1.):
   point=tuple(origin[i]+(x,y,z)[i] for i in range(3))
   points.append({'local':(x,y,z),'screen':cam.WorldToScreenPoint(*point)})
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'points':points,'screen':b.factory.CreateGame(b.level).GetScreenSize()})
'''
RESTORE_PROFILE = '''if hasattr(sys,'_product_cauldron_saved'):
 s.cauldron_profile,s.grid,s.liquid_profile,s.item_profile=sys._product_cauldron_saved
 del sys._product_cauldron_saved
''' + blueprints.RESTORE


def scene_ready(state):
    data = state['cauldron']
    if data['error']:
        raise RuntimeError('Cauldron Scene failed: ' + data['error'])
    return (blueprints.editor_preview_ready(state, state['expected_metadata'],
             state['expected_editor_id'], state['expected_document_id']) and
            data['owned'] and data['ready'] and not data['pending'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--launch-inputs', required=True, type=Path)
    parser.add_argument('--route', action='append', choices=('editor', 'full', 'missing'))
    parser.add_argument('--case', action='append')
    parser.add_argument('--controls', choices=('filled', 'all'), default='all')
    parser.add_argument('--extras', action='store_true')
    parser.add_argument('--visibility', action='store_true')
    parser.add_argument('--gallery', action='store_true')
    parser.add_argument('--production', action='store_true')
    parser.add_argument('--biome-switch', action='store_true')
    parser.add_argument('--compat-gallery', action='append')
    parser.add_argument('--reserve-height', type=int, default=2)
    parser.add_argument('--max-handles', type=int, default=350000)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh evidence report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT or not session.get('noactivation', {}).get('window_noactivate'):
        parser.error('Use the guarded background instance belonging to this project')
    sources = water.snapshot_sources(base.ROOT)
    launch = json.loads(args.launch_inputs.read_bytes())
    loaded_files = lambda values:dict((key,value) for key,value in values.items()
                                     if key.startswith(('behavior_pack/','resource_pack/')))
    if loaded_files(launch['source_sha256']) != loaded_files(sources):
        parser.error('Source/resources changed since launch')
    routes = args.route or ('editor', 'full', 'missing')
    cases = args.case or ('lava1', 'lava6', 'custom_red', 'potion_43_0')
    controls = ('filled', 'empty') if args.controls == 'all' else ('filled',)
    report = {'schema': 1, 'completed': False, 'restored': False, 'cleanup_errors': [],
              'captures': {}, 'rows': {}, 'extras': {}, 'measurements': [],
              'fixture': 'test.entities.cauldrons', 'routes': routes, 'cases': cases,
              'session': {key: session[key] for key in ('id','owner','session_file','game_pid','game_identity')},
              'source_sha256': sources, 'launch_source_sha256': launch['source_sha256'],
              'pixel_acceptance_claimed': False}
    started = time.monotonic()

    def record():
        base.write(args.output, report)

    with base.Client(timeout=40) as client:
        check = blueprints.BlueprintCheck(client, args.output, 45.)
        installed = visual_saved = environment = world_saved = options = hud = False
        try:
            check.run(blueprints.INSTALL_PROBE);installed = True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old editor', lambda row:not row['open'] and not row['transition'], check.navigation)
            report['profile'] = check.run(PRODUCTION_PROFILE if args.production else PROFILE)
            if set(routes)-{'editor'}:
                report['saved_visual'] = check.run(visuals.SAVE_VISUAL);visual_saved = True
                options = True;report['options'] = check.run(CAPTURE_OPTIONS)
                hud = True;report['hud'] = check.run(SAVE_HUD)
                environment = True;report['environment'] = base.run(client, base.ENVIRONMENT, True)
                reserve=water.RESERVE.replace('int(math.floor(foot[1]))+2',
                                             'int(math.floor(foot[1]))+%d' % args.reserve_height)
                reserve=reserve.replace("'world_height_above_foot':2",
                                        "'world_height_above_foot':%d" % args.reserve_height)
                report['reserve'] = base.run(client, reserve, True);world_saved = True
                report['flow'] = base.run(client, workspace.FLOW % True, True)
                origin = tuple(report['reserve']['origin'])
                document_origin = tuple(axis-3 for axis in origin)
                check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' % (document_origin,))

            def frame(label, row):
                metric = workspace.transport.metrics(args.session, args.owner)
                report['measurements'].append(dict(metric, label=label))
                if metric['handles'] >= args.max_handles:
                    raise RuntimeError('Native handle budget reached')
                state_code = SCENE_STATE if row['route'] == 'editor' else CAMERA_POINTS % (origin,)
                before = check.run(state_code)
                image = base.capture(args.session, args.owner,
                    args.output.with_name(args.output.stem+'_'+label+'.png'), args.capture_exe)
                after = check.run(state_code)
                image.update(before=before, after=after)
                report['captures'][label] = image;record()
                if row['route'] == 'editor':
                    stable_keys = ('pose','pan','scene_origin','scene_size','screen','source','biome')
                else:
                    stable_keys = ('position','rotation','screen')
                if any(before[key] != after[key] for key in stable_keys):
                    raise RuntimeError('Layout/camera changed during capture: '+label)

            def settled_scene():
                previous = [None]
                def accept(state):
                    if not scene_ready(state):
                        previous[0] = None
                        return False
                    value = tuple(state[key] for key in ('pose','pan','scene_origin','scene_size','screen','source'))
                    same = previous[0] == value
                    previous[0] = value
                    return same
                return accept

            for route in routes:
                if route == 'editor':
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('editor open', lambda row:row['open'] and not row['transition'], check.navigation)
                elif check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('editor close', lambda row:not row['open'] and not row['transition'], check.navigation)
                for identity in cases:
                    for control in controls:
                        label = route+'_'+identity+'_'+control
                        row = report['rows'][label] = {'route':route,'case':identity,'control':control,
                                                       'source':check.run(LOAD % ((identity,control),))}
                        if route == 'editor':
                            row['ready'] = check.wait(label, settled_scene(), lambda:check.run(SCENE_STATE))
                        else:
                            check.run('s.projection_missing=%r\nb.project()\n_result=True' % (route=='missing',))
                            row['ready'] = check.wait(label, workspace.world_ready, lambda:check.run(WORLD_STATE))
                            target = tuple(origin[i]+(.65 if i==1 else .5) for i in range(3))
                            row['camera'] = check.run(water.CAMERA % ((target,tuple(row['source']['camera']['world_offset'])),))
                            check.wait('camera settle', lambda value:water.camera_matches(value,row['camera']),
                                       lambda:check.run(water.CAMERA_STATE))
                        time.sleep(.2);frame(label,row)
                        if args.biome_switch and identity == 'water6' and control == 'filled':
                            for biome in ('swampland','plains'):
                                changed=check.run('''from modern_projection.projection import biomes
s.set_biome(%r)
color,unused=biomes.water_appearance(s.editor.document.biome)
_result=json.dumps({'biome':s.editor.document.biome,'color':color})''' % biome)
                                expected_color=(changed['color'][0]*65536+changed['color'][1]*256+changed['color'][2])
                                def tinted_ready(state):
                                    if state['biome'] != biome:
                                        return False
                                    if route == 'editor':
                                        return (scene_ready(state) and state['cauldron']['groups'] and
                                                all(group[3][3][2]==expected_color for group in state['cauldron']['groups']))
                                    return (workspace.world_ready(state) and state['liquid_groups'] and
                                            all(group['group'][3][3][2]==expected_color for group in state['liquid_groups']))
                                ready=check.wait('cauldron biome '+biome,tinted_ready,
                                                 lambda:check.run(SCENE_STATE if route=='editor' else WORLD_STATE))
                                report['extras'][label+'_biome_'+biome]={'changed':changed,'ready':ready}
                                frame(label+'_biome_'+biome,row)
                        if args.extras and control == 'filled':
                            time.sleep(.65);frame(label+'_later',row)
                            if route == 'missing':
                                cell = next(value for position,value in row['source']['cells'] if tuple(position)==(3,3,3))
                                report['extras'][label+'_write'] = base.run(client,workspace.WRITE % native.wire([(origin,cell)]),True)
                                report['extras'][label+'_occupied'] = check.wait('occupied cauldron',
                                    lambda state:workspace.world_ready(state) and not state['occupancy']['rendered_keep'] & 1
                                    and not state['occupancy']['pending'],lambda:check.run(WORLD_STATE))
                                frame(label+'_occupied',row)
                                report['extras'][label+'_clear'] = base.run(client,workspace.WRITE % native.wire([]),True)
                                report['extras'][label+'_restored'] = check.wait('restored cauldron',
                                    lambda state:workspace.world_ready(state) and bool(state['occupancy']['rendered_keep'] & 1)
                                    and not state['occupancy']['pending'],lambda:check.run(WORLD_STATE))
                                frame(label+'_restored',row)
                        if args.visibility and route == 'editor' and control == 'filled':
                            for mode in ('section', 'hidden', 'restored'):
                                if mode == 'section':
                                    code = "s.layer(2)\ns.display_mode('section')\n_result=True"
                                elif mode == 'hidden':
                                    code = "s.display_mode('full')\ns.toggle_layer('hide',3)\n_result=True"
                                else:
                                    code = "s.toggle_layer('hide',3)\ns.layer(3)\ns.display_mode('full')\n_result=True"
                                check.run(code)
                                def visible_ready(state):
                                    return (scene_ready(state) and
                                            bool(state['cauldron']['groups']) == (mode == 'restored') and
                                            sum(part['common_cells'] for part in state['parts']) ==
                                            (2 if mode == 'restored' else 1))
                                report['extras'][label+'_'+mode] = check.wait(
                                    'cauldron '+mode,visible_ready,lambda:check.run(SCENE_STATE))
                                frame(label+'_'+mode,row)
                        if route != 'editor':
                            check.run('b.stop_projection()\n_result=True')
                record()
            if args.gallery:
                if not check.navigation()['open']:
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('gallery editor open',lambda value:value['open'] and not value['transition'],check.navigation)
                label='editor_gallery_filled'
                row=report['rows'][label]={'route':'editor','case':'gallery','control':'filled',
                                           'source':check.run(GALLERY_LOAD)}
                row['ready']=check.wait('public cauldron gallery',settled_scene(),lambda:check.run(SCENE_STATE))
                if len(row['ready']['cauldron']['groups']) != row['source']['expected_cauldron_groups']:
                    raise RuntimeError('Public gallery did not publish every cauldron appearance')
                frame(label,row)
            for identity in args.compat_gallery or ():
                if not check.navigation()['open']:
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('compatibility editor open',lambda value:value['open'] and not value['transition'],check.navigation)
                label='editor_'+identity+'_filled'
                row=report['rows'][label]={'route':'editor','case':identity,'control':'filled',
                                           'source':check.run(COMPATIBILITY_LOAD % identity)}
                row['ready']=check.wait('public compatibility gallery',settled_scene(),lambda:check.run(SCENE_STATE))
                frame(label,row)
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error);record();raise
        finally:
            actions = [('projection_stop',lambda:check.run('b.stop_projection()\n_result=True'))]
            if world_saved:
                actions.extend((('world_clear',lambda:base.run(client,workspace.WRITE % native.wire([]),True)),
                                ('flow_restore',lambda:base.run(client,workspace.FLOW % False,True)),
                                ('world_cleanup',lambda:base.run(client,workspace.QUALIFICATION_CLEAN_WORLD,True))))
            if visual_saved:
                actions.extend((('camera_restore',lambda:check.run(visuals.camera_restore_code(False))),
                    ('visual_restore',lambda:check.run('''saved=sys._blueprint_visual_saved
s.origin=saved['origin'];s.opacity=saved['opacity'];s.projection_missing=saved['missing'];s.projection_outline=saved['outline']
del sys._blueprint_visual_saved
_result=True'''))))
            if installed:
                def restore_workspace():
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close cauldron editor',lambda row:not row['open'] and not row['transition'],check.navigation)
                    return check.run(RESTORE_PROFILE)
                actions.append(('workspace_restore',restore_workspace))
            if environment:
                actions.append(('environment_restore',lambda:base.run(client,
                    workspace.guarded_cleanup(base.RESTORE_ENVIRONMENT,'_context_environment_saved'),True)))
            if hud:
                actions.append(('hud_restore',lambda:check.run(workspace.guarded_cleanup(RESTORE_HUD,'_sign_visual_hud_saved'))))
            if options:
                actions.append(('options_restore',lambda:check.run(workspace.guarded_cleanup(RESTORE_OPTIONS,'_neighbor_visual_options_saved'))))
            for name, action in actions:
                try:
                    report[name] = action()
                except Exception as error:
                    report['cleanup_errors'].append(name+': '+type(error).__name__+': '+str(error))
                record()
            report['source_unchanged'] = sources == water.snapshot_sources(base.ROOT)
            if not report['source_unchanged']:
                report['cleanup_errors'].append('Sources/resources changed during capture')
            report['restored'] = not report['cleanup_errors']
            report['elapsed_seconds'] = time.monotonic()-started;record()
    print(json.dumps({key:report[key] for key in ('completed','restored','elapsed_seconds')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

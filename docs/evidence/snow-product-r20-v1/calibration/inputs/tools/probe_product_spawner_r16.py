"""Observe public spawner badges through ordinary editor/full/missing owners."""
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

PROFILE = '''from modern_projection.projection.spawner_marker import candidate_profile,production_profile
assert not hasattr(sys,'_spawner_qa_saved')
sys._spawner_qa_saved=(s.spawner_profile,s.grid,s.liquid_profile,s.item_profile)
production=%r
if production:
 expected=production_profile(b.engine_version)
 assert expected is not None and s.spawner_profile==expected
s.grid=False;s.liquid_profile=None;s.item_profile=None
_result=json.dumps({'engine':b.engine_version,'production_default':production})
'''
LOAD = '''from modern_projection.projection.debug_spawner_blueprints import source_document,VISUAL_CASE
from modern_projection.projection.cell import encode
from modern_projection.projection.spawner_marker import candidate_profile
identity,enabled,production=%r
document=source_document(identity)
if not production:s.spawner_profile=candidate_profile() if enabled else None
sys._blueprint_qa_identity='spawners_'+identity+'_'+str(enabled)
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':document.name,'size':document.size,'blocks':len(document.blocks)},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(document);s.progress=None;s.view='3d';s.page='workspace'
s.camera_view(*VISUAL_CASE['camera']['editor']);s.camera_pan=(0.,0.);s.emit()
_result=json.dumps({'case':identity,'camera':VISUAL_CASE['camera'],
 'cells':[(pos,encode(value)) for pos,value in sorted(document.blocks.items())]})
'''
SCENE_STATE = blueprints.STATUS + '''row=json.loads(_result)
from modern_projection.projection.cell import encode
row.update(pose=s.camera_pose,pan=s.camera_pan,scene_origin=s.scene_origin,scene_size=s.scene_size,
 screen=b.factory.CreateGame(b.level).GetScreenSize(),
 display={'mode':s.current_display_mode(),'layer':s.editor.layer,'hidden':sorted(s.editor.hidden_layers)},
 source=[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())])
_result=json.dumps(row)
'''
WORLD_STATE = '''from modern_projection.projection.cell import encode
work=b.projection_work;tracker=b.projection_occupancy
_result=json.dumps({'active':s.projection_active,'ready':work is not None and work.ready,
 'current':work is not None and work.serial==b.projection_serial and
  work.document.blocks==s.editor.document.blocks,'error':str(work.error) if work is not None and work.error else None,
 'occupancy':{'rendered_keep':tracker.rendered[tracker.index((3,3,3))],
  'pending':tracker.pending_model is not None or tracker.attaching,'failed':tracker.failed} if tracker else None,
 'source':[(pos,encode(value)) for pos,value in sorted(s.editor.document.blocks.items())]})
'''
RESTORE = '''s.spawner_profile,s.grid,s.liquid_profile,s.item_profile=sys._spawner_qa_saved
del sys._spawner_qa_saved
''' + blueprints.RESTORE


def scene_ready(row):
    return blueprints.editor_preview_ready(row, row['expected_metadata'],
                                           row['expected_editor_id'], row['expected_document_id'])


def world_ready(row):
    if row['error'] or (row['occupancy'] and row['occupancy']['failed']):
        raise RuntimeError('Spawner projection failed: ' + repr(row))
    return row['active'] and row['ready'] and row['current']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--launch-inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--case', action='append')
    parser.add_argument('--route', action='append', choices=('editor','full','missing'))
    parser.add_argument('--visibility', action='store_true')
    parser.add_argument('--occupancy', action='store_true')
    parser.add_argument('--production-default', action='store_true')
    parser.add_argument('--visibility-followup', action='store_true',
                        help='Capture retained geometry again without resubmitting it')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output')
    project = args.project.resolve(strict=True)
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != project:
        parser.error('Project does not own this instance')
    sources = water.snapshot_sources(project)
    launch = json.loads(args.launch_inputs.read_bytes())
    if sources != launch['source_sha256']:
        parser.error('Project changed since frozen launch')
    report = {'schema':1,'completed':False,'restored':False,'cleanup_errors':[],
              'source_sha256':sources,'fixture':'test.entities.spawners',
              'captures':{},'rows':{},'extras':{},'pixel_acceptance_claimed':False,
              'session':{key:session[key] for key in ('id','owner','game_pid','game_identity')}}
    cases = args.case or ('mob_spawner_empty','mob_spawner_pig_spawn_egg','mob_spawner_unknown',
                          'trial_spawner_empty','trial_spawner_pig_spawn_egg','trial_spawner_unknown')
    routes = args.route or ('editor','full','missing')
    controls = (True,) if args.production_default else (True,False)
    started = time.monotonic()
    record = lambda:base.write(args.output, report)
    with base.Client(timeout=40) as client:
        check = blueprints.BlueprintCheck(client,args.output,50.)
        installed = saved_visual = world_saved = options = hud = environment = False
        try:
            check.run(blueprints.INSTALL_PROBE);installed=True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old editor',lambda value:not value['open'] and not value['transition'],check.navigation)
            report['profile']=check.run(PROFILE % args.production_default)
            if set(routes)-{'editor'}:
                report['saved_visual']=check.run(visuals.SAVE_VISUAL);saved_visual=True
                options=True;report['options']=check.run(CAPTURE_OPTIONS)
                hud=True;report['hud']=check.run(SAVE_HUD)
                environment=True;report['environment']=base.run(client,base.ENVIRONMENT,True)
                reserve=water.RESERVE.replace('int(math.floor(foot[1]))+2','int(math.floor(foot[1]))+32')
                report['reserve']=base.run(client,reserve,True);world_saved=True
                origin=tuple(report['reserve']['origin'])
                check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' %
                          (tuple(value-3 for value in origin),))

            def frame(label,route):
                code=SCENE_STATE if route=='editor' else water.CAMERA_STATE
                before=check.run(code)
                receipt=base.capture(args.session,args.owner,args.output.with_name(args.output.stem+'_'+label+'.png'),args.capture_exe)
                after=check.run(code)
                stable=('pose','pan','scene_origin','scene_size','screen','source') if route=='editor' else ('position','rotation','screen')
                if any(before[key]!=after[key] for key in stable):
                    raise RuntimeError('Camera/source changed during capture: '+label)
                receipt.update(before=before,after=after)
                report['captures'][label]=receipt;record()

            for route in routes:
                if route=='editor':
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('open editor',lambda value:value['open'] and not value['transition'],check.navigation)
                elif check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close editor',lambda value:not value['open'] and not value['transition'],check.navigation)
                for identity in cases:
                    for enabled in controls:
                        label=route+'_'+identity+('_badge' if enabled else '_native')
                        row=report['rows'][label]={'source':check.run(LOAD % ((identity,enabled,args.production_default),))}
                        if route=='editor':
                            row['ready']=check.wait(label,scene_ready,lambda:check.run(SCENE_STATE))
                        else:
                            check.run('s.projection_missing=%r\nb.project()\n_result=True' % (route=='missing',))
                            row['ready']=check.wait(label,world_ready,lambda:check.run(WORLD_STATE))
                            target=tuple(origin[i]+(.65 if i==1 else .5) for i in range(3))
                            row['camera']=check.run(water.CAMERA % ((target,tuple(row['source']['camera']['world_offset'])),))
                            check.wait('camera settle',lambda value:water.camera_matches(value,row['camera']),
                                       lambda:check.run(water.CAMERA_STATE))
                        time.sleep(.3);frame(label,route)
                        if args.visibility and route=='editor' and enabled:
                            for mode,code in (
                                ('hidden',"s.toggle_layer('hide',3)"),
                                ('restored',"s.toggle_layer('hide',3)"),
                                ('section',"s.layer(2)\ns.display_mode('section')"),
                                ('full',"s.layer(3)\ns.display_mode('full')")):
                                check.run(code+'\n_result=True')
                                report['extras'][label+'_'+mode]=check.wait(mode,scene_ready,lambda:check.run(SCENE_STATE))
                                time.sleep(.3);frame(label+'_'+mode,route)
                                if args.visibility_followup and mode in ('hidden', 'section'):
                                    for delay in (.5, 1.5):
                                        time.sleep(delay)
                                        frame(label+'_'+mode+'_later_'+str(delay),route)
                        if args.occupancy and route=='missing' and enabled:
                            cell=next(value for position,value in row['source']['cells'] if tuple(position)==(3,3,3))
                            report['extras'][label+'_write']=base.run(client,workspace.WRITE % native.wire([(origin,cell)]),True)
                            report['extras'][label+'_occupied']=check.wait('occupied',lambda value:world_ready(value) and
                                not value['occupancy']['pending'] and not value['occupancy']['rendered_keep'] & 1,
                                lambda:check.run(WORLD_STATE))
                            time.sleep(.3);frame(label+'_occupied',route)
                            report['extras'][label+'_clear']=base.run(client,workspace.WRITE % native.wire([]),True)
                            report['extras'][label+'_restored']=check.wait('restored',lambda value:world_ready(value) and
                                not value['occupancy']['pending'] and bool(value['occupancy']['rendered_keep'] & 1),
                                lambda:check.run(WORLD_STATE))
                            time.sleep(.3);frame(label+'_restored',route)
                        if route!='editor':check.run('b.stop_projection()\n_result=True')
            report['completed']=True
        except Exception as error:
            report['error']=type(error).__name__+': '+str(error);record();raise
        finally:
            actions=[('projection_stop',lambda:check.run('b.stop_projection()\n_result=True'))]
            if world_saved:
                actions.extend((('world_clear',lambda:base.run(client,workspace.WRITE % native.wire([]),True)),
                                ('world_restore',lambda:base.run(client,workspace.QUALIFICATION_CLEAN_WORLD,True))))
            if saved_visual:
                actions.extend((('camera_restore',lambda:check.run(visuals.camera_restore_code(False))),
                    ('visual_restore',lambda:check.run("saved=sys._blueprint_visual_saved\ns.origin=saved['origin'];s.opacity=saved['opacity'];s.projection_missing=saved['missing'];s.projection_outline=saved['outline']\ndel sys._blueprint_visual_saved\n_result=True"))))
            if installed:
                def restore_workspace():
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('close editor',lambda value:not value['open'] and not value['transition'],check.navigation)
                    return check.run(RESTORE)
                actions.append(('workspace_restore',restore_workspace))
            if environment:actions.append(('environment_restore',lambda:base.run(client,workspace.guarded_cleanup(base.RESTORE_ENVIRONMENT,'_context_environment_saved'),True)))
            if hud:actions.append(('hud_restore',lambda:check.run(workspace.guarded_cleanup(RESTORE_HUD,'_sign_visual_hud_saved'))))
            if options:actions.append(('options_restore',lambda:check.run(workspace.guarded_cleanup(RESTORE_OPTIONS,'_neighbor_visual_options_saved'))))
            for label,action in actions:
                try:report[label]=action()
                except Exception as error:report['cleanup_errors'].append(label+': '+type(error).__name__+': '+str(error))
                record()
            report['source_unchanged']=sources==water.snapshot_sources(project)
            if not report['source_unchanged']:report['cleanup_errors'].append('Frozen project changed')
            report['restored']=not report['cleanup_errors']
            report['elapsed_seconds']=time.monotonic()-started;record()
    print(json.dumps({key:report[key] for key in ('completed','restored','elapsed_seconds')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())

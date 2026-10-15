"""Minimal owned editor water controls with actual native model/layout readback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


STATE = '''rows=[]
host=navigator.top._host
def native_ref_path(fiber,ref):
 if fiber.ref is ref:return fiber.native_path
 for child in fiber.child_fibers:
  found=native_ref_path(child,ref)
  if found:return found
 return None
def control_state(ref):
 control=ref.current
 if control is None:return None
 path=native_ref_path(host._root_fiber,ref)
 chain=[]
 if path:
  pieces=path.split('/')
  for length in range(2,len(pieces)+1):
   parent_path='/'.join(pieces[:length])
   parent=host.GetBaseUIControl(parent_path)
   if parent is not None:
    chain.append({'path':parent_path,'visible':parent.GetVisible(),
     'position':parent.GetPosition(),'global':parent.GetGlobalPosition(),'size':parent.GetSize()})
 return {'path':path,'visible':control.GetVisible(),'position':control.GetPosition(),
  'global':control.GetGlobalPosition(),'size':control.GetSize(),'chain':chain}
for key,entry in sorted(s.liquid_controls.registry.items(),key=lambda item:repr(item[0])):
 renderer=entry.get('renderer')
 row={'key':repr(key),'geometry':entry.get('geometry'),'clip_offset':entry.get('clip_offset'),
  'ready':entry.get('ready_request') is not None,'banks':[]}
 if renderer is not None:
  row.update(front=renderer.front,error=renderer.error,pending=renderer.pending is not None,
             cached_ids=renderer.ids,visible=renderer.visible)
  for slot,doll in enumerate(renderer.dolls):
   actual=doll.GetModelId()
   cached=renderer.ids[slot]
   group=renderer.groups[slot]
   row['banks'].append({'slot':slot,'cached_id':cached,'actual_id':actual,
    'model':group.model_name if group is not None else None,'pose':renderer.poses[slot],
    'cached_uniforms':renderer.uniforms[slot],
    'actual_uniforms':dict((index,renderer.model_component.GetExtraUniformValue(actual,index))
       for index in (1,2,3,4)) if actual != -1 else None,
    'cached_id_uniforms':dict((index,renderer.model_component.GetExtraUniformValue(cached,index))
       for index in (1,2,3,4)) if cached is not None else None,
    'doll':control_state(entry['dolls'][slot]),'surface':control_state(entry['surfaces'][slot])})
 rows.append(row)
_result=json.dumps({'groups':rows,'screen':b.factory.CreateGame(b.level).GetScreenSize(),
 'scene_origin':s.scene_origin,'scene_size':s.scene_size,'camera':s.camera_pose})
'''

HIDE = '''assert not hasattr(sys,'_water_editor_hidden')
sys._water_editor_hidden=[]
for entry in s.liquid_controls.registry.values():
 for ref in entry['surfaces']:
  control=ref.current
  sys._water_editor_hidden.append((control,control.GetVisible()))
  control.SetVisible(False,False)
_result=len(sys._water_editor_hidden)
'''
RESTORE_HIDDEN = '''if hasattr(sys,'_water_editor_hidden'):
 for control,shown in sys._water_editor_hidden:control.SetVisible(shown,False)
 del sys._water_editor_hidden
_result=True
'''

MOVE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory();player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0 and not hasattr(sys,'_water_editor_player')
platform=(2,5,2)
info=factory.CreateBlockInfo(player)
before=info.GetBlockNew(platform,dimension);back=info.GetLiquidBlock(platform,dimension)
assert before and before.get('name')=='minecraft:air',(platform,before)
assert back is None or back.get('name')=='minecraft:air',(platform,back)
sys._water_editor_player={'player':player,'dimension':dimension,'platform':platform,
 'foot':factory.CreatePos(player).GetFootPos()}
assert info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
assert factory.CreatePos(player).SetFootPos((2.5,6.,2.5))
_result=json.dumps(sys._water_editor_player)
'''
RESTORE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_water_editor_player',None)
if saved is not None:
 factory=api.GetEngineCompFactory()
 assert factory.CreatePos(saved['player']).SetFootPos(tuple(saved['foot']))
 info=factory.CreateBlockInfo(saved['player'])
 assert info.SetBlockNew(tuple(saved['platform']),{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
 assert info.GetBlockNew(tuple(saved['platform']),saved['dimension']).get('name')=='minecraft:air'
 del sys._water_editor_player
_result=json.dumps({'restored':True,'saved':saved})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--hud-control', action='store_true')
    parser.add_argument('--player-control', action='store_true')
    parser.add_argument('--world-primer', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh evidence output')
    project = args.project.resolve(strict=True)
    sys.path.insert(0, str(project / 'tools'))
    import probe_product_water as probe
    from _session import load_session
    from water_capture_contract import stable_scene_predicate
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    bound = load_session(args.session, args.owner, live=True)
    if Path(bound['project']).resolve() != project:
        parser.error('Project differs from bound session')
    before = probe.snapshot_sources(project)
    report = {'schema': 1, 'diagnostic_only': True, 'completed': False, 'restored': False,
              'cleanup_errors': [], 'phases': {}, 'captures': {}, 'session_id': bound['id'],
              'session_file': bound['session_file'], 'source_contract_sha256': probe.snapshot_digest(before),
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, args.output, 45.)
        installed = False
        try:
            check.run(probe.blueprints.INSTALL_PROBE)
            installed = True
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('close old editor', lambda value:not value['open'] and not value['transition'], check.navigation)
            report['profile'] = check.run(probe.PROFILE % (True, True))
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open editor', lambda value:value['open'] and not value['transition'], check.navigation)
            phases = ('wet', 'hidden', 'restored')
            if args.hud_control:
                phases += ('hud_hidden', 'hud_restored')
            if args.player_control:
                phases += ('player_high', 'player_restored')
            if args.world_primer:
                phases += ('world_primed', 'reopened')
            phases += ('dry', 'wet_again')
            for phase in phases:
                if phase in ('wet', 'dry', 'wet_again'):
                    control = 'wet' if phase == 'wet_again' else phase
                    check.run(probe.LOAD % (('pool', control, (35., 25., 4.6)),))
                    ready = check.wait('pool ' + phase,
                        stable_scene_predicate((35., 25., 4.6), (0., 0.), probe.workspace.scene_ready),
                        lambda:check.run(probe.SCENE_STATE))
                    report['phases'][phase] = {'ready': ready}
                elif phase.startswith('hud_'):
                    report['phases'][phase] = {'option': check.run(
                        probe.SAVE_HUD if phase == 'hud_hidden' else probe.RESTORE_HUD)}
                elif phase.startswith('player_'):
                    report['phases'][phase] = {'mutation': probe.base.run(client,
                        MOVE_PLAYER if phase == 'player_high' else RESTORE_PLAYER, True)}
                    expected = (2.5, 6., 2.5) if phase == 'player_high' else tuple(
                        report['phases']['player_high']['mutation']['foot'])
                    report['phases'][phase]['replicated'] = check.wait('player replication',
                        lambda value: value and max(abs(value[i]-expected[i]) for i in range(3))<.1,
                        lambda:check.run('_result=json.dumps(b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos())'))
                elif phase == 'world_primed':
                    report['phases'][phase] = {'saved': check.run(
                        "sys._water_editor_world=(s.origin,s.opacity,s.projection_missing,s.projection_outline)\n"
                        "s.origin=(63,-61,3);s.opacity=1.;s.projection_missing=False;s.projection_outline=False\n"
                        "b.project()\n_result=True")}
                    report['phases'][phase]['world'] = check.wait('world primer', probe.workspace.world_ready,
                        lambda:check.run(probe.WORLD_STATE))
                    report['phases'][phase]['stop'] = check.run(
                        "b.stop_projection()\ns.origin,s.opacity,s.projection_missing,s.projection_outline=sys._water_editor_world\n"
                        "del sys._water_editor_world\n_result=True")
                elif phase == 'reopened':
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close for remount', lambda value:not value['open'] and not value['transition'], check.navigation)
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('open for remount', lambda value:value['open'] and not value['transition'], check.navigation)
                    report['phases'][phase] = {'ready': check.wait('pool remounted',
                        stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                        lambda:check.run(probe.SCENE_STATE))}
                else:
                    check.run(HIDE if phase == 'hidden' else RESTORE_HIDDEN)
                    report['phases'][phase] = {}
                time.sleep(.6)
                report['phases'][phase]['native'] = check.run(STATE)
                report['captures'][phase] = probe.base.capture(args.session, args.owner,
                    args.output.with_name(args.output.stem + '_' + phase + '.png'), args.capture_exe)
                probe.base.write(args.output, report)
            report['completed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
            raise
        finally:
            if installed:
                if args.player_control:
                    try:
                        report['player_restore'] = probe.base.run(client, RESTORE_PLAYER, True)
                    except (RuntimeError, ValueError, TimeoutError) as error:
                        report['cleanup_errors'].append({'phase': 'player', 'error': str(error)})
                for label, code in (('hidden', RESTORE_HIDDEN),
                        ('world', "if hasattr(sys,'_water_editor_world'):\n b.stop_projection()\n s.origin,s.opacity,s.projection_missing,s.projection_outline=sys._water_editor_world\n del sys._water_editor_world\n_result=True"),
                        ('hud', probe.workspace.guarded_cleanup(probe.RESTORE_HUD, '_sign_visual_hud_saved')),
                        ('close', 'navigator.pop()\n_result=True' if check.navigation()['open'] else '_result=True')):
                    try:
                        report[label + '_restore'] = check.run(code)
                    except (RuntimeError, ValueError, TimeoutError) as error:
                        report['cleanup_errors'].append({'phase': label, 'error': str(error)})
                check.wait('editor closed', lambda value:not value['open'] and not value['transition'], check.navigation)
                try:
                    report['profile_restore'] = check.run(probe.RESTORE_PROFILE)
                except (RuntimeError, ValueError, TimeoutError) as error:
                    report['cleanup_errors'].append({'phase': 'profile', 'error': str(error)})
            report['restored'] = installed and not report['cleanup_errors']
            report['source_unchanged'] = before == probe.snapshot_sources(project)
            probe.base.write(args.output, report)
    print(json.dumps({key:report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()

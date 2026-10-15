"""Read an ordinary BB entity on the same owned water PaperDolls."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-prime-v6'
OWNER = 'water-r20-v6'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
TARGET = OUTPUT / 'same-doll-entity.json'
assert not TARGET.exists()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe

bound = json.loads((OUTPUT / 'start.json').read_bytes())
os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
before = probe.snapshot_sources(PROJECT)
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'completed': False, 'restored': False, 'cleanup_errors': [], 'phases': {}, 'captures': {},
    'source_contract_sha256': probe.snapshot_digest(before),
    'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
RESTORE_NATIVE = '''for renderer,slot,group,pose in sys._water_entity_control['rows']:
 assert renderer._render_pose(slot,group,pose)
 renderer.show(slot,True)
_result=True'''
with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client, TARGET, 45.)
    installed = saved = False
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        if check.navigation()['open']:
            check.run('navigator.pop()\n_result=True')
            check.wait('close prior workspace', lambda row:not row['open'] and not row['transition'], check.navigation)
        check.run(probe.PROFILE % (True, True))
        check.run('owner.open_workspace()\n_result=True')
        check.wait('open workspace', lambda row:row['open'] and not row['transition'], check.navigation)
        check.run(probe.LOAD % (('pool', 'wet', (35., 25., 4.6)),))
        report['ready'] = check.wait('ordinary pool',
            probe.stable_scene_predicate((35., 25., 4.6), (0., 0.), probe.workspace.scene_ready),
            lambda:check.run(probe.SCENE_STATE))
        check.run('''assert not hasattr(sys,'_water_entity_control')
sys._water_entity_control={'closed':s.liquid_controls.closed,'rows':[]}
for entry in s.liquid_controls.registry.values():
 renderer=entry['renderer'];slot=renderer.front
 sys._water_entity_control['rows'].append((renderer,slot,renderer.groups[slot],renderer.poses[slot]))
s.liquid_controls.closed=True
_result=True''')
        saved = True
        for label in ('baseline', 'cow', 'hidden', 'restored'):
            phase = report['phases'][label] = {}
            if label == 'cow':
                phase['submitted'] = check.run('''_result=[renderer.dolls[slot].RenderEntity({
 'entity_identifier':'minecraft:cow','scale':0.35,'render_depth':-50,
 'init_rot_y':45.0}) for renderer,slot,group,pose in sys._water_entity_control['rows']]''')
            elif label == 'hidden':
                phase['hidden'] = check.run('''for renderer,slot,group,pose in sys._water_entity_control['rows']:
 renderer.show(slot,False)
_result=True''')
            elif label == 'restored':
                check.run(RESTORE_NATIVE)
                phase['ids'] = check.wait('restored skeleton IDs',
                    lambda ids:len(ids)==8 and all(model_id != -1 for model_id in ids),
                    lambda:check.run('_result=[renderer.dolls[slot].GetModelId() for renderer,slot,group,pose in sys._water_entity_control["rows"]]'))
                check.run('''for renderer,slot,group,pose in sys._water_entity_control['rows']:
 for index,value in enumerate(group.uniforms,1):
  assert renderer.model_component.SetExtraUniformValue(renderer.dolls[slot].GetModelId(),index,value)
_result=True''')
            time.sleep(.8)
            report['captures'][label] = probe.base.capture(bound['session_file'], OWNER,
                OUTPUT / (TARGET.stem+'_'+label+'.png'), CAPTURE)
            probe.base.write(TARGET, report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        actions = []
        if saved:
            actions.append(('native', RESTORE_NATIVE))
            actions.append(('updater', '''s.liquid_controls.closed=sys._water_entity_control['closed']
del sys._water_entity_control
_result=True'''))
        if installed:
            actions.extend((('close', 'if navigator.top is not None:navigator.pop()\n_result=True'),
                            ('workspace', probe.RESTORE_PROFILE)))
        for label, code in actions:
            try:
                report[label+'_restore'] = check.run(code)
            except Exception:
                report['cleanup_errors'].append({'phase':label, 'error':traceback.format_exc()})
        report['restored'] = not report['cleanup_errors']
        report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
        probe.base.write(TARGET, report)
print(json.dumps({key:report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)

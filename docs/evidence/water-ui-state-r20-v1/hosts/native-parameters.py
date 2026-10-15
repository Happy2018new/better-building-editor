"""Freeze root launch configuration and diagnose native UI call parameters."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
REFERENCE = ROOT / '.runtime/projects/portal-r20'
OUTPUT = ROOT / '.runtime/water-r20-state-v7'
OWNER = 'water-r20-v7'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe

def save(name, value):
    probe.base.write(OUTPUT / name, value)

def prepare():
    assert not OUTPUT.exists()
    baseline = json.loads((ROOT / '.runtime/water-r20-prime-v6/launch-inputs.json').read_bytes())
    assert probe.snapshot_sources(PROJECT) == baseline['source_sha256']
    OUTPUT.mkdir()
    shutil.copy2(PROJECT / '.mcdev.json', OUTPUT / 'previous-mcdev.json')
    shutil.copy2(REFERENCE / '.mcdev.json', PROJECT / '.mcdev.json')
    shutil.copy2(PROJECT / '.mcdev.json', OUTPUT / 'launch-mcdev.json')
    shutil.copy2(ROOT / '.runtime/water-r20-prime-v6/launch-inputs.json', OUTPUT / 'launch-inputs.json')
    save('plan.json', {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'window_actions': [], 'source_contract_sha256': baseline['source_contract_sha256'],
        'config_equals_root_reference': True,
        'launch_config_sha256': hashlib.sha256((PROJECT / '.mcdev.json').read_bytes()).hexdigest(),
        'phases': ['cold_water', 'native_call_parameters'], 'root_product_inputs_untouched': True})
    print(json.dumps({'prepared': True, 'source_contract_sha256': baseline['source_contract_sha256']}))

def run():
    target = OUTPUT / 'call-parameters.json'
    assert not target.exists()
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
    before = probe.snapshot_sources(PROJECT)
    report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'completed': False, 'restored': False, 'cleanup_errors': [], 'phases': {}, 'captures': {},
        'source_contract_sha256': probe.snapshot_digest(before),
        'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, target, 45.)
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
            check.run('''assert not hasattr(sys,'_water_call_control')
sys._water_call_control={'closed':s.liquid_controls.closed,'rows':[]}
for entry in s.liquid_controls.registry.values():
 renderer=entry['renderer'];slot=renderer.front
 sys._water_call_control['rows'].append((renderer,slot,renderer.groups[slot],renderer.poses[slot]))
s.liquid_controls.closed=True
_result=True''')
            saved = True
            labels = ('baseline','animation_empty','animation_idle','light','depth15',
                      'entity_without_identity','skeleton_after_entity','entity_exact','restored')
            for label in labels:
                phase = report['phases'][label] = {}
                if label != 'baseline':
                    phase['submit'] = check.run('''label=%r
rows=[]
for renderer,slot,group,pose in sys._water_call_control['rows']:
 scale,rx,ry,rz=pose
 params={'scale':scale,'render_depth':-50,'init_rot_x':rx,'init_rot_y':ry,'init_rot_z':rz}
 if label in ('entity_without_identity','entity_exact'):
  if label=='entity_exact':params['entity_identifier']='minecraft:cow'
  ok=renderer.dolls[slot].RenderEntity(params)
 else:
  params['skeleton_model_name']=group.model_name
  if label=='animation_empty':params.update(animation='',animation_looped=False)
  elif label=='animation_idle':params.update(animation='idle',animation_looped=True)
  elif label=='light':params['light_direction']=(1.0,0.0,1.0)
  elif label=='depth15':params['render_depth']=-15
  ok=renderer.dolls[slot].RenderSkeletonModel(params)
 rows.append({'returned':ok,'params':params})
_result=json.dumps(rows)''' % label)
                    phase['ids'] = check.wait('native IDs',
                        lambda ids:len(ids)==8 and all(model_id != -1 for model_id in ids),
                        lambda:check.run('_result=[renderer.dolls[slot].GetModelId() for renderer,slot,group,pose in sys._water_call_control["rows"]]'))
                    phase['payload'] = check.run('''for renderer,slot,group,pose in sys._water_call_control['rows']:
 for index,value in enumerate(group.uniforms,1):
  assert renderer.model_component.SetExtraUniformValue(renderer.dolls[slot].GetModelId(),index,value)
_result=True''')
                time.sleep(.6)
                report['captures'][label] = probe.base.capture(bound['session_file'], OWNER,
                    OUTPUT / (target.stem+'_'+label+'.png'), CAPTURE)
                probe.base.write(target, report)
            report['completed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        finally:
            actions = []
            if saved:
                actions.append(('native', '''for renderer,slot,group,pose in sys._water_call_control['rows']:
 assert renderer._render_pose(slot,group,pose)
s.liquid_controls.closed=sys._water_call_control['closed']
del sys._water_call_control
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
            probe.base.write(target, report)
    print(json.dumps({key:report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
    return 0 if report['completed'] and report['restored'] else 1

raise SystemExit(prepare() if sys.argv[1]=='prepare' else run())

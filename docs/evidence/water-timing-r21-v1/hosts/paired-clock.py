"""Natural editor owner calls with paired wall/QPC clocks, no screenshots."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-state-v7'
TARGET = OUTPUT / 'ui-clock-v1.json'
OWNER = 'water-r20-v7'
assert not TARGET.exists()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe
from _session import load_session

parent = ROOT / '.runtime/water-r20-granular.py'
constants = {}
for node in ast.parse(parent.read_text(encoding='utf-8')).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('INSTALL', 'RESTORE'):
        constants[node.targets[0].id] = ast.literal_eval(node.value)
install = constants['INSTALL'].replace('import gc\n',
    'import gc,thread\nfrom modern_projection.projection.liquid_viewport import LiquidControls\nfrom modern_projection.projection.liquid_render import SkeletonLiquidRenderer\n')
install = install.replace("for cls,names in ((LiquidPreview,('advance','_start','signature')),",
    "for cls,names in ((LiquidControls,('update',)),(SkeletonLiquidRenderer,('restore_publication','update','_update_pose','_settle','_render_pose','_payload')),\n (LiquidPreview,('advance','_start','signature')),")
install = install.replace("if key=='Session.emit':row['field']=args[0] if args else None",
    "if key=='Session.emit':row['field']=args[0] if args else None\n  if key=='LiquidControls.update':row.update(requested_groups=len(args[0]),registry_entries=len(self.registry),thread_id=thread.get_ident())")
binding_path = json.loads((OUTPUT / 'start.json').read_bytes())['session_file']
os.environ.update(MCDEV_SESSION_FILE=binding_path, MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
binding = load_session(binding_path, OWNER, live=True)
assert Path(binding['project']).resolve() == PROJECT.resolve()
before = probe.snapshot_sources(PROJECT)
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'screenshots': [], 'window_actions': [], 'completed': False, 'restored': False,
    'cleanup_errors': [], 'rows': [], 'source_contract_sha256': probe.snapshot_digest(before),
    'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'parent_host_sha256': hashlib.sha256(parent.read_bytes()).hexdigest(),
    'session_binding': {key: binding[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')}}
with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client, TARGET, 45.)
    installed = timing = False
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        check.run(probe.PROFILE % (True, True))
        check.run('owner.open_workspace()\n_result=True')
        check.wait('open editor', lambda row: row['open'] and not row['transition'], check.navigation)
        report['install'] = check.run(install)
        timing = True
        for case in ('pool','flow_west','wet_oak_fence','wet_glass_pane','wet_oak_slab','wet_oak_stairs') * 3:
            for control in ('wet', 'dry'):
                metrics = probe.workspace.transport.metrics(binding_path, OWNER)
                assert metrics['handles'] < 220000, metrics
                check.run(probe.LOAD % ((case, control, (35.,25.,4.6)),))
                state = check.wait('clock ' + case + ' ' + control,
                    probe.stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                    lambda: check.run(probe.SCENE_STATE))
                report['rows'].append({'case': case, 'control': control, 'metrics': metrics,
                    'groups': len(state.get('liquid_groups', ()))})
                probe.base.write(TARGET, report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if timing:
            try:
                report['timing'] = check.run("_result=json.dumps(dict((k,v) for k,v in sys._water_granular.items() if k not in ('saved','stack')))")
                check.run(constants['RESTORE'])
            except Exception:
                report['cleanup_errors'].append({'phase': 'timing', 'error': traceback.format_exc()})
        if installed:
            for label, code in (('close', 'if navigator.top is not None:navigator.pop()\n_result=True'),
                                ('workspace', probe.RESTORE_PROFILE)):
                try:
                    report[label + '_restore'] = check.run(code)
                except Exception:
                    report['cleanup_errors'].append({'phase': label, 'error': traceback.format_exc()})
        report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
        report['restored'] = not report['cleanup_errors'] and report['source_unchanged']
        probe.base.write(TARGET, report)
print(json.dumps({key: report.get(key) for key in ('completed','restored','source_unchanged','error')}))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)

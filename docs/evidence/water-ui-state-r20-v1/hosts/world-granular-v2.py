"""World owner nested elapsed-time diagnostics without screenshots or input."""
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
OWNER = 'water-r20-v7'
TARGET = OUTPUT / os.environ.get('MCDEV_WATER_WORLD_REPORT', 'granular-world-v1.json')
assert not TARGET.exists()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe
from _session import load_session

host = ROOT / '.runtime/water-r20-granular.py'
constants = {}
for node in ast.parse(host.read_text(encoding='utf-8')).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ('INSTALL', 'RESTORE'):
            constants[node.targets[0].id] = ast.literal_eval(node.value)
install = constants['INSTALL'].replace(
    'except (ImportError,AttributeError,AssertionError):\n water_thread_seconds=None',
    "except (ImportError,AttributeError,AssertionError) as error:\n water_thread_failure=repr(error)\n water_thread_seconds=None")
install = install.replace("'thread_cpu_supported':water_thread_seconds is not None,",
    "'thread_cpu_supported':water_thread_seconds is not None,'thread_cpu_failure':globals().get('water_thread_failure'),")
if os.environ.get('MCDEV_WATER_WORLD_DETAIL') == '1':
    install = install.replace("(WorldLiquidRenderer,('advance','begin'))",
        "(WorldLiquidRenderer,('advance','begin','_create','retry_retired','_destroy','restore_positions','_promote','prepare_publication','finalize_publication','set_opacity'))")
bound = json.loads((OUTPUT / 'start.json').read_bytes())
os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
binding = load_session(bound['session_file'], OWNER, live=True)
assert Path(binding['project']).resolve() == PROJECT.resolve()
before = probe.snapshot_sources(PROJECT)
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'visual_acceptance_claimed': False, 'screenshots': [], 'window_actions': [],
    'completed': False, 'restored': False, 'cleanup_errors': [], 'rows': [],
    'source_contract_sha256': probe.snapshot_digest(before),
    'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'granular_parent_host_sha256': hashlib.sha256(host.read_bytes()).hexdigest(),
    'session_binding': {key: binding[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')}}
with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client, TARGET, 45.)
    installed = timing = saved = reserved = False
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        if check.navigation()['open']:
            check.run('navigator.pop()\n_result=True')
            check.wait('close workspace', lambda row: not row['open'] and not row['transition'], check.navigation)
        check.run(probe.PROFILE % (True, True))
        check.run("sys._water_world_saved={key:getattr(s,key) for key in ('origin','opacity','projection_missing','projection_outline')}\n_result=True")
        saved = True
        report['reservation'] = probe.base.run(client, probe.RESERVE, True)
        reserved = True
        origin = tuple(report['reservation']['origin'])
        document_origin = tuple(axis - 3 for axis in origin)
        check.run('s.origin=%r\ns.opacity=1.\ns.projection_outline=False\n_result=True' % (document_origin,))
        report['install'] = check.run(install)
        timing = True
        for route in ('full', 'missing'):
            for case in ('pool', 'flow_west', 'pool', 'flow_east', 'falling', 'diagonal'):
                for control in ('wet', 'dry'):
                    metrics = probe.workspace.transport.metrics(bound['session_file'], OWNER)
                    if metrics['handles'] >= 220000:
                        report['budget_stop'] = metrics
                        break
                    check.run(probe.LOAD % ((case, control, (35., 25., 4.6)),))
                    check.run('s.projection_missing=%r\nb.project()\n_result=True' % (route == 'missing',))
                    state = check.wait('world granular ' + route + ' ' + case + ' ' + control,
                        probe.workspace.world_ready, lambda: check.run(probe.WORLD_STATE))
                    report['rows'].append({'route': route, 'case': case, 'control': control,
                        'metrics': metrics, 'groups': len(state.get('liquid_groups', ())), 'ready': state})
                    check.run('b.stop_projection()\n_result=True')
                    probe.base.write(TARGET, report)
                if 'budget_stop' in report:
                    break
            if 'budget_stop' in report:
                break
        report['completed'] = 'budget_stop' not in report
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        actions = [('projection', 'b.stop_projection()\n_result=True', False)]
        if timing:
            try:
                report['timing'] = check.run("_result=json.dumps(dict((k,v) for k,v in sys._water_granular.items() if k not in ('saved','stack')))")
            except Exception:
                report['cleanup_errors'].append({'phase': 'timing_read', 'error': traceback.format_exc()})
            actions.append(('timing', constants['RESTORE'], False))
        if reserved:
            actions.append(('world', probe.workspace.QUALIFICATION_CLEAN_WORLD, True))
        if saved:
            actions.append(('origin', "for key,value in sys._water_world_saved.items():setattr(s,key,value)\ndel sys._water_world_saved\n_result=True", False))
        if installed:
            actions.append(('workspace', probe.RESTORE_PROFILE, False))
        for label, code, server in actions:
            try:
                report[label + '_restore'] = probe.base.run(client, code, True) if server else check.run(code)
            except Exception:
                report['cleanup_errors'].append({'phase': label, 'error': traceback.format_exc()})
        report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
        report['restored'] = not report['cleanup_errors'] and report['source_unchanged']
        probe.base.write(TARGET, report)
print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error', 'budget_stop')}))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)

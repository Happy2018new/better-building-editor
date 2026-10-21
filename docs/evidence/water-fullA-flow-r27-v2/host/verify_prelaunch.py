"""Execute actual launch prefix before Popen; no MC, watcher or RPC."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    spec = importlib.util.spec_from_file_location('merged_static_' + name[:-3], WORK / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_root.resolve()
    output.mkdir(exist_ok=False)
    sys.path.insert(0, str(WORK))
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    hosts = json.loads((WORK / 'prelaunch-host-binding-v1.json').read_bytes())
    watch = {'owners': [binding['owner']], 'errors': [], 'other_assertions': [],
             'checked_at': datetime.now(timezone.utc).isoformat(),
             'host_sha256': binding['diagnostic_watcher']['sha256']}
    launcher = load('launch_r25.py')
    tree = ast.parse((WORK / 'launch_r25.py').read_bytes())
    main_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    statements = []
    mocked = []
    boundary = None
    for node in main_function.body:
        if isinstance(node, ast.With) and 'stdout.json' in ast.unparse(node.items[0].context_expr):
            boundary = node.lineno
            break
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'watch' for target in node.targets):
            node = ast.parse('watch=STATIC_WATCHER_FIXTURE').body[0]
            mocked.append('fresh watcher status dictionary')
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'out' for target in node.targets):
            node = ast.parse('out=STATIC_OUTPUT_ROOT/"launch-prefix"').body[0]
            mocked.append('launch output directory')
        statements.append(node)
    assert boundary and len(mocked) == 2
    code = ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[]))
    namespace = dict(launcher.__dict__, STATIC_WATCHER_FIXTURE=watch, STATIC_OUTPUT_ROOT=output)
    original_argv = sys.argv[:]
    sys.argv = [str(WORK / 'launch_r25.py')]
    try:
        exec(compile(code, str(WORK / 'launch_r25.py') + ':actual-prefix', 'exec'), namespace)
    finally:
        sys.argv = original_argv
    assert all(sha(WORK / name) == expected for name, expected in hosts['host_sha256'].items())
    assert all(sha(ROOT / name) == expected for name, expected in hosts['external_host_sha256'].items())
    assert sha(WORK / 'final-source-binding-v1.json') == hosts['source_binding_sha256']
    assert all(sha(Path(binding['project']) / name) == value for name, value in dict(binding['source_sha256'], **binding['auxiliary_sha256']).items())
    assert all(sha(Path(binding['project']) / name) == value for name, value in binding['owner_and_qualification_preserved_sha256'].items())
    # The actual read-only cold-init payload is compiled in the real Python2 runtime.
    cold = load('observe_cold_default.py')
    result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
        'import sys;compile(sys.stdin.read(),"cold-observation","exec")'], input=cold.CODE.encode('utf8'), capture_output=True)
    assert result.returncode == 0, result.stderr
    payload = ast.parse(cold.CODE)
    forbidden = {'UiInitFinished', 'candidate_profile', 'production_profile', 'setattr', 'delattr'}
    assert not any(isinstance(node, ast.Call) and
                   ((isinstance(node.func, ast.Attribute) and node.func.attr in forbidden) or
                    (isinstance(node.func, ast.Name) and node.func.id in forbidden)) for node in ast.walk(payload))
    assert not any(isinstance(node, (ast.Assign, ast.AugAssign)) and
                   any(isinstance(target, ast.Attribute) for target in getattr(node, 'targets', [getattr(node, 'target', None)]))
                   for node in ast.walk(payload))
    imported = []
    for name in ('run_group.py', 'observe_cold_default.py', 'scene_game.py', 'scene_restore.py',
                 'flow_restore.py', 'world_readback.py', 'scene_policy.py', 'retire_helpers.py', 'start_assert_watch.py', 'watch_handles.py'):
        load(name)
        imported.append(name)
    flow = (WORK / 'run_flow.py').read_text('utf8')
    assert "'--production-default'" in flow
    assert "geometry_sample(label + '_before_burst')" in flow
    assert "capture_native_burst_startup" in flow and "'3200'" in flow
    assert "if STAGE != 'A':" in flow
    assert "ROUTES = ('editor', 'full', 'missing')" in flow
    assert "'flow_south', 'flow_west', 'flow_north', 'falling'" in flow
    assert "'--falling-skyward'" in flow and "'--camera-calibration'" in flow
    assert "if route != 'editor':" in flow
    geometry_function=next(node for node in ast.walk(ast.parse(flow)) if isinstance(node,ast.FunctionDef) and node.name=='geometry_sample')
    calls=[]
    namespace={'ROUTES':('editor','full','missing'),'OUT':Path('product-v2-a-v1.json'),'active_check':[object()],
      'original_run':lambda *args:calls.append(args) or {},'probe':type('Probe',(),{'SCENE_STATE':''})(),
      'scene_game':type('Game',(),{'EXTRA_STATE':''})(),'describe_scene':lambda *args:{'complete':True},
      'geometry':[],'save':lambda:None}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[geometry_function],type_ignores=[])),'actual_geometry_guard','exec'),namespace)
    for route in ('full','missing'):namespace['geometry_sample']('product-v2-a-v1_'+route+'_flow_east_wet')
    assert not calls, 'World must never query editor Scene geometry'
    namespace['geometry_sample']('product-v2-a-v1_editor_flow_east_wet')
    assert len(calls)==1 and len(namespace['geometry'])==1
    calibration=load('calibration_host.py')
    assert sha(calibration.CANDIDATE)==calibration.EXPECTED
    compiled=subprocess.run(['D:/Program/Python27/python.exe','-B','-c','import sys;compile(sys.stdin.read(),"single-stone-observation","exec")'],input=calibration.SINGLE_STONE_CODE.encode('utf8'),capture_output=True)
    assert compiled.returncode==0,compiled.stderr
    camera=(WORK/'run_camera.py').read_text('utf8')
    assert 'single_stone_sample(label' in camera and "tool.write_json=versioned_write" in camera
    assert 'versioned_calibration_host' in camera and 'validate_report' in flow
    assert '07:25 capture cutoff' in camera and '07:25 capture cutoff' in flow
    world=load('world_readback.py')
    for code in (world.SERVER_CODE,world.CLIENT_CODE):
        compiled=subprocess.run(['D:/Program/Python27/python.exe','-B','-c','import sys;compile(sys.stdin.read(),"world-readback","exec")'],input=code.encode('utf8'),capture_output=True)
        assert compiled.returncode==0,compiled.stderr
    group = (WORK / 'run_group.py').read_text('utf8')
    assert 'run_candidate_bootstrap' not in group and 'retire_bootstrap' not in group
    prefix = json.loads((output / 'launch-prefix/launch.json').read_bytes())
    report = {'schema': 1, 'passed': True, 'MC_started': False, 'Popen_dispatched': False,
              'RPC_dispatched': False, 'watcher_started': False,
              'actual_launcher_prefix_nodes_executed': len(statements), 'stop_before_line': boundary,
              'explicit_mock_inputs': mocked,
              'observed_active_MC_count': prefix['single_instance_preflight']['active_minecraft_count'],
              'source_files_checked': len(binding['source_sha256']), 'auxiliary_files_checked': len(binding['auxiliary_sha256']),
              'source_contract_sha256': binding['source_contract_sha256'],
              'owner_and_qualification_original_bytes_preserved': True,
              'cold_payload_python2_compile': True, 'cold_payload_no_init_or_profile_mutation': True,
              'runtime_lifecycle_imports': imported, 'full_A_15_cell_candidate': True, 'world_geometry_never_queries_editor': True, 'same_session_camera_required': True,
              'normal_default_initialized_session_required': True,
              'formal_A_accepted': False, 'default_path_evidence': False,
              'production_admission_performed': False, 'manual_closures_added': 0,
              'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
              'plan_sha256': sha(WORK / 'plan-v1.json'),
              'limitations': ['No real watcher freshness, runtime SDK state or native pixels are claimed.',
                             'Normal initialization reads historical generated constants; it is not new-source acceptance.',
                             'Explicit source/host inventory is not complete transitive closure.']}
    target = output / 'static-prelaunch-v1.json'
    with target.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({'passed': True, 'actual_launcher_prefix_nodes': len(statements), 'MC_started': False,
                      'report_sha256': sha(target), 'plan_sha256': report['plan_sha256'], 'host_binding_sha256': report['host_binding_sha256']}))


if __name__ == '__main__':
    main()

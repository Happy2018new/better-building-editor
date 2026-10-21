"""Execute the actual launcher prefix up to Popen with explicit status fixture.

No process spawn, MC, watcher, RPC, source mutation or real session is created.
Only the fresh watcher JSON input and launch-output directory are substituted.
"""
import argparse
import ast
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys,time

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    path=WORK/name
    spec=importlib.util.spec_from_file_location('water_static_'+name[:-3],path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args();out=args.output_root.resolve();out.mkdir(exist_ok=False)
    sys.path.insert(0,str(WORK))
    binding=json.loads((WORK/'final-source-binding-v1.json').read_bytes())
    hosts=json.loads((WORK/'prelaunch-host-binding-v1.json').read_bytes())
    watcher=binding['diagnostic_watcher']
    status={'owners':[binding['owner']],'errors':[],'other_assertions':[],
        'checked_at':datetime.now(timezone.utc).isoformat(),'host_sha256':watcher['sha256']}
    launch=load('launch_r25.py')
    tree=ast.parse((WORK/'launch_r25.py').read_bytes())
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    statements=[];mocked=[];boundary=None
    for node in function.body:
        if isinstance(node,ast.With) and 'stdout.json' in ast.unparse(node.items[0].context_expr):
            boundary={'first_line':node.lineno,'source':ast.unparse(node.items[0].context_expr)}
            break
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='watch' for t in node.targets):
            node=ast.parse('watch=STATIC_WATCHER_FIXTURE').body[0];mocked.append('fresh watcher status dictionary')
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in node.targets):
            node=ast.parse('out=STATIC_OUTPUT_ROOT/"launch-prefix"').body[0];mocked.append('launch report output directory')
        statements.append(node)
    assert boundary and len(mocked)==2
    module=ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[]))
    environment=dict(launch.__dict__,STATIC_WATCHER_FIXTURE=status,STATIC_OUTPUT_ROOT=out)
    original_argv=sys.argv[:];sys.argv=[str(WORK/'launch_r25.py')]
    try:exec(compile(module,str(WORK/'launch_r25.py')+':actual_prefix','exec'),environment)
    finally:sys.argv=original_argv
    prefix_report=json.loads((out/'launch-prefix/launch.json').read_bytes())
    assert prefix_report['single_instance_preflight']['active_minecraft_count']==0
    assert prefix_report['memory_preflight']['available_commit_bytes']>=6*1024**3
    # Bootstrap's actual pure checks and dispatch generation are run separately
    # because the live session check needs a game and is deliberately excluded.
    bootstrap=load('run_candidate_bootstrap.py')
    sources=bootstrap.checked_sources(binding)
    assert len(sources)==4484
    assert sha(WORK/'candidate_bootstrap.py')==binding['bootstrap_sha256']
    assert sha(Path(binding['archive']['path']))==binding['archive']['sha256']
    assert sha(Path(binding['project'])/binding['qualification_path'])==binding['qualification_sha256']
    code=bootstrap.dispatch_code((WORK/'candidate_bootstrap.py').read_text('utf8'),binding)
    assert code.encode('utf8')==(WORK/'dispatched-bootstrap-payload.py').read_bytes()
    # Import actual lifecycle modules and all pure dependencies; never call main.
    dependencies=[]
    for name in ('run_anchor_group.py','run_anchor_calibration.py','watch_handles.py',
                 'retire_bootstrap_marker.py','retire_helpers.py','start_assert_watch.py'):
        loaded=load(name);dependencies.append({'file':name,'sha256':sha(WORK/name),'imported':True})
    assert all(sha(WORK/name)==expected for name,expected in hosts['host_sha256'].items())
    assert all(sha(ROOT/name)==expected for name,expected in hosts['external_host_sha256'].items())
    assert sha(WORK/'final-source-binding-v1.json')==hosts['source_binding_sha256']
    original=WORK.with_name('water-anchor-calibration-v4')/'candidate_bootstrap.py'
    assert (WORK/'candidate_bootstrap.py').read_bytes()==original.read_bytes()
    report={'schema':1,'checked_at':time.time(),'passed':True,'MC_started':False,
        'Popen_dispatched':False,'RPC_dispatched':False,'watcher_started':False,
        'actual_launcher_prefix_nodes_executed':len(statements),'stop_before_boundary':boundary,
        'explicit_mock_inputs':mocked,'core_exact_original_sha256':binding['bootstrap_sha256'],
        'source_files_checked':len(sources),'actual_bootstrap_pure_preconditions_passed':True,
        'actual_dispatch_bytes_match':True,'lifecycle_imports':dependencies,
        'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json'),
        'test_host_sha256':sha(Path(__file__)),'actual_launch_host_sha256':sha(WORK/'launch_r25.py'),
        'runtime_readiness_dependency_assets':{name:v for name,v in hosts['external_host_sha256'].items()
            if '/pyreact-debugging/scripts/' in name or name.endswith('windows_manifest_reader.py') or 'watch_owned_disabled_skin_assert_r27_v5.py' in name},
        'limitations':['No live SDK/client/server readiness state is claimed.',
            'Original instances.py readiness implementation and its dependencies are SHA-bound; importing it does not execute MC readiness.',
            'The static watcher fixture proves expected field/hash consistency, not real watcher freshness.'],
        'formal_A_accepted':False,'manual_closures_added':0}
    output=out/'static-launch-review-v1.json'
    with output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':True,'actual_launcher_prefix_nodes':len(statements),
        'core_exact_original':True,'report_sha256':sha(output),'MC_started':False}))


if __name__=='__main__':main()

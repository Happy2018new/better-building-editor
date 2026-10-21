"""Freeze the v3 host and record exact resource-gate coverage; no game start."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
OLD=WORK.with_name('water-anchor-calibration-v2')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def region(path,names):
    text=path.read_text('utf-8');tree=ast.parse(text)
    functions=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name in names:
            functions.append({'name':node.name,'first_line':node.lineno,'last_line':node.end_lineno,
                              'source':'\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])})
    return {'path':str(path),'sha256':sha(path),'functions':functions}


def main():
    assert not (WORK/'v3-final-review.json').exists()
    binding=json.loads((WORK/'final-source-binding-v1.json').read_bytes())
    project=Path(binding['project'])
    assert all(sha(project/name)==expected for name,expected in
               dict(binding['source_sha256'],**binding['auxiliary_sha256']).items())
    assert sha(Path(binding['archive']['path']))==binding['archive']['sha256']
    plan=json.loads((OLD/'plan-v1.json').read_bytes())
    plan.update(schema=3,declared_at_utc=datetime.now(timezone.utc).isoformat(),
                previous_plan_sha256=sha(OLD/'plan-v1.json'),
                failed_cleanup_policy='Original exception retained; final readonly RPC/source audit faults captured as cleanup_errors/restore_unknown; final report saved. Group retains ordinary stop and same-handle exit.',
                per_capture_handle_gates='Same retained PID+creation handle reads before configure, immediately before and after each capture; success and failure paths. Continuous exact-owner watcher samples independently at 1 second intervals.',
                resource_gate_scope='game and MCDK process identities. Short-lived WGC child is owner-bound and reaped by capture wrapper, not covered by game/MCDK adjacent-handle count claims.')
    plan['host_code_sha256']={name:sha(WORK/name) for name in ('anchor_game.py','run_anchor_calibration.py')}
    (WORK/'plan-v1.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    stage=json.loads((WORK/'stage-r25.json').read_bytes());stage['plan_sha256']=sha(WORK/'plan-v1.json')
    (WORK/'stage-r25.json').write_text(json.dumps(stage,indent=2)+'\n',encoding='utf-8')
    coverage={'schema':1,'MC_started':False,'actual_runtime_coverage_established':False,
        'gate_limits':plan['resource_gates'],
        'game_MCDK_coverage':['Per capture host checks both exact creation identities and counts from same retained process handles; records counts before enforcing strict limits.',
            'Before configure, immediately before WGC capture, after success or attempted after failed capture. Post-capture failure cannot overwrite the original capture exception.',
            'Watch_handles starts at starting state as soon as exact game/MCDK IDs are known; independent 1s sampling until identity ends or stop/deadline/guard breach.',
            'Watcher enforces count>=250000 or adjacent positive increase>=10000 by ordinary owner-bound stop; no OS suspension.'],
        'limits':['Checks are sampled; they do not prove every intermediate handle count between observations.',
                  'Per-capture and continuous-watcher adjacent samples are separate streams; they are not merged as one observed high-frequency timeline.',
                  'Static WGC wrapper does not itself enforce game/MCDK handle-growth thresholds.',
                  'The short-lived WGC helper is a retained subprocess; no claim that it shares the game/MCDK handle-growth guard.',
                  'None of this prepared coverage is runtime evidence before an actual launch.'],
        'sources':{
            'per_capture':region(WORK/'run_anchor_calibration.py',('resource_sample','preflight','capture')),
            'continuous':region(WORK/'watch_handles.py',('sample_process','main')),
            'limits':region(WORK/'guard_policy.py',('handle_breach',)),
            'launch':region(WORK/'launch_r25.py',('main',)),
            'capture_wrapper':region(project/'tools/capture_native_window.py',('capture',)),
            'group_stop':region(WORK/'run_anchor_group.py',('main',))}}
    with (WORK/'resource-coverage-v1.json').open('x',encoding='utf-8') as stream:json.dump(coverage,stream,indent=2)
    old=json.loads((OLD/'prelaunch-host-binding-v1.json').read_bytes())
    assert all(sha(ROOT/name)==expected for name,expected in old['external_host_sha256'].items())
    hosts=dict(old,schema=3,frozen_at_utc=datetime.now(timezone.utc).isoformat(),
               previous_host_binding_sha256=sha(OLD/'prelaunch-host-binding-v1.json'),
               host_sha256={path.name:sha(path) for path in WORK.glob('*.py')}|
                   {name:sha(WORK/name) for name in ('product-v2-launch-inputs.json','stage-r25.json','plan-v1.json')})
    (WORK/'prelaunch-host-binding-v1.json').write_text(json.dumps(hosts,indent=2)+'\n',encoding='utf-8')
    for path in WORK.glob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    review={'schema':3,'MC_started':False,'source_unchanged':True,'source_files':len(binding['source_sha256']),
        'auxiliary_files':len(binding['auxiliary_sha256']),'archive_sha256':binding['archive']['sha256'],
        'plan_sha256':sha(WORK/'plan-v1.json'),'host_binding_sha256':sha(WORK/'prelaunch-host-binding-v1.json'),
        'resource_coverage_sha256':sha(WORK/'resource-coverage-v1.json'),
        'failure_cleanup_review_sha256':sha(WORK/'failure-cleanup-review-v1.json'),
        'resource_gate_review_sha256':sha(WORK/'resource-gate-review-v1.json'),
        'failure_controls':{'actual_AST_host_cases':5,'actual_AST_group_stop_cases':1,'actual_AST_resource_boundary_cases':6,
            'MC_started':False,'RPC_dispatched':False,'subprocess_dispatched':False},
        'first_control_fixture_error_retained':True,'v1_v2_preserved':True,
        'python3_AST_scripts':len(list(WORK.glob('*.py'))),'production_admission_performed':False,
        'manual_closures_added':0}
    with (WORK/'v3-final-review.json').open('x',encoding='utf-8') as stream:json.dump(review,stream,indent=2)
    print(json.dumps(review))


if __name__=='__main__':main()

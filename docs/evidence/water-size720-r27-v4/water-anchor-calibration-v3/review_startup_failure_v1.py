"""Read-only causality and exact cleanup review of this single failed launch."""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import _kernel,process_identity


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=WORK/'startup-failure-review-v1.json'
    assert not target.exists()
    names=['group-execution-v1.json','launch/launch.json','launch/exact-exit.json',
        'continuous-handle-guard-v1.json','helper-retirement-v1.json','assert-watch/status.json',
        'root-window-preflight-v1.json','root-grant-v1.json','plan-v1.json',
        'prelaunch-host-binding-v1.json','final-source-binding-v1.json']
    inputs={name:json.loads((WORK/name).read_bytes()) for name in names}
    group=inputs['group-execution-v1.json'];launch=inputs['launch/launch.json']
    guard=inputs['continuous-handle-guard-v1.json'];binding=inputs['final-source-binding-v1.json']
    kernel=_kernel()
    observations={}
    for kind in ('game','mcdk'):
        pid=launch[kind+'_pid'];native=kernel.OpenProcess(0x1000,False,pid)
        row={'pid':pid,'expected_identity':launch[kind+'_identity'],'process_identity_now':process_identity(pid),
             'open_succeeded':bool(native),'open_winerror':None if native else ctypes.get_last_error()}
        if native:
            try:
                code=wintypes.DWORD();assert kernel.GetExitCodeProcess(native,ctypes.byref(code))
                row.update(exit_code=code.value,still_active=code.value==259)
            finally:kernel.CloseHandle(native)
        observations[kind]=row
    stats={}
    for source,samples in [('launch',launch['samples']),('continuous_guard',guard['samples'])]:
        stats[source]={}
        for kind in ('game','mcdk'):
            counts=[r[kind]['handles'] for r in samples if isinstance(r.get(kind),dict) and r[kind].get('handles') is not None]
            stats[source][kind]={'observed_count':len(counts),'maximum_handles':max(counts) if counts else None,
                'maximum_adjacent_positive_growth':max([0]+[b-a for a,b in zip(counts,counts[1:])])}
    changed=[]
    for name,expected in dict(binding['source_sha256'],**binding['auxiliary_sha256']).items():
        if sha(Path(binding['project'])/name)!=expected:changed.append(name)
    report={'schema':1,'reviewed_at':time.time(),'input_sha256':{n:sha(WORK/n) for n in names},
        'owner':binding['owner'],'attempt_count':1,'completed':False,'ready_reached':bool(launch.get('ready')),
        'bootstrap_started':any(s['label']=='bootstrap' for s in group['steps']),
        'diagnostic_UI_started':any(s['label']=='anchor' for s in group['steps']),
        'capture_report_exists':(WORK/'anchor-capture-v1.json').exists(),
        'observed_failure_chain':[
            'Assertion watcher recorded a PermissionError while reading the owned starting session.json.',
            'Fourth continuous resource sample observed assertion_watcher_not_healthy and initiated an ordinary owner-bound stop.',
            'Guard stop command returned 1: game had not closed within its wait. No force stop was used by this host.',
            'Same-handle observer later recorded game exit 0xC0000409 and MCDK exit 0.',
            'Starter then rejected the ended game creation identity; group final ordinary stop returned 0 and retired its watcher.'
        ],
        'failure_attribution_limits':[
            'The watcher did not record winerror for the read failure; a Windows sharing/replacement race is a static hypothesis, not measured OS proof.',
            'Do not describe the game exit as spontaneous or normal. An ordinary stop request preceded it.',
            'No new neutral, matrix, water pixel, animation or product rendering result exists for this attempt.',
            'Resource observations are sampled and do not establish unobserved instantaneous maxima.'
        ],
        'guard_breach':guard['guard_breach'],'modal_guard_breach':guard['modal_guard_breach'],
        'guard_stop':guard['ordinary_stop'],'final_ordinary_stop_exit_code':group['ordinary_stop']['exit_code'],
        'same_handle_exit':inputs['launch/exact-exit.json'],'exact_post_cleanup':observations,
        'helper_retirement':inputs['helper-retirement-v1.json'],'resource_stats':stats,
        'source_and_auxiliary_count':len(binding['source_sha256'])+len(binding['auxiliary_sha256']),
        'source_changed_paths':changed,'source_unchanged':not changed,
        'independent_UI_restore_applicable':False,'bootstrap_marker_retirement_applicable':False,
        'no_same_condition_retry_performed':True,'formal_A_accepted':False,
        'production_admission_performed':False,'manual_closures_added':0}
    assert not report['ready_reached'] and not report['bootstrap_started'] and not report['diagnostic_UI_started']
    assert not report['capture_report_exists'] and not changed
    assert all(r['process_identity_now'] is None for r in observations.values())
    with target.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'report_sha256':sha(target),'source_unchanged':not changed,'resource_stats':stats,
        'game_exit':inputs['launch/exact-exit.json']['processes']['game']['exit_code_hex'],
        'final_stop':report['final_ordinary_stop_exit_code'],'watcher_retired':report['helper_retirement'].get('exact_helper_terminated')}))


if __name__=='__main__':main()

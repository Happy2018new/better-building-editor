"""Preserve the first configured-cell failure and actual cleanup facts."""
import hashlib,json,time
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target=WORK/'payload-failure-review-v1.json';assert not target.exists()
    names=('group-execution-v1.json','launch/launch.json','launch/exact-exit.json','anchor-capture-v1.json',
        'independent-restore-v1.json','bootstrap-marker-retired-v1.json','helper-retirement-v1.json',
        'continuous-handle-guard-v1.json','assert-watch/status.json','final-source-binding-v1.json')
    inputs={name:json.loads((WORK/name).read_bytes()) for name in names}
    g=inputs['group-execution-v1.json'];capture=inputs['anchor-capture-v1.json'];binding=inputs['final-source-binding-v1.json']
    launch=inputs['launch/launch.json'];guard=inputs['continuous-handle-guard-v1.json']
    stats={}
    for kind in ('game','mcdk'):
        counts=[r[kind]['handles'] for r in guard['samples'] if r[kind].get('handles') is not None]
        stats[kind]={'maximum_handles':max(counts),'maximum_adjacent_positive_growth':max([0]+[b-a for a,b in zip(counts,counts[1:])])}
    source_unchanged=all(sha(Path(binding['project'])/n)==v for n,v in dict(binding['source_sha256'],**binding['auxiliary_sha256']).items())
    report={'schema':1,'reviewed_at':time.time(),'input_sha256':{n:sha(WORK/n) for n in names},
        'owner':binding['owner'],'ready_reached':launch['ready'],'bootstrap_completed':True,
        'window_GUI_readback':capture['window_rows'][0]['opened'],'configured_rows_attempted':len(capture['rows']),
        'successful_captures':sum('capture' in r for r in capture['rows']),
        'failure_kind':'Diagnostic CONFIGURE payload construction error, before the first capture.',
        'actual_error':capture['error'],'static_error_line':"pack_group(...,(0.,0.,0.),1.,1.)",
        'contract':'appearance_uniform requires exactly three integer RGB bytes, and rejects float channels.',
        'earlier_preparation_gap':'True Python2 compilation checked syntax but did not call pack_group with the diagnostic constants.',
        'source_unchanged':source_unchanged,'source_and_auxiliary_files':5875,
        'capture_restored':capture['restored'],'capture_restore_unknown':capture['restore_unknown'],
        'cleanup_errors':capture['cleanup_errors'],'independent_restore':inputs['independent-restore-v1.json']['restored'],
        'bootstrap_marker_retired':inputs['bootstrap-marker-retired-v1.json']['marker_retired'],
        'ordinary_stop_exit_code':g['ordinary_stop']['exit_code'],'same_handle_exit':g['same_handle_exit'],
        'exact_processes_absent':{kind:process_identity(launch[kind+'_pid']) is None for kind in ('game','mcdk')},
        'watcher_retired':inputs['helper-retirement-v1.json'].get('exact_helper_terminated'),
        'assertion_errors':inputs['assert-watch/status.json']['errors'],
        'native_manifest_read_recovery_events':inputs['assert-watch/status.json']['manifest_read_events'],
        'continuous_guard_samples':len(guard['samples']),'guard_breach':guard['guard_breach'],
        'modal_guard_breach':guard.get('modal_guard_breach'),'resource_stats':stats,
        'formal_A_accepted':False,'production_admission_performed':False,'manual_closures_added':0,
        'no_same_condition_retry_performed':True}
    assert report['successful_captures']==0 and source_unchanged
    assert all(report['exact_processes_absent'].values())
    assert report['capture_restored'] and report['independent_restore'] and report['bootstrap_marker_retired']
    with target.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'report_sha256':sha(target),'captures':0,'exact_processes_absent':report['exact_processes_absent'],
                     'source_unchanged':source_unchanged,'resource_stats':stats}))


if __name__=='__main__':main()

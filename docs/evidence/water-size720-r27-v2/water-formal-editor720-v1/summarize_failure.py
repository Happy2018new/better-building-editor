"""Summarize the failed original-limit non-trace cell, preserving every raw."""
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    burst = WORK/'formal-east-editor-size720-v1_editor_flow_east_wet_burst'
    paths = dict(manifest=burst/'manifest.json', wrapper=burst.with_name(burst.name+'.capture.json'),
        report=WORK/'formal-east-editor-size720-v1.json', group=WORK/'group-execution-v1.json',
        restore=WORK/'independent-restore-v1.json', guard=WORK/'continuous-handle-guard-v1.json',
        exits=WORK/'launch/exact-exit.json', bootstrap=WORK/'candidate-bootstrap-execution-v1.json',
        helper_retirement=WORK/'helper-retirement-v1.json')
    loaded = {name:json.loads(path.read_bytes()) for name,path in paths.items()}
    native, wrapper = loaded['manifest'], loaded['wrapper']
    frames = sorted([row for row in native['frames'] if row['capture_valid']],
                    key=lambda row:row['frame_qpc_100ns'])
    stamps = [row['frame_qpc_100ns'] for row in frames]
    start = (stamps[0]-native['request_qpc_100ns'])/10000. if stamps else None
    interior = max((b-a for a,b in zip(stamps,stamps[1:])),default=0)/10000.
    tail = (native['planned_end_qpc_100ns']-stamps[-1])/10000. if stamps else None
    resources = {}
    for kind in ('game','mcdk'):
        values = [row[kind]['handles'] for row in loaded['guard']['samples'] if row[kind]['handles'] is not None]
        resources[kind] = dict(maximum_handles=max(values),maximum_adjacent_growth=max(
            (b-a for a,b in zip(values,values[1:])),default=0))
    result = dict(schema=1, MC_started=True, sampling_protocol_check_only=True,
        formal_A_accepted=False, world_A_accepted=False, production_admission_performed=False,
        manual_closures_added=0, host_sha256=sha(Path(__file__)),
        inputs={name:dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size) for name,path in paths.items()},
        owner=loaded['group']['owner'],source_contract_sha256=loaded['group']['source_contract_sha256'],
        native_window_size=[wrapper['window']['width'],wrapper['window']['height']],
        capture_valid=wrapper['capture_valid'],temporal_complete=wrapper['temporal_complete'],
        helper_returncode=wrapper.get('helper_returncode'),capture_errors=wrapper.get('errors'),
        native_error=native.get('error'),valid_frames=len(frames),attempted_frames=len(native['frames']),
        start_gap_ms=start,maximum_interior_gap_ms=interior,tail_gap_ms=tail,
        gap_limit_ms=150,preparation_ms=1500,measurement_ms=3200,
        peak_accounted_buffer_bytes=native['peak_accounted_buffer_bytes'],
        total_buffer_limit_bytes=native['total_buffer_limit_bytes'],
        report_completed=loaded['report']['completed'],report_restored=loaded['report']['restored'],
        source_unchanged=loaded['report']['source_unchanged'],cleanup_errors=loaded['report']['cleanup_errors'],
        independent_standard_restore_passed=loaded['restore']['passed'],
        explicit_bootstrap_retirement_recorded=(WORK/'bootstrap-marker-retired-v1.json').exists(),
        continuous_guard_samples=len(loaded['guard']['samples']),resources=resources,
        guard_breach=loaded['guard']['guard_breach'],modal_guard_breach=loaded['guard'].get('modal_guard_breach'),
        exact_exit_codes={kind:row['exit_code_hex'] for kind,row in loaded['exits']['processes'].items()},
        exact_identities_absent=loaded['group']['exact_identities_absent_after_stop'],
        ordinary_stop_exit=loaded['group']['ordinary_stop']['exit_code'],
        exact_watcher_retired=loaded['helper_retirement'].get('exact_helper_terminated',False),
        limits_unchanged=True,prior_v3_trace_result_preserved=True,
        prior_v3_direction_failure_preserved=True,
        limitation='Non-trace helper has no FrameArrived/lifetime instrumentation; cannot infer callback root cause.')
    target = WORK/'failure-summary-r27-v1.json'
    with target.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps({key:result[key] for key in ('capture_valid','temporal_complete','start_gap_ms',
        'maximum_interior_gap_ms','tail_gap_ms','valid_frames','attempted_frames','report_restored',
        'source_unchanged','exact_exit_codes','explicit_bootstrap_retirement_recorded')}))
    print(json.dumps(dict(summary_sha256=sha(target))))


if __name__ == '__main__':
    main()

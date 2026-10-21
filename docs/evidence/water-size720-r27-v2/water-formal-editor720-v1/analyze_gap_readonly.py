"""Compare preserved trace/nontrace timing without fabricating absent lifecycle events."""
import difflib
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    groups = [WORK.with_name('water-size720-v3'), WORK]
    records = []
    for directory in groups:
        path = next(directory.glob('*_burst/manifest.json'))
        manifest = json.loads(path.read_bytes())
        valid = sorted((frame for frame in manifest['frames'] if frame['capture_valid']),
                       key=lambda frame:frame['frame_qpc_100ns'])
        gaps = sorted(((second['frame_qpc_100ns']-first['frame_qpc_100ns'],first,second)
            for first,second in zip(valid,valid[1:])),key=lambda value:value[0],reverse=True)
        all_stages = []
        for frame in manifest['frames']:
            before = frame['before']['observed_qpc_100ns']
            read = frame['after_readback']['observed_qpc_100ns']
            encoded = frame['after']['observed_qpc_100ns']
            all_stages.append(dict(sequence=frame['sequence'],capture_valid=frame['capture_valid'],
                frame_time_from_measurement_start_ms=(frame['frame_qpc_100ns']-manifest['request_qpc_100ns'])/10000.,
                source_frame_age_at_poll_ms=(before-frame['frame_qpc_100ns'])/10000.,
                poll_through_readback_ms=(read-before)/10000.,
                readback_to_after_ms=(encoded-read)/10000.,
                before_from_measurement_start_ms=(before-manifest['request_qpc_100ns'])/10000.,
                readback_from_measurement_start_ms=(read-manifest['request_qpc_100ns'])/10000.,
                assessment=frame.get('assessment'), future_wait=frame.get('future_timestamp_wait')))
        gap_rows=[]
        for gap,first,second in gaps[:5]:
            first_index,second_index=first['sequence']-1,second['sequence']-1
            gap_rows.append(dict(gap_ms=gap/10000.,first_sequence=first['sequence'],second_sequence=second['sequence'],
                worker_unobserved_between_frames_ms=(second['before']['observed_qpc_100ns']-
                    first['after']['observed_qpc_100ns'])/10000.,
                context=all_stages[max(0,first_index-1):min(len(all_stages),second_index+2)]))
        records.append(dict(directory=str(directory),manifest_sha256=sha(path),
            diagnostic_lifetime_events_present=bool(manifest.get('diagnostic_frame_lifetime_events')),
            diagnostic_arrivals_present='diagnostic_arrivals' in manifest,
            manifest_keys=sorted(manifest),attempted_frames=len(all_stages),valid_frames=len(valid),
            maximum_poll_through_readback_ms=max(row['poll_through_readback_ms'] for row in all_stages),
            maximum_readback_to_after_ms=max(row['readback_to_after_ms'] for row in all_stages),
            worst_gaps=gap_rows,per_frame_observable_stages=all_stages,
            Close_or_COM_release_coverage='explicit trace events' if manifest.get('diagnostic_frame_lifetime_events')
                else 'not instrumented: no runtime proof of every Close or COM release'))
    contract_paths = [ROOT/'.runtime/round-20261021'/name/'host-contract-v1.json'
                      for name in ('water-startup-protocol-v2','trace-lifetime-v2')]
    contracts = [json.loads(path.read_bytes()) for path in contract_paths]
    py_equal = {}
    for name in ('capture_native_burst.py','capture_native_burst_deferred.py','capture_native_burst_startup.py'):
        matches = [[(path,value) for path,value in contract['sources'].items() if Path(path).name == name][0]
                   for contract in contracts]
        py_equal[name] = dict(bytes_equal=Path(matches[0][0]).read_bytes()==Path(matches[1][0]).read_bytes(),
            formal_sha256=matches[0][1],trace_sha256=matches[1][1])
    before_path = ROOT/'.runtime/round-20261021/water-startup-protocol-v2/candidate/tools/native_wgc/startup/burst_window_capture.cpp'
    after_path = ROOT/'.runtime/round-20261021/trace-lifetime-v2/source/burst_window_capture.cpp'
    before,after=before_path.read_text('utf-8'),after_path.read_text('utf-8')
    patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='formal/burst_window_capture.cpp',tofile='trace/burst_window_capture.cpp'))
    patch_path=WORK/'formal-to-trace-cpp-readonly.patch'
    with patch_path.open('x',encoding='utf-8',newline='') as stream:
        stream.write(patch)
    result=dict(schema=1,read_only=True,MC_started=False,root_cause_identified=False,
        no_thresholds_changed=True,previous_results_preserved=True,records=records,
        contracts={str(path):sha(path) for path in contract_paths},python_wrapper_comparison=py_equal,
        cpp_diff=dict(formal_source_sha256=sha(before_path),trace_source_sha256=sha(after_path),
            path=str(patch_path),sha256=sha(patch_path),
            differences='Trace adds fixed numeric poll/arrival/lifetime storage and timestamps, changing scheduling overhead; original acquisition/wait/buffer/timeline remain.'),
        limitation='Per-frame poll/readback observations cannot observe empty polling or callbacks in the nontrace run. A long unobserved interval cannot assign CPU, engine, compositor, WGC or driver cause.')
    output=WORK/'gap-readonly-r27-v1.json'
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(dict(summary_sha256=sha(output),records=[dict(
        directory=record['directory'],maximum_poll_through_readback_ms=record['maximum_poll_through_readback_ms'],
        maximum_readback_to_after_ms=record['maximum_readback_to_after_ms'],
        worst_gap=record['worst_gaps'][0]) for record in records])))


if __name__ == '__main__':
    main()

"""Preserve missing observations as null; inspect worker and source gaps separately."""
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def millis(first, second):
    return (second - first) / 10000. if first > 0 and second > 0 else None


def main():
    records = []
    for directory in (WORK.with_name('water-size720-v3'), WORK):
        path = next(directory.glob('*_burst/manifest.json'))
        manifest = json.loads(path.read_bytes())
        start = manifest['request_qpc_100ns']
        rows = []
        for frame in manifest['frames']:
            before = frame['before']['observed_qpc_100ns']
            read = frame['after_readback']['observed_qpc_100ns']
            guard = frame['capture_last_window_state']['observed_qpc_100ns']
            source = frame['frame_qpc_100ns']
            rows.append(dict(sequence=frame['sequence'],capture_valid=frame['capture_valid'],
                before_qpc_100ns=before or None,readback_qpc_100ns=read or None,
                capture_guard_qpc_100ns=guard or None,source_qpc_100ns=source or None,
                source_from_measurement_start_ms=millis(start,source),
                before_from_measurement_start_ms=millis(start,before),
                readback_from_measurement_start_ms=millis(start,read),
                source_age_at_poll_ms=millis(source,before),
                poll_through_readback_ms=millis(before,read),
                readback_to_capture_guard_ms=millis(read,guard)))
        adjacent = []
        for first,second in zip(rows,rows[1:]):
            if not first['capture_valid'] or not second['capture_valid']:
                continue
            adjacent.append(dict(first_sequence=first['sequence'],second_sequence=second['sequence'],
                source_gap_ms=millis(first['source_qpc_100ns'],second['source_qpc_100ns']),
                worker_unobserved_from_capture_guard_ms=millis(first['capture_guard_qpc_100ns'],second['before_qpc_100ns']),
                worker_unobserved_from_readback_ms=millis(first['readback_qpc_100ns'],second['before_qpc_100ns'])))
        maxima = {}
        for field in ('poll_through_readback_ms','readback_to_capture_guard_ms'):
            observed=[row for row in rows if row[field] is not None]
            worst=max(observed,key=lambda row:row[field])
            maxima[field]=dict(sequence=worst['sequence'],value=worst[field],observed_frames=len(observed))
        records.append(dict(directory=str(directory),manifest_sha256=sha(path),
            attempts=len(rows),valid_frames=sum(row['capture_valid'] for row in rows),
            undefined_observations=[row['sequence'] for row in rows if row['readback_qpc_100ns'] is None],
            maximum_observed_frame_stages=maxima,
            largest_source_gaps=sorted(adjacent,key=lambda row:row['source_gap_ms'],reverse=True)[:5],
            largest_worker_unobserved_intervals=sorted(adjacent,key=lambda row:row['worker_unobserved_from_capture_guard_ms'],reverse=True)[:5],
            per_frame_observable_stages=rows,
            lifecycle_events_instrumented=bool(manifest.get('diagnostic_frame_lifetime_events'))))
    result=dict(schema=2,read_only=True,MC_started=False,no_thresholds_changed=True,
        previous_results_preserved=True,formal_A_accepted=False,root_cause_identified=False,
        host_sha256=sha(Path(__file__)),records=records,
        supersedes_summary=str(WORK/'gap-readonly-r27-v1.json'),
        correction='An invalid final frame has no readback observation (raw 0). Keep that observation null and exclude undefined durations; the prior derived max was not meaningful.',
        limitation='The nontrace helper does not instrument empty polling, callback arrival, Close or COM release. An interval between successful frame observations cannot assign a game, DWM, WGC, scheduler or driver cause.')
    path=WORK/'gap-readonly-r27-v2.json'
    with path.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(dict(sha256=sha(path),records=[{key:value for key,value in row.items()
        if key!='per_frame_observable_stages'} for row in records])))


if __name__ == '__main__':
    main()

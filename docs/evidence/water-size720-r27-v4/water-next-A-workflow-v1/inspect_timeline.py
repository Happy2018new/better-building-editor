"""Inspect immutable source-frame and worker observation clocks separately."""
import argparse
import hashlib
import json
from pathlib import Path


def observed(value):
    return value if type(value) is int and value > 0 else None


def delta(first, second):
    return (second - first) / 10000. if first is not None and second is not None else None


def inspect(manifest):
    start = observed(manifest['request_qpc_100ns'])
    end = observed(manifest['planned_end_qpc_100ns'])
    rows = []
    for frame in manifest['frames']:
        source = observed(frame.get('frame_qpc_100ns'))
        before = observed(frame.get('before', {}).get('observed_qpc_100ns'))
        readback = observed(frame.get('after_readback', {}).get('observed_qpc_100ns'))
        guard = observed(frame.get('capture_last_window_state', {}).get('observed_qpc_100ns'))
        initial = observed(frame.get('initial_timestamp_assessment', {}).get('observed_qpc_100ns'))
        rows.append({'sequence': frame['sequence'], 'capture_valid': frame['capture_valid'],
                     'source_qpc_100ns': source, 'before_qpc_100ns': before,
                     'initial_qpc_100ns': initial, 'readback_qpc_100ns': readback,
                     'capture_guard_qpc_100ns': guard,
                     'source_from_fixed_start_ms': delta(start, source),
                     'worker_before_from_fixed_start_ms': delta(start, before),
                     'source_age_at_poll_ms': delta(source, before),
                     'poll_through_readback_ms': delta(before, readback),
                     'readback_to_capture_guard_ms': delta(readback, guard)})
    valid = [row for row in rows if row['capture_valid'] and row['source_qpc_100ns'] is not None]
    pairs = []
    for first, second in zip(valid, valid[1:]):
        pairs.append({'first_sequence': first['sequence'], 'second_sequence': second['sequence'],
                      'source_gap_ms': delta(first['source_qpc_100ns'], second['source_qpc_100ns']),
                      'worker_before_gap_ms': delta(first['before_qpc_100ns'], second['before_qpc_100ns']),
                      'worker_unobserved_after_capture_guard_ms':
                          delta(first['capture_guard_qpc_100ns'], second['before_qpc_100ns']),
                      'worker_unobserved_after_readback_ms':
                          delta(first['readback_qpc_100ns'], second['before_qpc_100ns'])})
    source_max = max(pairs, key=lambda row: row['source_gap_ms']) if pairs else None
    worker_pairs = [row for row in pairs if row['worker_unobserved_after_capture_guard_ms'] is not None]
    worker_max = max(worker_pairs, key=lambda row: row['worker_unobserved_after_capture_guard_ms']) if worker_pairs else None
    return {'schema': 1, 'scope': 'Observed timestamps only; missing observations stay null; no root-cause attribution',
            'request_qpc_100ns': start, 'planned_end_qpc_100ns': end,
            'fixed_measurement_ms': delta(start, end),
            'manifest_capture_valid': manifest.get('capture_valid'),
            'manifest_temporal_complete': manifest.get('temporal_complete'),
            'manifest_ok': manifest.get('ok'),
            'attempts': len(rows), 'valid_frames': len(valid),
            'start_source_gap_ms': delta(start, valid[0]['source_qpc_100ns']) if valid else None,
            'tail_source_gap_ms': delta(valid[-1]['source_qpc_100ns'], end) if valid else None,
            'largest_source_gap': source_max, 'largest_worker_unobserved_interval': worker_max,
            'source_and_worker_maximum_same_pair': source_max == worker_max,
            'source_gap_limit_ms': manifest.get('max_gap_ms'),
            'source_gap_exceedances': [row for row in pairs if row['source_gap_ms'] > manifest['max_gap_ms']],
            'adjacent_valid_pairs': pairs, 'per_attempt': rows,
            'formal_A_accepted': False, 'root_cause_identified': False,
            'no_timeline_trim_or_threshold_changes': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    raw = args.manifest.read_bytes()
    result = inspect(json.loads(raw))
    result.update(manifest_path=str(args.manifest.resolve()),
                  manifest_sha256=hashlib.sha256(raw).hexdigest(),
                  analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    assert args.manifest.read_bytes() == raw
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('per_attempt', 'adjacent_valid_pairs')}))


if __name__ == '__main__':
    main()

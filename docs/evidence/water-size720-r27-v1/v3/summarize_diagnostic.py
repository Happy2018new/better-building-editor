"""Read the single editor diagnostic without converting it into qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent


def main():
    burst = next(WORK.glob('*_burst'))
    path = burst / 'manifest.json'
    manifest = json.loads(path.read_bytes())
    wrapper_path = burst.with_name(burst.name + '.capture.json')
    wrapper = json.loads(wrapper_path.read_bytes())
    report_path = WORK / 'diagnostic-east-editor-size720-v1.json'
    report = json.loads(report_path.read_bytes())
    group = json.loads((WORK / 'group-execution-v1.json').read_bytes())
    restore = json.loads((WORK / 'independent-restore-v1.json').read_bytes())
    module_path = ROOT / '.runtime/round-20261021/trace-lifetime-v2/analyze_lifetime_trace.py'
    spec = importlib.util.spec_from_file_location('lifetime_analysis', module_path)
    lifetime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifetime)
    lifecycle = lifetime.analyze(manifest)
    with (WORK / 'lifetime-analysis-r27-v1.json').open('x', encoding='utf-8') as stream:
        json.dump(lifecycle, stream, indent=2)
    frames = [frame for frame in manifest['frames'] if frame['capture_valid']]
    frames.sort(key=lambda frame: frame['frame_qpc_100ns'])
    assert len(frames) == wrapper['validated_timeline']['valid_frames']
    stamps = [frame['frame_qpc_100ns'] for frame in frames]
    start = (stamps[0] - manifest['request_qpc_100ns']) / 10000.
    interior = max((b-a for a, b in zip(stamps, stamps[1:])), default=0) / 10000.
    tail = (manifest['planned_end_qpc_100ns'] - stamps[-1]) / 10000.
    arrivals = manifest['diagnostic_arrivals']
    arrival_stamps = [event['begin_qpc_100ns'] for event in arrivals]
    guard = json.loads((WORK / 'continuous-handle-guard-v1.json').read_bytes())
    resource = {}
    for kind in ('game', 'mcdk'):
        values = [row[kind]['handles'] for row in guard['samples'] if row[kind]['handles'] is not None]
        resource[kind] = {'maximum_handles': max(values),
                         'maximum_adjacent_growth': max((b-a for a, b in zip(values, values[1:])), default=0)}
    result = {'schema': 1, 'diagnostic_only': True, 'formal_A_accepted': False,
        'production_admission_performed': False, 'world_A_accepted': False,
        'manual_closures_added': 0, 'owner': group['owner'],
        'source_contract_sha256': group['source_contract_sha256'],
        'inputs': {str(p): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size}
                   for p in (path, wrapper_path, report_path, module_path)},
        'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'capture_valid': wrapper['capture_valid'], 'temporal_complete': wrapper['temporal_complete'],
        'native_window_size': [wrapper['window']['width'], wrapper['window']['height']],
        'start_gap_ms': start, 'maximum_interior_gap_ms': interior, 'tail_gap_ms': tail,
        'actual_gap_limit_ms': 150, 'valid_frames': len(frames), 'attempted_frames': len(manifest['frames']),
        'arrival_events': len(arrivals), 'maximum_arrival_gap_ms': max((b-a for a,b in zip(arrival_stamps, arrival_stamps[1:])), default=0)/10000.,
        'lifecycle': {key:value for key,value in lifecycle.items() if key != 'frames'},
        'peak_accounted_buffer_bytes': manifest['peak_accounted_buffer_bytes'],
        'total_buffer_limit_bytes': manifest['total_buffer_limit_bytes'],
        'report_completed': report['completed'], 'report_restored': report['restored'],
        'source_unchanged': report['source_unchanged'], 'cleanup_errors': report['cleanup_errors'],
        'independent_standard_restore_passed': restore['passed'],
        'explicit_bootstrap_retirement_recorded': (WORK / 'bootstrap-marker-retired-v1.json').exists(),
        'resource': resource, 'continuous_guard_sample_count': len(guard['samples']),
        'guard_breach': guard['guard_breach'], 'modal_guard_breach': guard.get('modal_guard_breach'),
        'limitations': ['One changed size and a different frozen product source do not establish the cause of the old S0 callback gap.',
                       'Private lifetime trace is not the pinned formal A helper.',
                       'No old pixel ROI or world-camera qualification was reused.']}
    with (WORK / 'diagnostic-summary-r27-v1.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({key: result[key] for key in ('capture_valid', 'temporal_complete', 'start_gap_ms',
           'maximum_interior_gap_ms', 'tail_gap_ms', 'valid_frames', 'report_restored', 'formal_A_accepted')}))


if __name__ == '__main__':
    main()

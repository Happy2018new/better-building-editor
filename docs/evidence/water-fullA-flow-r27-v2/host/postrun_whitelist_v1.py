"""Read-only, bounded post-run receipt; never prints nested capture/session data."""
import hashlib
import json
from pathlib import Path
import time

WORK = Path(__file__).resolve().parent


def load(name):
    return json.loads((WORK / name).read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'postrun-whitelist-v1.json'
    assert not output.exists()
    binding = load('final-source-binding-v1.json')
    group = load('group-execution-v1.json')
    camera = load('product-v2-camera-seam-v1.json')
    product = load('product-v2-a-v1.json')
    exit_receipt = load('launch/exact-exit.json')
    project = Path(binding['project'])
    source_checks = {}
    for name, key in (('source', 'source_sha256'), ('auxiliary', 'auxiliary_sha256')):
        expected = binding[key]
        mismatches = []
        for relative, expected_sha in expected.items():
            path = project / relative
            if not path.is_file() or sha(path) != expected_sha:
                mismatches.append(relative)
        source_checks[name] = {'checked': len(expected), 'matched': len(expected) - len(mismatches),
                               'mismatches': mismatches, 'passed': not mismatches}
    cells = []
    for key, burst in product['flow_bursts'].items():
        capture = burst['capture']
        native = capture['native_manifest']
        images = [frame['png'] for frame in capture['frames'] if frame.get('png')]
        assert images
        cells.append({
            'key': key,
            **{field: capture[field] for field in ('ok', 'reliable', 'capture_valid', 'temporal_complete')},
            **{field: native[field] for field in ('attempted_frames', 'valid_frames', 'rejected_frames',
                                                  'maximum_gap_100ns', 'start_gap_100ns', 'tail_gap_100ns')},
            'raw_manifest': capture['native_manifest_file'],
            'first_valid_png': {field: images[0][field] for field in ('path', 'sha256', 'bytes')},
            'last_valid_png': {field: images[-1][field] for field in ('path', 'sha256', 'bytes')},
            'static_pngs': [{field: product['captures'][name][field] for field in ('path', 'sha256', 'bytes')}
                            for name in (key, key + '_later')],
        })
    processes = {}
    for role, process in exit_receipt['processes'].items():
        processes[role] = {field: process[field] for field in ('pid', 'identity', 'exit_code', 'exit_code_hex')}
    restores = {}
    for filename in ('independent-restore-after-camera.json', 'independent-restore-v1.json'):
        receipt = load(filename)
        restores[filename] = {field: receipt[field] for field in ('restored', 'restore_unknown', 'source_unchanged')}
    result = {
        'schema': 1, 'owner': binding['owner'], 'checked_at': time.time(),
        'scope': 'Capture and cleanup only; strict pixel/flow analysis and qualification remain separate.',
        'group_completed': group['completed'], 'group_elapsed_seconds': group['elapsed_seconds'],
        'camera': {field: camera[field] for field in ('passed', 'completed', 'restored', 'cleanup_errors')},
        'product': {field: product[field] for field in ('completed', 'restored', 'cleanup_errors', 'source_unchanged')},
        'source_checks': source_checks,
        'source_before_after_equal': product['source_file_sha256_before'] == product['source_file_sha256_after'],
        'independent_restores': restores,
        'static_count': len(product['captures']),
        'all_static_ok': all(capture['ok'] for capture in product['captures'].values()),
        'cells': cells, 'all_cell_capture_valid': all(cell['capture_valid'] for cell in cells),
        'all_cell_temporal_complete': all(cell['temporal_complete'] for cell in cells),
        'ordinary_stop_exit_code': group['ordinary_stop']['exit_code'],
        'exact_identities_absent': group['exact_identities_absent'],
        'exit_observer_completed': exit_receipt['completed'], 'processes': processes,
        'helper_retirement': {field: load('helper-retirement-v1.json')[field]
                              for field in ('game_and_mcdk_identities_absent', 'exact_helper_terminated')},
        'reports': {name: {'sha256': sha(WORK / name), 'bytes': (WORK / name).stat().st_size}
                    for name in ('group-execution-v1.json', 'product-v2-camera-seam-v1.json',
                                 'product-v2-a-v1.json', 'launch/exact-exit.json')},
        'formal_A_accepted': False, 'production_admission_performed': False, 'manual_closures_added': 0,
    }
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'sha256': sha(output),
                      'source_matched': source_checks['source']['matched'],
                      'auxiliary_matched': source_checks['auxiliary']['matched'],
                      'cells': len(cells), 'capture_valid': result['all_cell_capture_valid'],
                      'temporal_complete': result['all_cell_temporal_complete'],
                      'valid_frames': sum(cell['valid_frames'] for cell in cells),
                      'rejected_frames': sum(cell['rejected_frames'] for cell in cells)}, ensure_ascii=True))


if __name__ == '__main__':
    main()

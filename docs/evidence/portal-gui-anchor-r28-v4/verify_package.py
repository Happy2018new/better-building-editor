"""Offline evidence verification. Uses only the Python standard library.

No game, watcher, process/window mutation, source regeneration or qualification.
Use --write-receipt only when intentionally creating the first review receipt.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(relative):
    path = HERE / relative
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, HERE / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def verify():
    index = read('index.json')
    originals = {}
    for entry in index['entries']:
        path = HERE / entry['path']
        data = path.read_bytes()
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']
        raw = gzip.decompress(data) if entry['encoding'] == 'gzip-mtime-zero' else data
        assert len(raw) == entry['original_bytes'] and sha(raw) == entry['original_sha256'], entry['path']
        assert entry['original_bytes_reconstructable'] and not entry['redactions']
        originals[entry['original_path']] = raw
    for entry in index['derived_entries']:
        data = (HERE / entry['path']).read_bytes()
        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], entry['path']

    sensitive_names = {'api_key', 'apikey', 'access_token', 'refresh_token', 'password',
                       'secret', 'authorization', 'cookie', 'credential', 'credentials'}
    sensitive_patterns = [
        re.compile(r'\b(?:sk|rk|sess)-[A-Za-z0-9_-]{16,}'),
        re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._-]{16,}'),
    ]
    credential_findings = []

    def scan_json(value, label):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in sensitive_names and child not in (None, '', [], {}):
                    credential_findings.append(label + ':' + key)
                scan_json(child, label)
        elif isinstance(value, list):
            for child in value:
                scan_json(child, label)

    text_inputs = []
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or path.suffix not in ('.json', '.py', '.md', '.gz'):
            continue
        if path.name == 'verification-receipt.json':
            continue
        raw = path.read_bytes()
        if path.suffix == '.gz':
            raw = gzip.decompress(raw)
        text = raw.decode('utf8')
        text_inputs.append(path.relative_to(HERE).as_posix())
        for pattern in sensitive_patterns:
            if pattern.search(text):
                credential_findings.append(path.relative_to(HERE).as_posix() + ':token-shape')
        try:
            obj = json.loads(text)
        except ValueError:
            continue
        scan_json(obj, path.relative_to(HERE).as_posix())
        if isinstance(obj, dict) and isinstance(obj.get('stdout'), str):
            try:
                scan_json(json.loads(obj['stdout']), path.relative_to(HERE).as_posix() + ':stdout')
            except ValueError:
                pass
    assert not credential_findings, 'Credential-shaped values present; do not print their contents'

    report = read('raw/report.json.gz')
    closeout = read('provenance/closeout-v1/native-closeout-v1.json')
    assert report['owner'] == index['owner'] == closeout['owner']
    assert report['source_commit'] == index['source_commit']
    assert closeout['report_sha256'] == sha(gzip.decompress((HERE / 'raw/report.json.gz').read_bytes()))
    for key in ('completed', 'restored', 'source_unchanged'):
        assert report[key], key
    assert not report['cleanup_errors'] and len(report['restore_audits']) == 2
    for audit in report['restore_audits']:
        assert all(audit[key] for key in ('fields_equal', 'library_equal', 'profiles_same',
                                         'undo_redo_selection_equal', 'restored', 'preview_ready'))
    assert report['window_restore']['physical_after']['client_size'] == report['original_window']['client_size'] == [1280, 720]
    assert report['manual_issues_closed'] == closeout['manual_issues_closed'] == index['manual_issues_closed'] == 0
    assert not any(report[key] for key in ('qualification_changed', 'production_modified',
                                         'native_candidate_selected', 'star_density_or_animation_accepted',
                                         'runtime_pixels_qualified', 'overlays'))

    source_counts = {}
    for version in ('v3', 'v4'):
        manifest_raw = gzip.decompress((HERE / ('provenance/' + version + '-source-manifest.json.gz')).read_bytes())
        binding_raw = (HERE / ('provenance/' + version + '-host-binding-final.json')).read_bytes()
        source_guard = closeout['source_guards']['portal-gui-anchor-' + version]
        assert sha(manifest_raw) == source_guard['source_manifest_sha256']
        assert sha(binding_raw) == source_guard['host_binding_sha256']
        manifest = json.loads(manifest_raw)
        assert len(manifest['files']) == source_guard['runtime_files'] == 3712
        assert len(manifest['host_files']) == source_guard['historical_helpers'] == 36
        assert source_guard['all_bound_bytes_unchanged']
        assert manifest['source_commit'] == index['source_commit']
        if version == 'v4':
            assert manifest['helper_source_commit'] == index['source_commit']
        source_counts[version] = {'runtime': len(manifest['files']), 'historical_helpers': len(manifest['host_files'])}

    v4_manifest = read('provenance/v4-source-manifest.json.gz')
    assert read('provenance/v3-source-manifest.json.gz')['host_files'] == v4_manifest['host_files']
    v4_binding = read('provenance/v4-host-binding-final.json')
    for relative, expected in v4_binding['files'].items():
        data = gzip.decompress((HERE / 'provenance/v4-source-manifest.json.gz').read_bytes()) if relative == 'source-manifest.json' else (HERE / 'host' / relative).read_bytes()
        assert sha(data) == expected, relative
    for relative, expected in v4_binding['offline_control_receipts'].items():
        assert sha((HERE / 'host' / relative).read_bytes()) == expected, relative
    for path in (HERE / 'source').rglob('*'):
        if path.is_file():
            relative = path.relative_to(HERE / 'source').as_posix()
            assert sha(path.read_bytes()) == v4_manifest['files'][relative], relative
    external = read('host/external-host-binding.json')
    for relative, expected in external.items():
        copied = HERE / 'external' / Path(relative).name
        if copied.exists():
            assert sha(copied.read_bytes()) == expected, relative

    module('camera_gate', 'host/camera_gate.py')
    protocol = module('protocol', 'host/protocol.py')
    native = read('analysis/native-triplets.json')
    assert native['source_report_sha256'] == closeout['report_sha256']
    assert len(native['triplets']) == 6
    pngs = list((HERE / 'captures').glob('*.png'))
    assert len(pngs) == index['original_PNG_count'] == 18
    assert sum(p.stat().st_size for p in pngs) == index['original_PNG_bytes']
    stats = []
    for family in report['families']:
        assert family['completed'] and len(family['stages']) == 9 and len(family['triplets']) == 3
        stage_map = {(s['gui'], s['stage']): s for s in family['stages']}
        expected_document = family['load']['document']
        for stage in family['stages']:
            assert stage['completed']
            for phase in ('before', 'after'):
                assert protocol.require_state(stage[phase], expected_document, family['family'], stage['gui'], stage['stage'])
            protocol.capture_stable(stage['before'], stage['after'])
            capture = stage['capture']
            path = HERE / 'captures' / Path(capture['path']).name
            data = path.read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n'
            dimensions = list(struct.unpack('>II', data[16:24]))
            assert dimensions == capture['size'] == list(dict(protocol.SAMPLES)[stage['gui']])
            assert sha(data) == capture['sha256'] and not capture['pixels_accepted']
            host = read('captures/' + path.with_suffix('.host.json').name)
            receipt = json.loads(host['stdout'])
            assert host['returncode'] == 0 and not host['stderr']
            assert receipt['ok'] and receipt['reliable'] and receipt['background_safe'] and receipt['foreground_unchanged']
            assert receipt['sha256'] == capture['sha256'] and receipt['bytes'] == len(data)
            assert receipt['frame']['backend'] == 'Windows.Graphics.Capture' and receipt['frame']['native_resolution']
            assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']

        for item in family['triplets']:
            gui = item['gui']
            states = {name: stage_map[(gui, name)]['after'] for name in ('a', 'b', 'a_return')}
            replayed = protocol.triplet(states['a'], states['b'], states['a_return'], gui)
            assert replayed == item['deltas']
            derived = next(t for t in native['triplets'] if t['family'] == family['family'] and t['gui'] == gui)
            assert len(derived['rows']) == len(replayed)
            max_native_error = 0.
            max_native_position_error = 0.
            for row in derived['rows']:
                key = row['key']
                geometries = {stage: next(g for g in state['portal_geometry'] if g['key'] == key)
                              for stage, state in states.items()}
                assert row['native_all_slots'] == {stage: g['slots'] for stage, g in geometries.items()}
                assert row['cached_geometry'] == {stage: g['geometry'] for stage, g in geometries.items()}
                assert row['native_A_return_slots_value_equal']
                assert geometries['a']['slots'] == geometries['a_return']['slots']
                for stage, g in geometries.items():
                    slot = next(s for s in g['slots'] if s['slot'] == g['front'])
                    assert row['native_active_slots'][stage] == slot
                    assert row['native_positions'][stage] == slot['position']
                    binding = next(b for b in states[stage]['native_portal_doll_readback'] if b['key'] == key)
                    assert row['native_doll_bindings'][stage] == binding
                    max_native_position_error = max(max_native_position_error,
                        *(abs(slot['position'][i] - g['geometry'][0][i]) for i in range(2)))
                prediction = min(geometries['a']['size']) * (1. / gui - 1. / 4.)
                actual = row['native_positions']['b'][1] - row['native_positions']['a'][1]
                assert row['predicted_logical_dy'] == prediction
                assert row['native_logical_dy'] == actual
                assert row['native_prediction_difference'] == actual - prediction
                assert row['cached_logical_dy'] == geometries['b']['geometry'][0][1] - geometries['a']['geometry'][0][1]
                assert abs(actual - prediction) < .001
                if gui == 4:
                    assert actual == prediction == 0.
                max_native_error = max(max_native_error, abs(actual - prediction))
            stats.append({'family': family['family'], 'gui': gui, 'groups': len(replayed),
                          'max_cached_prediction_error': max(abs(d['actual_logical_dy'] - d['predicted_logical_dy']) for d in replayed),
                          'max_native_prediction_error': max_native_error,
                          'max_native_position_vs_cached_error': max_native_position_error,
                          'A_return_all_native_slots_equal': True})

    assert closeout['ordinary_stop_returncode'] == 1 and closeout['ordinary_stop_grace_seconds'] == 45
    assert not closeout['force_executed']
    assert closeout['registry_finalize_returncode'] == 0 and closeout['registry_final_state'] == 'stopped'
    assert closeout['exact_exit_codes']['game']['exit_code'] == 3221226505
    assert closeout['exact_exit_codes']['game']['exit_code_hex'] == '0xC0000409' and closeout['game_exit_is_abnormal']
    assert closeout['exact_exit_codes']['mcdk']['exit_code'] == 0
    assert all(r['owned_identity_absent'] for r in closeout['exact_owned_identities_absent'])
    assert not closeout['watcher_errors'] and not closeout['watcher_other_assertions']
    assert closeout['watcher_known_assert_recoveries'] == 0
    assert not closeout['watcher_manifest_read_events'] and not closeout['startup_assigned_manifest_read_events']
    retirement = read('provenance/closeout-v1/helper-retirement-v1.json')
    assert retirement['completed'] and not retirement['game_or_mcdk_touched']
    assert sha((HERE / 'provenance/closeout-v1/helper-retirement-v1.json').read_bytes()) == closeout['helper_retirement_sha256']
    review = read('analysis/root-visual-review-scope.json')
    assert review['count'] == len(review['original_PNGs_reviewed_by_root']) == 10
    assert not review['pixels_or_animation_accepted']
    return {
        'schema': 1, 'passed': True, 'mode': 'offline',
        'index_sha256': sha((HERE / 'index.json').read_bytes()),
        'original_entries': len(index['entries']), 'derived_entries': len(index['derived_entries']),
        'original_PNGs': len(pngs), 'original_PNG_bytes': index['original_PNG_bytes'],
        'report_original_sha256': closeout['report_sha256'],
        'source_counts': source_counts, 'bound_host_objects': len(v4_binding['files']),
        'bound_offline_controls': len(v4_binding['offline_control_receipts']),
        'protocol_before_after_checks': 36, 'capture_stability_checks': 18,
        'triplets': stats, 'native_groups_total': sum(s['groups'] for s in stats),
        'restore_audits': 2, 'ordinary_stop_returncode': 1,
        'game_exit': '0xC0000409', 'game_exit_abnormal': True, 'force_executed': False,
        'text_inputs_scanned': len(text_inputs), 'credential_findings': 0,
        'root_visual_review_PNGs': 10, 'manual_issues_closed': 0,
        'production_modified': False, 'qualification_changed': False,
        'pixels_or_animation_accepted': False,
        'runtime_source_guard_scope': 'Original live closeout guard receipt and byte-exact manifests preserved; no new live runtime requalification',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-receipt', action='store_true')
    args = parser.parse_args()
    result = verify()
    if args.write_receipt:
        output = HERE / 'verification-receipt.json'
        assert not output.exists(), 'Do not replace an existing review receipt'
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=True))

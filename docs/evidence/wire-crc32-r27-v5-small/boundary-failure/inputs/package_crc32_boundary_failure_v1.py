"""Small original-byte evidence for the stopped CRC boundary failure."""
import gzip
import hashlib
import json
from pathlib import Path

from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'crc32-boundary-failure-small-v1'
PART = 250000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    OUT.mkdir()
    known = []
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    rows = []
    scans = []

    def add(name, raw, original=None, transform='none'):
        findings, stats = credential_scan(raw, known)
        assert not findings, name
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        encoding = 'gzip' if len(raw) >= PART else 'identity'
        stored = gzip.compress(raw, compresslevel=9, mtime=0) if encoding == 'gzip' else raw
        chunks = []
        for index, offset in enumerate(range(0, max(len(stored), 1), PART), 1):
            part_name = name + ('.gz' if encoding == 'gzip' else '') + ('.part%03d' % index if len(stored) > PART else '')
            path = OUT / part_name
            path.parent.mkdir(parents=True, exist_ok=True)
            chunk = stored[offset:offset + PART]
            path.write_bytes(chunk)
            chunks.append({'path': part_name, 'bytes': len(chunk), 'sha256': sha(chunk)})
        rows.append({'object': name, 'original_source': original,
                     'original_sha256': sha(raw) if original else None,
                     'derived_from': [], 'content_transform': transform,
                     'content_sha256': sha(raw), 'content_bytes': len(raw),
                     'redacted': False, 'encoding': encoding, 'parts': chunks})

    def source(path, name):
        add(name, path.read_bytes(), path.relative_to(ROOT).as_posix())

    for name in ('report.json', 'gate.json', 'observer-retirement.json',
                 'rpc-0939-result.json', 'rpc-1021.py', 'rpc-1021-result.json',
                 'rpc-1024-result.json', 'rpc-1033-result.json'):
        source(HERE / 'flat-boundary-actual-v5' / name, 'boundary/' + name)
    for name in ('stop.json', 'exact-exit.json', 'watcher-stop-v6.json', 'watch-binding.json',
                 'assert-watch/status.json'):
        source(HERE / 'launch-v5' / name, 'lifecycle/' + name)
    for name in ('trial_capture_v5.py', 'phase_transport_v5.py', 'session_reader_v2.py',
                 'frozen-trial-plan-v5.json', 'frozen-cold-lifecycle-plan-v6.json',
                 'retire_crc32_watcher_v5.py', 'package_crc32_boundary_failure_v1.py'):
        source(HERE / name, 'inputs/' + name)
    external = ROOT / '.runtime/round-20261022/water-anchor-watcher-v5'
    for name in ('watch_owned_disabled_skin_assert_r27_v5.py', 'windows_manifest_reader.py'):
        source(external / name, 'inputs/' + name)
    source(HERE / 'verify_review_bundle_v3.py', 'verify_bundle.py')
    report = json.loads((HERE / 'flat-boundary-actual-v5/report.json').read_bytes())
    receipt = json.loads((HERE / 'flat-boundary-actual-v5/observer-retirement.json').read_bytes())
    last = json.loads((HERE / 'flat-boundary-actual-v5/rpc-1021-result.json').read_bytes())
    summary = {
        'schema': 'wire-r27-CRC-boundary-watch-read-failure-v1',
        'completed': report['completed'], 'restored': report['restored'],
        'error': report['error'], 'cleanup_errors': report['cleanup_errors'],
        'captured_tool_traceback_call_chain': [
            'phase_transport_v5.collect:118 check.run(CHUNK)',
            'trial_capture_v5.Check.run:211 boundary before RPC entry/dispatch',
            'trial_capture_v5.boundary:203 session_reader.read_json(args.watch)',
            'session_reader_v2.read_json:34 bounded_manifest_read(native_read_json)',
            'windows_manifest_reader.native_read_json:44 json.loads(native_read_bytes(path))',
            'JSONDecodeError: Expecting value: line 1 column 1 (char 0)',
        ],
        'traceback_provenance': 'Derived from captured exec tool process stderr; original process stderr was not separately stored',
        'exact_failed_read_bytes_preserved': False,
        'empty_read_proven': False,
        'watcher_source_has_in_place_truncate_then_write_status_publication': True,
        'completed_phase_exports': 7, 'exported_native_records': 168,
        'observer_final_record_count': receipt['record_count'],
        'phase8_partial_chunks_acknowledged': last['index'] + 1,
        'phase8_expected_chunks': 111,
        'all_completed_chunk_CRC_checks_had_passed': True,
        'MC_chunk_RPC_for_failing_boundary_dispatched': False,
        'independent_runtime_state_audit_restored': report['independent_audit']['restored'],
        'runtime_and_host_unchanged': report['runtime_and_host_unchanged'],
        'ordinary_stop_returncode': 0,
        'retained_actual_game_exit_code': '0xC0000409',
        'retained_actual_MCDK_exit_code': '0x00000000',
        'watcher_cleanup_exit_code': '0x00000001', 'genuinely_live_MC_after_cleanup': 0,
        'forced_game_or_MCDK_stop': False, 'restarted_after_failure': False,
        'remaining_six_extension_fixtures_run': False,
        'native_exit_cause_attributed': False,
        'production_changed': False, 'GPU_qualified': False, 'manual_closures': 0,
    }
    add('summary.json', json.dumps(summary, indent=2).encode('ascii'), transform='derived failure summary')
    add('credential-scan.json', json.dumps({'passed': True, 'findings': [], 'objects': scans.copy(),
        'known_secret_values_recorded': False}, indent=2).encode('ascii'), transform='derived scan report')
    manifest = {'schema': 'wire-r27-CRC-boundary-failure-small-v1', 'objects': rows,
                'max_stored_file_bytes': max(part['bytes'] for row in rows for part in row['parts']),
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    raw_manifest = json.dumps(manifest, indent=2).encode('ascii')
    (OUT / 'manifest.json').write_bytes(raw_manifest)
    for row in rows:
        stored = b''.join((OUT / part['path']).read_bytes() for part in row['parts'])
        raw = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(raw) == row['content_bytes'] and sha(raw) == row['content_sha256']
        if row['original_source']:
            assert raw == (ROOT / row['original_source']).read_bytes()
    assert all(path.stat().st_size < 300000 for path in OUT.rglob('*') if path.is_file())
    print(json.dumps({'bundle': str(OUT), 'objects': len(rows),
                      'files': sum(path.is_file() for path in OUT.rglob('*')),
                      'bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                      'manifest_sha256': sha(raw_manifest), 'credential_scan_passed': True}))


if __name__ == '__main__':
    main()

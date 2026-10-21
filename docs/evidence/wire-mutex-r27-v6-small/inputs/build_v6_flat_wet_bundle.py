"""Lossless small objects for actual v6 flat and the pre-candidate wet rejection."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'review-bundle-v6-flat-wet-v2'
PART = 250000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    reports = {key: json.loads((HERE / name / 'report.json').read_bytes()) for key, name in
               [('flat', 'flat-interior-actual-v6'), ('wet', 'negative-wet-wire-actual-v6')]}
    assert reports['flat']['completed'] and reports['flat']['restored']
    assert not reports['wet']['completed'] and reports['wet']['restored']
    assert 'Wire contribution changed: opaque_top_repeat' in reports['wet']['error']
    assert all(not report['cleanup_errors'] and report['runtime_and_host_unchanged'] for report in reports.values())
    assert all(not report['read_events'] for report in reports.values())
    known = []
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    OUT.mkdir()
    objects, scans = [], []

    def add(name, raw, original=None, transform='none'):
        findings, stats = credential_scan(raw, known)
        assert not findings, 'Potential credential finding in ' + name
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        encoding = 'gzip' if len(raw) >= PART and not name.endswith(('.png', '.zip')) else 'identity'
        stored = gzip.compress(raw, compresslevel=9, mtime=0) if encoding == 'gzip' else raw
        parts = []
        for index, offset in enumerate(range(0, max(len(stored), 1), PART), 1):
            part = name + ('.gz' if encoding == 'gzip' else '') + ('.part%03d' % index if len(stored) > PART else '')
            chunk = stored[offset:offset + PART]
            target = OUT / part
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(chunk)
            parts.append({'path': part, 'bytes': len(chunk), 'sha256': sha(chunk)})
        objects.append({'object': name, 'original_source': original,
                        'original_sha256': sha(raw) if original else None,
                        'content_transform': transform, 'redacted': False,
                        'content_sha256': sha(raw), 'content_bytes': len(raw),
                        'encoding': encoding, 'parts': parts})

    def source(path, name):
        add(name, path.read_bytes(), path.relative_to(ROOT).as_posix())

    for key, name in [('flat', 'flat-interior-actual-v6'), ('wet', 'negative-wet-wire-actual-v6')]:
        folder = HERE / name
        for member in ('report.json', 'gate.json', 'observer-retirement.json'):
            source(folder / member, key + '/' + member)
        for pattern in ('phase-*-native.json', 'phase-*-complete-original.json', 'phase-*-transport.json'):
            for path in sorted(folder.glob(pattern)):
                source(path, key + '/' + path.name)
        captures = ([('opaque_top', 'base'), ('opaque_top', 'candidate'),
                     ('opaque_grazing', 'base'), ('opaque_grazing', 'candidate'),
                     ('default_top', 'base'), ('default_top', 'candidate')] if key == 'flat'
                    else [('opaque_top', 'base'), ('opaque_top', 'repeat')])
        for view, mode in captures:
            for visibility in (('shown',) if key == 'flat' else ('shown', 'hidden')):
                image = 'report_%s_%s_%s_native.png' % (view, mode, visibility)
                source(folder / image, key + '/images/' + image)
                metadata = image.replace('.png', '.capture.json')
                source(folder / metadata, key + '/images/' + metadata)
        rpc_manifest = []
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted([*folder.glob('rpc-*.py'), *folder.glob('rpc-*-result.json')]):
                raw = path.read_bytes()
                findings, stats = credential_scan(raw, known)
                assert not findings, 'Potential credential finding in RPC member ' + path.name
                scans.append({'archive_entry': key + '/' + path.name, 'findings': findings, 'stats': stats})
                rpc_manifest.append({'entry': path.name, 'source': path.relative_to(ROOT).as_posix(),
                                     'bytes': len(raw), 'sha256': sha(raw)})
                info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, raw, compresslevel=9)
        rpc_bytes = buffer.getvalue()
        with zipfile.ZipFile(io.BytesIO(rpc_bytes)) as archive:
            assert len(archive.namelist()) == len(rpc_manifest)
            for row in rpc_manifest:
                raw = archive.read(row['entry'])
                assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
                assert raw == (ROOT / row['source']).read_bytes()
        add(key + '/all-original-rpc-records.zip', rpc_bytes, transform='byte-preserving archive')
        add(key + '/all-original-rpc-records-manifest.json', json.dumps(rpc_manifest, indent=2).encode('ascii'), transform='derived exact RPC source and digest index')

    for name in ('frozen-trial-plan-v6.json', 'frozen-cold-lifecycle-plan-v7.json', 'project-manifest-v6.json',
                 'freeze-cold-status-v7.json', 'full-input-manifest-cold-status-v7.json',
                 'offline-cold-status-v7-review/report.json',
                 'root-flat-v6-sentinel-review-v1.json', 'actual-crc32-flat-v6-reconciliation.json',
                 'actual-native-deltas-v6-flat.json', 'wet-repeat-v6-readonly-analysis.json',
                 'analyze_wet_repeat_v6.py', 'audit_crc32_actual_v5.py', 'analyze_actual_native_v2.py',
                 'trial_capture_v6.py', 'cold_lifecycle_v7.py', 'phase_transport_v5.py',
                 'trial_payloads_v3.py', 'observer_client_v3.py', 'session_reader_v3.py',
                 'launch-v6/stop.json', 'launch-v6/exact-exit.json', 'launch-v6/watcher-stop-v7.json',
                 'build_v6_flat_wet_bundle.py', 'WIRE_CONTEXT_R27-v6-addendum-draft.md'):
        path = HERE / name
        source(path, 'inputs/' + name)
    status = HERE.parent / 'wire-atomic-watcher-v10'
    source(HERE.parent / 'root-wire-status-v7-review-v1.json', 'inputs/root-wire-status-v7-review-v1.json')
    for name in ('windows-mutex-controls-v2/report.json', 'root-controls-v1/report.json',
                 'status_io.py', 'windows_manifest_reader.py', 'watch_owned_disabled_skin_assert_r27_v10.py'):
        source(status / name, 'inputs/status-host/' + name)
    source(HERE / 'verify_review_bundle_v3.py', 'verify_bundle.py')
    summary = {'schema': 'wire-r27-actual-v6-flat-and-wet-pre-candidate-failure-small-lossless',
               'flat_completed_restored': True, 'flat_phases': 12, 'flat_native_records': 72,
               'flat_original_PNGs': 6, 'wet_completed': False, 'wet_restored': True,
               'wet_candidate_reached': False, 'wet_phases': 2, 'wet_native_records': 12,
               'wet_original_PNGs': 4, 'wet_failure': reports['wet']['error'],
               'actual_game_exit_hex': '0xC0000409', 'actual_MCDK_exit': 0,
               'ordinary_stop_returncode': 0, 'all_owned_process_identities_finally_null': True,
               'all_original_RPC_bytes_included': True,
               'full_cold_archives_repacked': False, 'water_native_uniforms_or_clock_captured': False,
               'water_animation_individual_pixel_causality_proven': False,
               'strict_wire_gate_weakened': False, 'production_changed': False,
               'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    add('summary.json', json.dumps(summary, indent=2).encode('ascii'), transform='derived precise outcome summary')
    scan = {'passed': True, 'findings': [], 'objects_and_archive_members': scans.copy(),
            'raw_known_credentials_recursive_JSON_base64_escaped_members_scanned': True,
            'known_credential_values_recorded': False}
    add('credential-scan.json', json.dumps(scan, indent=2).encode('ascii'), transform='derived recursive credential scan')
    manifest = {'schema': 'wire-r27-small-lossless-v6-flat-wet-bundle', 'objects': objects,
                'max_stored_file_bytes': max(part['bytes'] for row in objects for part in row['parts']),
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    raw_manifest = json.dumps(manifest, indent=2).encode('ascii')
    assert len(raw_manifest) < 300000
    (OUT / 'manifest.json').write_bytes(raw_manifest)
    for row in objects:
        stored = b''.join((OUT / part['path']).read_bytes() for part in row['parts'])
        raw = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(raw) == row['content_bytes'] and sha(raw) == row['content_sha256']
        assert not credential_scan(raw, known)[0]
        if row['original_source']:
            assert raw == (ROOT / row['original_source']).read_bytes()
    assert all(path.stat().st_size < 300000 for path in OUT.rglob('*') if path.is_file())
    print(json.dumps({'bundle': str(OUT), 'objects': len(objects),
                      'files': sum(path.is_file() for path in OUT.rglob('*')),
                      'bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                      'manifest_sha256': sha(raw_manifest), 'credential_scan_passed': True}))


if __name__ == '__main__':
    main()

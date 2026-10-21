"""Preserve the new actual CRC flat as small lossless review objects."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile

from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FLAT = HERE / 'flat-interior-actual-v5'
OUT = HERE / 'review-bundle-crc32-flat-v5'
PART = 250000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    report = json.loads((FLAT / 'report.json').read_bytes())
    assert report['completed'] and report['restored'] and not report['cleanup_errors']
    assert report['runtime_and_host_unchanged']
    known = []
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    OUT.mkdir()
    rows = []
    scans = []

    def add(name, raw, original=None, transform='none', derived_from=()):
        findings, stats = credential_scan(raw, known)
        assert not findings, name
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        encoding = 'gzip' if len(raw) >= PART and not name.endswith(('.png', '.zip')) else 'identity'
        stored = gzip.compress(raw, compresslevel=9, mtime=0) if encoding == 'gzip' else raw
        chunks = []
        for index, offset in enumerate(range(0, max(len(stored), 1), PART), 1):
            part_name = name + ('.gz' if encoding == 'gzip' else '') + ('.part%03d' % index if len(stored) > PART else '')
            chunk = stored[offset:offset + PART]
            path = OUT / part_name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(chunk)
            chunks.append({'path': part_name, 'bytes': len(chunk), 'sha256': sha(chunk)})
        rows.append({'object': name, 'original_source': original,
                     'original_sha256': sha(raw) if original else None,
                     'derived_from': list(derived_from), 'content_transform': transform,
                     'content_sha256': sha(raw), 'content_bytes': len(raw),
                     'redacted': False, 'encoding': encoding, 'parts': chunks})

    def source(path, name):
        add(name, path.read_bytes(), path.relative_to(ROOT).as_posix())

    for name in ('report.json', 'gate.json', 'observer-retirement.json'):
        source(FLAT / name, 'flat/' + name)
    for pattern in ('phase-*-native.json', 'phase-*-complete-original.json', 'phase-*-transport.json'):
        for path in sorted(FLAT.glob(pattern)):
            source(path, 'flat/' + path.name)
    for view in ('opaque_top', 'opaque_grazing', 'default_top'):
        for mode in ('base', 'candidate'):
            name = 'report_%s_%s_shown_native.png' % (view, mode)
            source(FLAT / name, 'flat/images/' + name)
            source(FLAT / name.replace('.png', '.capture.json'), 'flat/images/' + name.replace('.png', '.capture.json'))
    # Keep every original request/result byte; pack to avoid a huge top-level manifest.
    rpc_manifest = []
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted([*FLAT.glob('rpc-*.py'), *FLAT.glob('rpc-*-result.json')]):
            raw = path.read_bytes()
            findings, stats = credential_scan(raw, known)
            assert not findings, path.name
            scans.append({'archive_entry': path.name, 'findings': findings, 'stats': stats})
            rpc_manifest.append({'entry': path.name, 'source': path.relative_to(ROOT).as_posix(),
                                 'bytes': len(raw), 'sha256': sha(raw)})
            info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw, compresslevel=9)
    rpc_raw = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(rpc_raw)) as archive:
        for row in rpc_manifest:
            raw = archive.read(row['entry'])
            assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
            assert raw == (ROOT / row['source']).read_bytes()
    add('flat/all-original-rpc-records.zip', rpc_raw, transform='byte-preserving archive')
    add('flat/all-original-rpc-records-manifest.json', json.dumps(rpc_manifest, indent=2).encode('ascii'),
        transform='derived archive source and digest index')
    for name in ('frozen-trial-plan-v5.json', 'frozen-cold-lifecycle-plan-v6.json',
                 'project-manifest-v5.json', 'freeze-crc32-v6.json',
                 'offline-cold-v6-review.json', 'phase-transport-controls-v5/report.json',
                 'actual-crc32-flat-v5-reconciliation.json', 'actual-native-deltas-v5-flat.json',
                 'audit_crc32_actual_v5.py', 'analyze_actual_native_v2.py',
                 'trial_capture_v5.py', 'phase_transport_v5.py', 'cold_lifecycle_v6.py',
                 'observer_client_v3.py', 'trial_payloads_v3.py',
                 'build_crc32_flat_bundle_v5.py'):
        source(HERE / name, 'inputs/' + name)
    source(HERE / 'verify_review_bundle_v3.py', 'verify_bundle.py')
    summary = {'schema': 'wire-r27-new-CRC-flat-review-v5',
               'completed': True, 'restored': True, 'cleanup_errors': [],
               'engine': report['transport_preflight']['engine'],
               'actual_game_known_answer_CRC32': report['transport_preflight']['crc32'],
               'phase_count': 12, 'native_record_count': 72, 'original_capture_hashes_in_report': 24,
               'original_PNGs_in_bundle': 6, 'original_RPC_files': len(rpc_manifest),
               'same_new_session_sentinel_root_approval_still_required': True,
               'seven_extension_fixtures_completed': False,
               'session_ordinary_stop_completed': False,
               'production_changed': False, 'GPU_qualified': False, 'manual_closures': 0,
               'SHA256_origin': 'Host-derived after complete original game CRC32 chunk reconstruction',
               'acceptance_limits': ['New flat only; no extension fixture qualification',
                                     'Native diagnostic resources remain until ordinary session stop',
                                     'No product promotion or final GPU qualification']}
    add('summary.json', json.dumps(summary, indent=2).encode('ascii'), transform='derived summary')
    scan = {'passed': True, 'findings': [], 'objects_and_archive_members': scans.copy(),
            'known_secret_values_recorded': False,
            'checks': ['raw known credential bytes', 'credential string patterns', 'recursive nested JSON',
                       'base64 JSON members', 'escaped strings', 'every original RPC archive member']}
    add('credential-scan.json', json.dumps(scan, indent=2).encode('ascii'), transform='derived scan report')
    manifest = {'schema': 'wire-r27-review-bundle-crc32-flat-v5', 'objects': rows,
                'max_stored_file_bytes': max(part['bytes'] for row in rows for part in row['parts']),
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    raw_manifest = json.dumps(manifest, indent=2).encode('ascii')
    assert len(raw_manifest) < 300000
    (OUT / 'manifest.json').write_bytes(raw_manifest)
    for row in rows:
        stored = b''.join((OUT / part['path']).read_bytes() for part in row['parts'])
        raw = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(raw) == row['content_bytes'] and sha(raw) == row['content_sha256']
        assert not credential_scan(raw, known)[0]
        if row['original_source']:
            assert raw == (ROOT / row['original_source']).read_bytes()
    assert all(path.stat().st_size < 300000 for path in OUT.rglob('*') if path.is_file())
    print(json.dumps({'bundle': str(OUT), 'objects': len(rows),
                      'files': sum(path.is_file() for path in OUT.rglob('*')),
                      'bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                      'manifest_sha256': sha(raw_manifest), 'credential_scan_passed': True,
                      'production_changed': False, 'GPU_qualified': False}))


if __name__ == '__main__':
    main()

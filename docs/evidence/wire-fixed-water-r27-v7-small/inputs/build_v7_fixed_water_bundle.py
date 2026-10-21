"""Separate lossless v7 fixed-water records; original failed host verdict retained."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'review-bundle-v7-fixed-water-v1'
PART = 250000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    reports = {key: json.loads((HERE / name / 'report.json').read_bytes()) for key, name in
               [('flat', 'flat-interior-fixed-water-actual-v7'), ('wet', 'negative-wet-wire-fixed-water-actual-v7')]}
    assert reports['flat']['completed'] and reports['flat']['restored']
    assert reports['wet']['completed'] and not reports['wet']['restored']
    assert reports['wet']['cleanup_errors']==[{'step':'water_observer','error':'AssertionError: '}]
    assert reports['wet']['independent_audit']['restored'] and reports['wet']['water_retirement']['passed']
    assert all(report['runtime_and_host_unchanged'] for report in reports.values())
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

    for key, name in [('flat', 'flat-interior-fixed-water-actual-v7'), ('wet', 'negative-wet-wire-fixed-water-actual-v7')]:
        folder = HERE / name
        for member in ('report.json', 'gate.json', 'observer-retirement.json'):
            source(folder / member, key + '/' + member)
        for receipt in sorted((folder/'water-receipts').glob('*.json')):
            source(receipt,key+'/water-receipts/'+receipt.name)
        for pattern in ('phase-*-native.json', 'phase-*-complete-original.json', 'phase-*-transport.json'):
            for path in sorted(folder.glob(pattern)):
                source(path, key + '/' + path.name)
        captures = [('opaque_top','base'),('opaque_top','candidate'),
                    ('opaque_grazing','base'),('opaque_grazing','candidate'),
                    ('default_top','base'),('default_top','candidate')]
        for view,mode in captures:
            image='report_%s_%s_shown_native.png'%(view,mode)
            source(folder/image,key+'/images/'+image)
            metadata=image.replace('.png','.capture.json')
            source(folder/metadata,key+'/images/'+metadata)
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

    for name in ('frozen-trial-plan-v7-fixed-water.json','frozen-cold-lifecycle-plan-v8-fixed-water.json',
                 'project-manifest-v7-fixed-water.json','freeze-fixed-water-v1.json','full-input-manifest-fixed-water-v1.json',
                 'root-flat-fixed-water-v7-sentinel-review-v1.json','fixed-water-v7-readonly-ledger-analysis.json',
                 'analyze_fixed_water_actual_v7.py','trial_capture_v7_fixed_water.py','cold_lifecycle_v8_fixed_water.py',
                 'phase_transport_v5.py','trial_payloads_v3.py','observer_client_v3.py','session_reader_v3.py',
                 'fixed-water-v1/water_setter_observer.py','fixed-water-v1/fixed_water_receipts_v1.py',
                 'fixed-water-v1/water_resource_mapping_v1.py','fixed-water-v1/test_water_observer_py2.py',
                 'fixed-water-v1/test_fixed_water_host_v1.py','fixed-water-v1/py2-controls-v1.json',
                 'fixed-water-v1/root-py2-controls-v1.json','fixed-water-v1/host-controls-v1/report.json',
                 'fixed-water-v1/root-host-controls-v1/report.json','fixed-water-v1/complete-host.diff',
                 'fixed-water-v1/water-clock-exact.diff','fixed-water-v1/shader-change-manifest-v1.json',
                 'fixed-water-v1/credential-review.json','launch-v7-fixed-water/stop.json',
                 'launch-v7-fixed-water/exact-exit.json','build_v7_fixed_water_bundle.py',
                 'WIRE_CONTEXT_R27-fixed-water-v7-zh-draft.md'):
        source(HERE/name,'inputs/'+name)
    for name in ('modern_projection_liquid_product_still_water_grey.fragment',
                 'modern_projection_liquid_product_flowing_water_grey.fragment',
                 'modern_projection_liquid_product_flowing_water_grey_top.fragment'):
        source(HERE/'fixed-water-v1'/name,'inputs/fixed-shaders/'+name)
    for name in ('root-wire-fixed-water-review-v1.json',):
        source(HERE.parent/name,'inputs/'+name)
    for name in ('negative-wet-wire-actual-v6/report.json','wet-repeat-v6-readonly-analysis.json'):
        source(HERE/name,'prior-animated-water-v6/'+name)
    status = HERE.parent / 'wire-atomic-watcher-v10'
    for name in ('windows-mutex-controls-v2/report.json', 'root-controls-v1/report.json',
                 'status_io.py', 'windows_manifest_reader.py', 'watch_owned_disabled_skin_assert_r27_v10.py'):
        source(status / name, 'inputs/status-host/' + name)
    source(HERE / 'verify_review_bundle_v3.py', 'verify_bundle.py')
    summary = {'schema':'wire-r27-actual-fixed-water-v7-small-lossless',
               'flat_completed':True,'flat_restored':True,'flat_phases':12,'flat_native_palette_records':72,
               'flat_original_PNGs':6,'wet_completed':True,'wet_restored':False,'wet_phases':12,
               'wet_native_palette_records':72,'wet_original_PNGs':6,
               'wet_original_cleanup_errors':reports['wet']['cleanup_errors'],
               'wet_independent_runtime_audit_restored':True,'wet_native_observer_restoration_passed':True,
               'wet_water_native_calls':864,'wet_actual_FreeModel_creations':72,'wet_actual_FreeModel_removals':72,
               'wet_actual_uniform_acknowledgements':432,'wet_all_strict_opaque_wire_modes_equal':True,
               'readonly_inner_packed_uniform_value_decode_matches':True,'readonly_group_snapshots_checked':288,
               'frozen_report_updated_or_backfilled':False,'source_or_native_receipt_modified':False,
               'actual_game_exit_hex':'0xC0000409','actual_MCDK_exit':0,'ordinary_stop_returncode':0,
               'dedicated_watcher_final_receipt':'Deferred until frozen 07:45 self-exit; supplemental exact receipt required',
               'all_original_RPC_bytes_included':True,'full_cold_archives_repacked':False,
               'water_independent_native_readback':False,'engine_clock_readback':False,
               'individual_v6_pixel_causality_proven':False,'strict_wire_gate_weakened':False,
               'production_changed':False,'candidate_promoted':False,'GPU_qualified':False,'manual_closures':0}
    add('summary.json', json.dumps(summary, indent=2).encode('ascii'), transform='derived precise outcome summary')
    scan = {'passed': True, 'findings': [], 'objects_and_archive_members': scans.copy(),
            'raw_known_credentials_recursive_JSON_base64_escaped_members_scanned': True,
            'known_credential_values_recorded': False}
    add('credential-scan.json', json.dumps(scan, indent=2).encode('ascii'), transform='derived recursive credential scan')
    manifest = {'schema': 'wire-r27-small-lossless-fixed-water-v7-bundle', 'objects': objects,
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

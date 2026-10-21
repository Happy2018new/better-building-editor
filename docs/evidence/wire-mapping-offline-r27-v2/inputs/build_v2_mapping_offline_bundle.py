"""Small exact v2 offline candidate and genuine Py2 export/control review bundle."""
import hashlib
import json
from pathlib import Path
from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'review-bundle-v2-mapping-offline-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    report = json.loads((HERE / 'fixed-water-v2/host-cross-controls-v1/report.json').read_bytes())
    assert report['passed'] and report['control_count'] == 18
    assert not report['MC_started'] and not report['original_reports_or_freeze_modified']
    known = []
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    OUT.mkdir()
    objects, scans = [], []

    def add(name, raw, original=None, transform='none'):
        assert len(raw) < 300000
        findings, stats = credential_scan(raw, known)
        assert not findings, 'Potential credential finding in ' + name
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        path = OUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
        objects.append({'object': name, 'original_source': original,
                        'original_sha256': sha(raw) if original else None,
                        'content_transform': transform, 'content_sha256': sha(raw),
                        'content_bytes': len(raw), 'redacted': False, 'encoding': 'identity',
                        'parts': [{'path': name, 'bytes': len(raw), 'sha256': sha(raw)}]})

    for path in sorted((HERE / 'fixed-water-v2').rglob('*')):
        if path.is_file() and path.suffix not in ('.pyc', '.pyo') and '__pycache__' not in path.parts:
            name = path.relative_to(HERE).as_posix()
            add(name, path.read_bytes(), path.relative_to(ROOT).as_posix())
    for name in ('fixed-water-v1/water_setter_observer.py', 'fixed-water-v1/water_resource_mapping_v1.py',
                 'fixed-water-v1/shader-change-manifest-v1.json', 'prepare_water_mapping_v2.py',
                 'build_v2_mapping_offline_bundle.py', 'verify_review_bundle_v3.py'):
        path = HERE / name
        add('inputs/' + name, path.read_bytes(), path.relative_to(ROOT).as_posix())
    summary = {'schema': 'wire-r27-offline-v2-nonempty-cross-Python-candidate-review',
               'passed_controls': 18, 'real_desktop_Python2_executed_exact_frozen_observer': True,
               'fake_native_in_Python2_controls': True, 'original_v1_mapping_negative_control_retained': True,
               'actual_v7_preserved_evidence_read_only_correlation': True,
               'original_wet_report_completed': True, 'original_wet_report_restored': False,
               'base_v7_evidence_manifest_sha256': sha((HERE / 'review-bundle-v7-fixed-water-v1/manifest.json').read_bytes()),
               'root_independent_review_required': True, 'trial_v1_modified_or_v2_installed': False,
               'MC_started': False, 'production_changed': False, 'candidate_promoted': False, 'manual_closures': 0}
    add('summary.json', (json.dumps(summary, indent=2) + '\n').encode('ascii'), transform='derived precise scope summary')
    add('credential-scan.json', (json.dumps({'passed': True, 'findings': [], 'rows': scans.copy(),
        'known_secret_values_included': False}, indent=2) + '\n').encode('ascii'), transform='derived recursive scan')
    manifest = {'schema': 'wire-r27-offline-v2-mapping-small-review-bundle', 'objects': objects,
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    raw = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    assert len(raw) < 300000
    (OUT / 'manifest.json').write_bytes(raw)
    for row in objects:
        raw = (OUT / row['parts'][0]['path']).read_bytes()
        assert len(raw) == row['content_bytes'] and sha(raw) == row['content_sha256']
        if row['original_source']:
            assert raw == (ROOT / row['original_source']).read_bytes()
    print(json.dumps({'bundle': str(OUT), 'objects': len(objects),
                      'bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                      'manifest_sha256': sha((OUT / 'manifest.json').read_bytes()),
                      'credential_scan_passed': True, 'MC_started': False}))


if __name__ == '__main__':
    main()

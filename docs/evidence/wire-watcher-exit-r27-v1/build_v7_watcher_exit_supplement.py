"""Add separate small exact self-exit receipts after the frozen watcher ends."""
import hashlib
import json
from pathlib import Path
from build_review_bundle_v3 import credential_scan

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'review-bundle-v7-watcher-exit-supplement-v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    assert not OUT.exists()
    source_folder = HERE / 'launch-v7-fixed-water'
    actual = json.loads((source_folder / 'watcher-self-exit-v1.json').read_bytes())
    assert actual['completed'] and all(value is None for value in actual['final_actual_identities'].values())
    assert not actual['process_signalled_or_terminated'] and not actual['process_restarted']
    base = HERE / 'review-bundle-v7-fixed-water-v1/manifest.json'
    assert base.exists()
    known = []
    for path in (Path.home() / '.pyreact-debug/instances').glob('*/session.json'):
        value = json.loads(path.read_bytes()).get('token')
        if isinstance(value, str) and len(value) >= 16:
            known.append(value.encode('utf8'))
    OUT.mkdir()
    rows, scans = [], []

    def add(name, raw, original=None, transform='none'):
        assert len(raw) < 300000
        findings, stats = credential_scan(raw, known)
        assert not findings, name
        scans.append({'object': name, 'findings': findings, 'stats': stats})
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(raw)
        rows.append({'object': name, 'original_source': original,
                     'original_sha256': sha(raw) if original else None, 'content_transform': transform,
                     'content_sha256': sha(raw), 'content_bytes': len(raw), 'redacted': False,
                     'encoding': 'identity', 'parts': [{'path': name, 'bytes': len(raw), 'sha256': sha(raw)}]})

    for name in ('launch-v7-fixed-water/watcher-self-exit-v1.json',
                 'launch-v7-fixed-water/watcher-self-exit-binding-v1.json',
                 'observe_fixed_water_watcher_self_exit_v1.py', 'build_v7_watcher_exit_supplement.py',
                 'launch-v7-fixed-water/stop.json', 'launch-v7-fixed-water/exact-exit.json',
                 'audit_crc32_fixed_water_actual_v7.py',
                 'actual-crc32-fixed-water-v7-flat-reconciliation.json',
                 'actual-crc32-fixed-water-v7-wet-reconciliation.json'):
        path = HERE / name
        add(name, path.read_bytes(), path.relative_to(ROOT).as_posix())
    summary = {'schema': 'wire-r27-fixed-water-v7-watcher-final-self-exit-supplement',
               'completed': True, 'base_manifest_sha256': sha(base.read_bytes()),
               'all_owned_game_MCDK_watcher_final_identities_null': True,
               'watcher_retained_handle_actual_exit_code': actual['retained_handle_actual_exit_code'],
               'watcher_retained_handle_actual_exit_hex': actual['retained_handle_actual_exit_hex'],
               'watcher_observed_exit_at': actual['observed_exit_at'],
               'game_exit_hex': '0xC0000409', 'MCDK_exit_hex': '0x00000000',
               'ordinary_stop_returncode': 0, 'all_actual_exit_codes_zero': False,
               'force_or_restart_executed': False, 'watcher_frozen_source_or_configuration_modified': False,
               'original_wet_report_restored': False, 'readonly_analysis_does_not_backfill_original_verdict': True,
               'candidate_promoted': False, 'manual_closures': 0}
    add('summary.json', (json.dumps(summary, indent=2) + '\n').encode('ascii'), transform='derived exact final process summary')
    add('credential-scan.json', (json.dumps({'passed': True, 'rows': scans.copy(),
        'known_secret_values_included': False}, indent=2) + '\n').encode('ascii'), transform='derived recursive credential scan')
    manifest = {'schema': 'wire-r27-v7-watcher-exit-small-supplement', 'objects': rows,
                'base_bundle_manifest_sha256': sha(base.read_bytes()),
                'candidate_promoted': False, 'GPU_qualified': False, 'manual_closures': 0}
    raw = (json.dumps(manifest, indent=2) + '\n').encode('ascii')
    assert len(raw) < 300000
    (OUT / 'manifest.json').write_bytes(raw)
    print(json.dumps({'completed': True, 'manifest_sha256': sha(raw),
                      'watcher_exit_hex': actual['retained_handle_actual_exit_hex'],
                      'files': len(rows) + 1, 'credential_scan_passed': True}))


if __name__ == '__main__':
    main()

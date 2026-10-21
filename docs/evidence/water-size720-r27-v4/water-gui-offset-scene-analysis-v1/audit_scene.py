"""Read-only post-run accounting for the completed, frozen GUI Scene attempt."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ATTEMPT = ROOT / '.runtime/round-20261022/water-gui-offset-lifecycle-v4'
OUT = Path(__file__).resolve().parent / 'scene-native-audit-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not OUT.exists(), 'Preserve every previous audit'
    names = ['scene-observation-v1.json', 'group-execution-v1.json',
             'independent-restore-v1.json', 'continuous-handle-guard-v1.json',
             'helper-retirement-v1.json', 'private-source-v1.json',
             'launch/exact-exit.json']
    data = {name: json.loads((ATTEMPT / name).read_bytes()) for name in names}
    scene = data[names[0]]
    group = data[names[1]]
    source = data['private-source-v1.json']
    assert scene['completed'] and scene['restored'] and scene['source_unchanged']
    assert not scene['cleanup_errors'] and not scene.get('error')
    assert group['completed'] and group['ordinary_stop']['exit_code'] == 0
    assert all(group['exact_identities_absent'][kind] for kind in ('game', 'mcdk'))
    assert data['independent-restore-v1.json']['restored']
    project = Path(source['private_project'])
    source_entries = dict(source['source_sha256'])
    source_entries.update(source['auxiliary_sha256'])
    mismatches = [name for name, expected in source_entries.items()
                  if sha(project / name) != expected]
    assert not mismatches
    rows = []
    seams = []
    captures = []
    for phase in scene['phases']:
        assert phase['completed'] and len(phase['rows']) == 8
        for row in phase['rows']:
            native = [sample['native_geometry'] for sample in row['samples']]
            assert len(native) == 3
            assert all(value['complete'] and not value['errors'] for value in native)
            assert row['capture_layout_unchanged']
            capture = row['capture']
            assert all(capture[field] for field in
                       ('ok', 'reliable', 'native_resolution', 'foreground_unchanged', 'background_safe'))
            capture_path = Path(capture['path'])
            assert sha(capture_path) == capture['sha256']
            captures.append({'label': row['label'], 'path': str(capture_path),
                             'sha256': capture['sha256'],
                             'size': [capture['width'], capture['height']]})
            rows.append({'label': row['label'], 'control': row['control'],
                         'native_samples': len(native),
                         'visible_banks_each': [value['visible_banks'] for value in native],
                         'gui_cache': row['samples'][-1]['state']['gui_cache'],
                         'native_complete': True, 'capture_layout_unchanged': True})
        seam = phase.get('resize_existing_water')
        if seam:
            before = seam['before_previous_GUI']
            after = seam['after_actual_event_refresh']
            same = {
                'document_id': before['document_id'] == after['document_id'],
                'source_cells': before['source_cells'] == after['source_cells'],
                'group_keys': sorted(value['key'] for value in before['liquid_groups']) ==
                              sorted(value['key'] for value in after['liquid_groups']),
            }
            assert all(same.values()) and not seam['document_reloaded']
            assert seam['capture_layout_unchanged']
            capture = seam['capture']
            assert sha(Path(capture['path'])) == capture['sha256']
            captures.append({'label': phase['label'] + '_same_document_resize',
                             'path': capture['path'], 'sha256': capture['sha256'],
                             'size': [capture['width'], capture['height']]})
            seams.append({'label': phase['label'], 'same': same,
                          'request_values_unchanged': seam['request_values_unchanged'],
                          'same_request_required': seam['same_request_required'],
                          'capture_layout_unchanged': True})
    assert len(rows) == 24 and len(captures) == 26 and len(seams) == 2
    same_font = [{'label': entry['label'], 'native': entry['native'],
                  'explicit_configure_while_workspace_closed':
                      entry['explicit_configure_while_workspace_closed']}
                 for entry in scene['same_font_real_SDK']]
    assert len(same_font) == 3
    assert [entry['native']['cached_gui'] for entry in same_font] == [4., 3., 2.]
    assert [entry['native']['font'] for entry in same_font] == [5.] * 3
    guard = data['continuous-handle-guard-v1.json']
    resources = scene['resources']
    report = {
        'schema': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Post-run native SDK geometry/cache and capture-byte accounting; no fitted pixel or temporal gate',
        'input_sha256': {name: sha(ATTEMPT / name) for name in names},
        'source_contract_sha256': source['source_contract_sha256'],
        'source_entries_verified': len(source_entries), 'source_unchanged': True,
        'source_is_complete_transitive_closure': False,
        'rows': rows, 'same_font_real_SDK': same_font, 'same_document_resize': seams,
        'captures': captures, 'captures_verified': len(captures),
        'native_samples_verified': sum(row['native_samples'] for row in rows),
        'scene_resource_samples': len(resources),
        'scene_minimum_available_commit_bytes': min(value['available_commit_bytes'] for value in resources),
        'scene_maximum_handles': {kind: max(value['processes'][kind]['handles'] for value in resources)
                                  for kind in ('game', 'mcdk')},
        'scene_maximum_adjacent_growth': {
            kind: max(value['processes'][kind].get('growth') or 0 for value in resources)
            for kind in ('game', 'mcdk')},
        'continuous_guard_samples': len(guard['samples']),
        'continuous_guard_breach': guard.get('guard_breach'),
        'continuous_modal_guard_breach': guard.get('modal_guard_breach'),
        'restored': True, 'exact_identities_absent': group['exact_identities_absent'],
        'same_handle_exit': data['launch/exact-exit.json'],
        'helper_retirement': data['helper-retirement-v1.json'],
        'elapsed_seconds': group['elapsed_seconds'],
        'formal_A_accepted': False, 'default_path_evidence': False,
        'production_admission_performed': False, 'manual_closures_added': 0,
        'original_reports_modified': False,
    }
    assert not guard.get('guard_breach') and not guard.get('modal_guard_breach')
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(OUT), 'sha256': sha(OUT),
                      'captures_verified': 26, 'native_samples_verified': 72,
                      'source_entries_verified': len(source_entries),
                      'minimum_available_commit_bytes': report['scene_minimum_available_commit_bytes'],
                      'scene_maximum_handles': report['scene_maximum_handles'],
                      'scene_maximum_adjacent_growth': report['scene_maximum_adjacent_growth']}))


if __name__ == '__main__':
    main()

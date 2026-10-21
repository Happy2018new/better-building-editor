"""Small independent readback/restore/exit boundary audit; no runtime calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
BASE = ROOT / '.runtime/round-20261021'
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


water = BASE / 'water-final41-r25-v6'
water_index_path = ROOT / 'docs/evidence/water-final41-editor-r26-v1/index.json'
water_index = read(water_index_path)
group = read(water / 'group-execution-v1.json')
bootstrap = read(water / 'candidate-bootstrap-execution-v1.json')
restored = read(water / 'independent-restore-v1.json')
retired = read(water / 'bootstrap-marker-retired-v1.json')
f = read(water / 'product-v2-f-editor-v1.json')
f_host = read(water / 'product-v2-f-editor-v1-host.json')
assert group['completed'] and all(row.get('exit_code') == 0 for row in group['steps'])
assert not group['production_admission_performed'] and not group['default_path_evidence']
assert bootstrap['completed'] and bootstrap['runtime_readback']['original_function_identity_now']
assert restored['passed'] and restored['source_unchanged']
assert not restored['client']['markers'] and not restored['world']['markers']
assert not any(restored['client'][key] for key in ('projection_active', 'busy', 'edit_job', 'io_job', 'world_actors', 'preparing_entity'))
assert retired['marker_retired'] and retired['original_function_identity_now']
assert f['completed'] and f['restored'] and f['source_unchanged'] and not f['cleanup_errors']
assert len(f['rows']) == 14 and f_host['finished_rows'] == 13 and f_host['captured'] == 30
assert f['cases'] == ['source', 'flow_east', 'wet_oak_fence', 'neighbor_stone', 'transparent_overlap']
acceptance = {key: f[key] for key in ('native_shape_accepted', 'native_uv_accepted', 'native_alpha_accepted', 'product_style_accepted')}
assert not any(acceptance.values())
assert group['ordinary_stop']['exit_code'] == 1
assert all(group['exact_identities_absent_after_stop'].values())
assert group['registry_finalize']['exit_code'] == 0
assert json.loads(group['registry_finalize']['stdout'])['state'] == 'stopped'
water_exit = read(water / 'launch/exact-exit.json')
assert water_exit['completed'] and not water_exit['process_or_window_mutation']
assert water_exit['processes']['game']['exit_code'] == 0xC0000409
assert water_exit['processes']['mcdk']['exit_code'] == 0
watch = read(water / 'assert-watch/status.json')
assert not watch['known_assert_recoveries'] and not watch['other_assertions'] and not watch['errors']
helpers = read(water / 'helper-retirement-v1.json')
assert helpers['all_owned_helper_identities_absent'] and not helpers['game_or_mcdk_force_used']

t02 = BASE / 't02-face-missing-cold-v1'
t02_index_path = ROOT / 'docs/evidence/t02-face-missing-r26-v1/index.json'
t02_summary = read(ROOT / 'docs/evidence/t02-face-missing-r26-v1/summary.json')
report = read(t02 / 'check/report.json')
diag = read(t02 / 'button0-diag/report.json')
assert report['completed'] and report['restored'] and report['source_unchanged']
assert report['manual_issues_closed'] == 0 and not report['manual_acceptance']
assert not report['world_write_performed'] and not report['native_world_occupancy']
assert len(report['editor_faces']) == 10 and len(report['operations']) == 2
assert all(row.get('missing_completed') and row.get('observer_restored') for row in report['operations'])
assert diag['completed'] and diag['restored']
audits = {}
for name in ('face-restore-after1.json', 'face-restore-after2.json',
             'button0-final-restore-after1.json', 'button0-final-restore-after2.json'):
    audit = read(t02 / name)
    assert audit['completed'] and audit['source_unchanged'] and not audit['changed_keys']
    assert max(abs(value) for value in audit['camera_rotation_delta']) <= .0001
    audits[name] = {'sha256': digest(t02 / name),
                   'camera_rotation_exact': audit['camera_rotation_exact'],
                   'camera_rotation_delta': audit['camera_rotation_delta'],
                   'volatile_performance_fields': audit['performance_observed']['volatile_fields']}
stop = read(t02 / 'stop/report.json')
assert stop['completed'] and not stop['force_executed']
assert stop['registry_final']['state'] == 'stopped' and not stop['normal_shutdown_qualified']
t02_exit = read(t02 / 'launch/exact-exit.json')
assert t02_exit['completed'] and not t02_exit['process_or_window_mutation']
assert t02_exit['processes']['game']['exit_code'] == 0xC0000409
assert t02_exit['processes']['mcdk']['exit_code'] == 0
closed = read(t02 / 'assert-watch-close.json')
assert closed['completed'] and not closed['game_process_touched']
assert closed['actual_creation_identity'] == closed['expected_creation_identity']
assert t02_summary['visual_review']['process_completion_is_not_pixel_acceptance']

observations = [
    {'pack': 'water-final41-editor-r26-v1',
     'raw_images_opened': ['product-v2-g-v1_editor_gallery_dry.png', 'product-v2-g-v1_editor_gallery_wet.png',
                           'product-v2-f-editor-v1_editor_source_wet.png', 'product-v2-f-editor-v1_editor_source_dry.png'],
     'observation': 'G dry/wet have visible blue-water differences, but gallery subjects are small at 90%. F source wet clearly shows a translucent blue water volume above the stone support, while dry shows the support alone.',
     'limit': 'A four-image spot check does not accept native shape, UV, alpha, motion, every F case, or world projection. Those flags remain false.'},
    {'pack': 't02-face-missing-r26-v1',
     'raw_images_opened': ['check/t02_ladder_2_editor.png', 'check/t02_button_0_editor.png',
                           'button0-diag/t02_button_0_single_pitch80_editor.png', 'button0-diag/t02_button_0_single_pitch45_editor.png',
                           'check/t02_rotate_y90_missing_empty.png', 'check/t02_rotate_y90_missing_occupied.png',
                           'check/t02_rotate_y90_missing_restored.png'],
     'observation': 'Ladder face is visible in the editor spot check. Bottom button geometry and thickness are visible in the single-layer diagnostic. The rotated ladder is visible, disappears under controlled occupied, then returns; the stone backing remains visible.',
     'limit': 'The full-scene bottom-button image mainly shows the stone support and does not establish its unobscured attachment. Single-layer visibility establishes geometry existence only. Controlled occupancy does not establish native world blocks, all directions, or full missing matrices.'}
]
result = {'schema_version': 1, 'reviewer': '/root/integration_resume',
          'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'blocking_findings': [],
          'package_indexes': {'water-final41-editor-r26-v1': digest(water_index_path),
                              't02-face-missing-r26-v1': digest(t02_index_path)},
          'water': {'candidate_bootstrap_and_restore_observed': True,
                    'f_report_rows': len(f['rows']), 'f_host_transition_counter': f_host['finished_rows'],
                    'f_capture_count': f_host['captured'], 'acceptance_flags': acceptance,
                    'first_ordinary_stop_exit_code': group['ordinary_stop']['exit_code'],
                    'game_exit_hex': '0xC0000409', 'mcdk_exit_code': 0,
                    'registry_stopped': True, 'normal_shutdown_claimed': False,
                    'assertion_recoveries_observed': 0,
                    'idle_helper_retirement_includes_exact_python_watcher_termination': True,
                    'game_mcdk_forced': False},
          't02': {'ten_captures_two_operations_completed': True, 'restore_audits': audits,
                  'restoration_is_exact_for_strict_fields_and_tolerant_for_native_camera_rotation': True,
                  'native_camera_rotation_tolerance': .0001,
                  'previewWall_is_volatile_not_restore_equality': True,
                  'game_exit_hex': '0xC0000409', 'mcdk_exit_code': 0,
                  'registry_stopped': True, 'normal_shutdown_claimed': False,
                  'watcher_exact_identity_retired': True, 'force_executed': False},
          'independent_visual_spot_checks': observations,
          'manual_issues_closed': 0, 'manual_acceptance': False,
          'limits': ['No new MC, RPC, source changes or full-source scan in this review.',
                     'Restore/exit receipts establish the scoped observed states; abnormal game exit is retained and not qualified as a normal shutdown.',
                     'Watcher had no recovery events in these runs, so the fixed helper still has no live-trigger recovery proof from these instances.'],
          'passed': True}
(HERE / 'semantic-visual-review.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps(result, indent=2))

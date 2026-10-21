"""Compact T02 cold review inputs and observed images, retaining exact raw hashes."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image
from frozen_guard import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'docs/evidence/t02-normal-cold-r25-v1'
manifest = verify()
assert not OUT.exists()
OUT.mkdir(parents=True)
(OUT / 'records').mkdir()
(OUT / 'images').mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
records = ['source-manifest.json', 'derivation.json', 'preflight-resume-v2.json',
           'check-resume-v2-receipt.json', 'watch-resume-v2-derivation.json',
           'assert-watch-start.json', 'assert-watch-close.json', 'assert-watch/status.json',
           'launch/report.json', 'launch/exact-exit.json', 'check/report.json', 'stop/report.json',
           'prepare.py', 'freeze.py', 'frozen_guard.py', 'launch_owned.py', 'stop_owned.py',
           'start_watch.py', 'start_watch_resume_v2.py', 'close_final_watch.py',
           'check_t02.py', 'check_t02_resume_v2.py', 'payloads.py', 'public_entry_host.py',
           'run_transform_final.py', 'lifecycle_helpers.py', 'compact.py']
index = {'source_commit': manifest['source_commit'], 'owner': manifest['owner'],
         'created_at': datetime.now(timezone.utc).isoformat(), 'manual_issues_closed': 0,
         'records': [], 'images': []}
for relative in records:
    source = HERE / relative
    assert source.is_file(), relative
    data = source.read_bytes()
    target = OUT / 'records' / relative.replace('/', '__')
    row = {'raw': source.relative_to(ROOT).as_posix(), 'sha256': sha(source), 'bytes': len(data)}
    if source.suffix == '.json' and len(data) > 100000:
        packed = gzip.compress(data, compresslevel=9, mtime=0)
        assert gzip.decompress(packed) == data
        target = target.with_suffix('.json.gz')
        target.write_bytes(packed)
        row.update(encoding='gzip', archive_sha256=sha(target), archive_bytes=len(packed))
    else:
        shutil.copyfile(source, target)
    row['archived'] = target.relative_to(OUT).as_posix()
    index['records'].append(row)
names = ['t02_initial_editor_closeup', 't02_mirror_y_editor_closeup', 't02_mirror_y_world_closeup',
         't02_rotate_y90_editor_closeup', 't02_rotate_y90_world_closeup']
for name in names:
    source = HERE / 'check' / (name + '.png')
    target = OUT / 'images' / (name + '.jpg')
    with Image.open(source) as image:
        image = image.convert('RGB')
        image.thumbnail((1600, 1000))
        image.save(target, 'JPEG', quality=82, optimize=True)
    index['images'].append({'label': name, 'raw': source.relative_to(ROOT).as_posix(),
                            'raw_sha256': sha(source), 'review_jpeg': target.relative_to(OUT).as_posix(),
                            'review_sha256': sha(target), 'bytes': target.stat().st_size,
                            'agent_opened_raw_image': True, 'human_acceptance': False})
check = json.loads((HERE / 'check/report.json').read_bytes())
stop = json.loads((HERE / 'stop/report.json').read_bytes())
summary = {'source_commit': manifest['source_commit'], 'owner': manifest['owner'],
 'source_manifest_sha256': sha(HERE / 'source-manifest.json'), 'source_unchanged': verify() == manifest,
 'completed': check['completed'], 'restored': check['restored'], 'manual_issues_closed': 0,
 'manual_acceptance': False, 'world_write_performed': False, 'candidate_profile_assignment': False,
 'actual_public_card_callbacks': True, 'native_mouse_clicked': False,
 'fixture_cells': check['fixture_cells'], 'direction_samples': check['direction_samples'],
 'fixture_material_counts': check['fixture_material_counts'],
 'operations': [{'operation': row['operation'], 'data_equal': row['data']['equal'],
                 'semantic_equal': row['data']['document_semantic_equal'], 'encoded_equal': row['data']['encoded_equal']}
                for row in check['operations']],
 'independent_restore_audit_count': len(check['independent_restore_audits']),
 'native_camera_exact_in_both_audits': all(row['native_camera_exact'] for row in check['independent_restore_audits']),
 'restore_camera_rotation_deltas': [row['camera_rotation_delta'] for row in check['independent_restore_audits']],
 'semantic_camera_restored_in_both_audits': all(row['semantic_camera_pose_restored'] for row in check['independent_restore_audits']),
 'camera_restore_tolerance_degrees': .0001,
 'camera_restore_note': 'Semantic rotation restoration is within 0.0001 degrees; exact floating point equality is reported separately and is not assumed.',
 'agent_visual_observation': 'Initial and transformed editor overviews plus mirror-Y and rotate-Y90 full projections all contain the expected scene. Stairs/slabs and attachment layout move consistently with the transform. Some ladders face edge-on and buttons are too small or occluded for complete per-face pixel acceptance in these overview cameras.',
 'remaining_visual_scope': 'All 28 samples need user inspection or targeted face closeups for complete visual acceptance; mirror-X/mirror-Z and missing were not tested in this bounded cold session.',
 'missing_checked': False,
 'preflight_failures_preserved': ['Counting all non-stone cells included four colored markers (32 versus 28).',
                                  'Undo/redo are Editor methods via Session.action, not named Editor.run tools.'],
 'runtime_host_corrections_only': ['Explicit five-family sample census', 'Undo/redo through existing action API',
                                   'Strict active-owner coverage with verified empty non-owner PreviewTile classification'],
 'lifecycle': {'game_pid': 63648, 'game_identity': '134370328107798494',
               'ordinary_stop_and_finalize_completed': stop['completed'], 'registry_state': stop['registry_final']['state'],
               'actual_exit_codes': stop['actual_exit_codes'], 'normal_shutdown_qualified': stop['normal_shutdown_qualified'],
               'force_executed': stop['force_executed'],
               'watcher_retired': json.loads((HERE / 'assert-watch-close.json').read_bytes())['completed']}}
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
index['summary_sha256'] = sha(OUT / 'summary.json')
(OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({'output': str(OUT), 'images': len(index['images']), 'records': len(index['records']),
                  'total_bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                  'index_sha256': sha(OUT / 'index.json')}))

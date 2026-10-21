"""Archive compact review copies while retaining every raw input hash and failure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image
from frozen_guard import verify

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'docs/evidence/final-kelp-chest-r25-v1'
assert not OUT.exists()
manifest = verify()
OUT.mkdir(parents=True)
(OUT / 'records').mkdir()
(OUT / 'images').mkdir()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
records = ['source-manifest.json', 'assert-watch-start.json', 'assert-watch-close.json',
 'assert-watch/status.json', 'launch/report.json', 'launch/exact-exit.json',
 'kelp/report.json', 'kelp-resume-v2/report.json', 'kelp-resume-v3/report.json', 'kelp-resume-v4/report.json',
 'kelp-resume-v2-receipt.json', 'kelp-resume-v3-receipt.json', 'kelp-resume-v4-receipt.json',
 't04-cold-resume-v2.json', 't04-resume-v2-receipt.json', 't04-restore-before.json',
 't04-restore-after1.json', 't04-restore-v2-after1.json', 't04-restore-v2-after2.json', 'stop/report.json',
 'start_watch_resume.py', 'check_kelp_resume_v2.py', 'check_kelp_resume_v3.py', 'check_kelp_resume_v4.py',
 'run_context_resume_v2.py', 'audit_t04_resume.py', 'audit_t04_resume_v2.py', 'compact_resume.py']
index = {'source_commit': manifest['source_commit'], 'created_at': datetime.now(timezone.utc).isoformat(),
         'manual_issues_closed': 0, 'records': [], 'images': []}
for relative in records:
    source = HERE / relative
    assert source.is_file(), relative
    target = OUT / 'records' / relative.replace('/', '__')
    shutil.copyfile(source, target)
    index['records'].append({'raw': source.relative_to(ROOT).as_posix(), 'archived': target.relative_to(OUT).as_posix(),
                             'sha256': sha(source), 'bytes': source.stat().st_size})
images = [('kelp_' + name, HERE / 'kelp-resume-v4' / (name + '.png')) for name in
          ('editor_low', 'editor_cross16', 'missing_low', 'missing_cross16')]
images += [('t04_' + name, HERE / ('t04-cold-resume-v2_t04_' + name + '_native.png')) for name in
           ('before_editor_closeup', 'after_editor_closeup', 'production_world_closeup',
            'missing_empty', 'missing_single_half', 'missing_occupied', 'missing_restored')]
for label, source in images:
    target = OUT / 'images' / (label + '.jpg')
    with Image.open(source) as image:
        raw_size = image.size
        image = image.convert('RGB')
        image.thumbnail((1600, 1000))
        image.save(target, 'JPEG', quality=82, optimize=True)
    index['images'].append({'label': label, 'raw': source.relative_to(ROOT).as_posix(), 'raw_sha256': sha(source),
        'raw_size': raw_size, 'review_jpeg': target.relative_to(OUT).as_posix(), 'review_sha256': sha(target),
        'bytes': target.stat().st_size, 'agent_opened_raw_image': True, 'human_acceptance': False})
kelp = json.loads((HERE / 'kelp-resume-v4/report.json').read_bytes())
t04 = json.loads((HERE / 't04-cold-resume-v2.json').read_bytes())
stop = json.loads((HERE / 'stop/report.json').read_bytes())
summary = {'source_commit': manifest['source_commit'], 'source_manifest_sha256': sha(HERE / 'source-manifest.json'),
 'source_unchanged': verify() == manifest, 'manual_issues_closed': 0, 'manual_acceptance': False,
 'candidate_profile_assignment': False, 'world_write_performed': False,
 'kelp': {'completed': kelp['completed'], 'restored': kelp['restored'], 'source_unchanged': kelp['source_unchanged'],
          'public_card_callbacks': True, 'native_mouse_clicked': False, 'formal_material_names': kelp['formal_material_names'],
          'agent_visual_observation': 'Editor low/isolated and cross16 plants, plus both matching missing projection views, are visible and show stem/top continuity. This is bounded agent evidence for the public fixture, not human closure.',
          'first_fail_preserved': 'kelp/report.json', 'v2_host_error_preserved': 'kelp-resume-v2/report.json',
          'v3_blank_closeups_preserved': 'kelp-resume-v3/report.json',
          'host_corrections': ['Exclude only verified empty non-region-owner PreviewTile slots; all active owners remain strict.',
                               'Use exactly data[0:3] for palette counts.',
                               'Focus the mounted camera through camera_focus_request before zoom.']},
 't04': {'completed': t04['completed'], 'restored': t04['restored'], 'source_unchanged': t04['source_unchanged'],
         'native_world_occupancy': False, 'runtime_context_patch': False,
         'stages': [row['final']['observations'] for row in t04['missing']['stages']],
         'agent_visual_observation': 'Mirror before/after, full projection and four observed missing stages are visually consistent. Occupied red support is clean, single-half removes only the occupied half, blue pair remains, and restored returns both pairs without flat chest wood on supports.',
         'input_normalization_note': 'Original preflight saw current-host LF versus archive CRLF rail bytes. v2 binds exact frozen manifest bytes, retaining raw comparisons and CRLF-to-LF equality without changing frozen inputs.',
         'independent_restore_audits': ['t04-restore-v2-after1.json', 't04-restore-v2-after2.json'],
         'initial_audit_fail_preserved': 't04-restore-after1.json',
         'restore_metric_note': 'previewWall changes when restored preview rebuild finishes; all other performance fields, document/editor/session identity, restored settings, profiles and native camera remain strict.'},
 'lifecycle': {'owner': manifest['owner'], 'game_pid': 62820, 'game_creation_identity': '134370206332889401',
               'ordinary_stop_and_registry_finalize': stop['completed'], 'registry_state': stop['registry_final']['state'],
               'actual_exit_codes': stop['actual_exit_codes'], 'game_exit_hex': '0xC0000409',
               'normal_shutdown_qualified': stop['normal_shutdown_qualified'], 'force_executed': stop['force_executed'],
               'assert_watcher_retired': json.loads((HERE / 'assert-watch-close.json').read_bytes())['completed']}}
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
index['summary_sha256'] = sha(OUT / 'summary.json')
(OUT / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps({'output': str(OUT), 'records': len(index['records']), 'images': len(index['images']),
                  'total_bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
                  'index_sha256': sha(OUT / 'index.json'), 'source_unchanged': summary['source_unchanged']}))

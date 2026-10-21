"""Prepare one distinct normal-source T02 cold runtime; never launch or inject fixtures."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / 'final-kelp-chest-cold-v1'
OWNER = 'r25-t02-normal-v1'
PROJECT = ROOT / '.runtime/projects' / OWNER
derivation = {}
for name in ('freeze.py', 'frozen_guard.py', 'launch_owned.py', 'stop_owned.py',
             'close_final_watch.py', 'lifecycle_helpers.py', 'public_entry_host.py',
             'run_transform_final.py', 'audit_t04_resume_v2.py'):
    original = OLD / name
    source = original.read_text(encoding='utf8')
    source = source.replace('r25-final-kelp-chest-v1', OWNER).replace('final-kelp-chest-cold-v1', 't02-normal-cold-v1')
    source = source.replace('t04-restore-', 't02-restore-').replace('_kelp_final_r25', '_t02_normal_r25')
    if name == 'public_entry_host.py':
        source = source.replace("get('identity') == 'registry'", "get('identity') == 'transforms'")
    target = HERE / name
    assert not target.exists()
    ast.parse(source)
    target.write_text(source, encoding='utf8')
    derivation[name] = {'original': original.relative_to(ROOT).as_posix(),
                        'original_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                        'new_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
source = (OLD / 'start_watch_resume.py').read_text(encoding='utf8').replace('r25-final-kelp-chest-v1', OWNER)
target = HERE / 'start_watch.py'
assert not target.exists()
target.write_text(source, encoding='utf8')
source = (OLD / 'payloads.py').read_text(encoding='utf8').replace('_kelp_final_r25', '_t02_normal_r25')
target = HERE / 'payloads.py'
assert not target.exists()
target.write_text(source, encoding='utf8')
(HERE / 'derivation.json').write_text(json.dumps({'owner': OWNER, 'project': str(PROJECT),
 'sources': derivation, 'production_changes': False, 'candidate_assignment': False,
 'no_game_started': True, 'cold_commit': '900100aa402f7442b1f1cf6cf1554f1f3d76fd14'}, indent=2) + '\n', encoding='utf8')
print('T02 lifecycle/entry/focus/oracle hosts prepared without game start')

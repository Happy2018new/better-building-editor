"""Independently apply and archive the private, unqualified Scene combination."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / '.runtime/round-20261023'
SOURCE = RUN / 'scene-portal-combination-v1'
REPLAY = RUN / 'root-combined-replay-v1'
OUT = ROOT / 'docs/evidence/scene-portal-combination-r28-v1'
PREFIX = Path('behavior_pack/modern_projection/projection')
COMMIT = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def blob(path):
    return subprocess.check_output(['git', 'cat-file', 'blob', COMMIT + ':' + path.as_posix()], cwd=str(ROOT))


def unique(tree, name):
    values = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(values) == 1, name
    return values[0]


index = read(SOURCE / 'index.json')
assert digest((SOURCE / 'index.json').read_bytes()) == '7ed96ce3492b5dc300d0b474d40e18d69e42f7f5c04da6c4d400712ca2782086'
assert not REPLAY.exists() and not OUT.exists()
OUT.mkdir()
for row in index['entries']:
    path = (SOURCE / row['path']).resolve()
    assert path.is_relative_to(SOURCE.resolve())
    data = path.read_bytes()
    assert digest(data) == row['sha256'] and len(data) == row['bytes']
    target = OUT / row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
shutil.copyfile(SOURCE / 'index.json', OUT / 'index.json')
for name in ('scene.py', 'portal_profile.py'):
    data = blob(PREFIX / name)
    assert data == (SOURCE / 'baseline' / PREFIX / name).read_bytes()
    target = REPLAY / PREFIX / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
invocations = []
for check in (True, False):
    args = ['git', 'apply'] + (['--check'] if check else []) + [
        '--directory=' + REPLAY.relative_to(ROOT).as_posix(), str(SOURCE / 'combined.patch')]
    result = subprocess.run(args, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    invocations.append({'args': args, 'returncode': result.returncode,
                        'stdout': result.stdout.decode('utf8'), 'stderr': result.stderr.decode('utf8')})
    assert result.returncode == 0, result.stderr
actual = {}
for name in ('scene.py', 'portal_profile.py', 'scene_owner.py'):
    data = (REPLAY / PREFIX / name).read_bytes()
    assert data == (SOURCE / 'combined' / PREFIX / name).read_bytes(), name
    actual[name] = {'bytes': len(data), 'sha256': digest(data)}
old = ast.parse(blob(PREFIX / 'scene.py'))
new = ast.parse((REPLAY / PREFIX / 'scene.py').read_bytes())
owner_only = ast.parse((RUN / 'scene-owner-minimal-v2/scene.candidate.py').read_bytes())
portal_only = ast.parse((RUN / 'portal-anchor-candidate-v1/candidate' / PREFIX / 'scene.py').read_bytes())
restored = copy.deepcopy(new)
for name in ('own_liquid', 'own_items', 'own_cauldrons', 'own_portals', 'own_books', 'portal_view'):
    reference = portal_only if name == 'portal_view' else owner_only
    assert ast.dump(unique(new, name)) == ast.dump(unique(reference, name)), name
    unique(restored, name).body = copy.deepcopy(unique(old, name).body)
restored.body = [node for node in restored.body if not (
    isinstance(node, ast.ImportFrom) and node.module == 'scene_owner' and node.level == 1)]
assert ast.dump(restored) == ast.dump(old)
controls = []
for family in ('owner', 'portal'):
    paired = [read(RUN / ('combined-root-%s-py%d-v1.json' % (family, major))) for major in (2, 3)]
    if family == 'owner':
        assert paired[0]['cases'] == paired[1]['cases'] and len(paired[0]['cases']) == 58
        assert all(row['completed'] for row in paired)
    else:
        for key in ('formula_rows', 'dispatch_rows', 'invalid_GUI_rejected', 'historical_V4_formula_rows'):
            assert paired[0][key] == paired[1][key]
        assert all(row['passed'] for row in paired)
    for major in (2, 3):
        name = 'combined-root-%s-py%d-v1.json' % (family, major)
        shutil.copyfile(RUN / name, OUT / name)
        controls.append(name)
receipt = {
    'completed': True, 'base_commit': COMMIT,
    'root_actual_check_apply': invocations, 'three_replayed_files_exact_agent_combination': actual,
    'whole_Scene_AST_identical_except_six_authorized_bodies_and_import': True,
    'new_root_real_Py2_Py3_controls': controls,
    'runtime_written': False, 'MC_started': False, 'water_qualification_transferred': False,
    'manual_issues_closed': 0,
}
shutil.copyfile(__file__, OUT / 'review_combination_root_v1.py')
(OUT / 'root-review.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf8')
entries = []
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        data = path.read_bytes()
        entries.append({'path': path.relative_to(OUT).as_posix(), 'bytes': len(data), 'sha256': digest(data)})
(OUT / 'root-index.json').write_text(json.dumps({'entries': entries, 'merged': False}, indent=2, sort_keys=True) + '\n', encoding='utf8')
print(json.dumps({'completed': True, 'exact_replayed_files': len(actual), 'archive_files': len(entries) + 1,
                  'archive_bytes_without_root_index': sum(row['bytes'] for row in entries)}))

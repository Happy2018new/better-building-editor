"""Root review and exact-byte archive of the two unmerged R28 candidates."""
import ast
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / '.runtime/round-20261023'
OUT = ROOT / 'docs/evidence/next-cycle-candidates-r28-v1'
COMMIT = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
PREFIX = 'behavior_pack/modern_projection/projection/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(path):
    return subprocess.check_output(['git', 'cat-file', 'blob', COMMIT + ':' + path], cwd=str(ROOT))


def read(path):
    return json.loads(path.read_bytes())


def stable(path):
    return {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def write(path, data):
    assert not path.exists(), str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf8')


def safe_file(base, relative):
    path = (base / relative).resolve()
    assert path.is_relative_to(base.resolve()) and path.is_file(), relative
    return path


assert not OUT.exists()
portal = RUN / 'portal-anchor-candidate-v1'
scene = RUN / 'scene-owner-minimal-v2'
portal_index = portal / 'index.json'
scene_index = scene / 'ready-index.json'
assert sha(portal_index.read_bytes()) == '4dbe14c85741f389e168ecdb47ca9950003710243e50eb7b1596ddf803695009'
assert sha(scene_index.read_bytes()) == 'dab6301625661123426e8e42b2369b623f3cf537694b904bd61ba6ad79fa89c9'
checked = {}
for name, base, index, rows in (
    ('portal', portal, portal_index, [(row['path'], row) for row in read(portal_index)['entries']]),
    ('scene', scene, scene_index, list(read(scene_index)['files'].items())),
):
    checked[name] = []
    for relative, expected in rows:
        source = safe_file(base, relative)
        actual = stable(source)
        assert actual == {key: expected[key] for key in ('bytes', 'sha256')}, relative
        target = OUT / name / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert target.read_bytes() == source.read_bytes()
        checked[name].append({'path': relative, **actual})
    shutil.copyfile(index, OUT / name / index.name)

# Independently fetch Git blobs, rather than trusting the candidate provenance.
baseline = {}
for name in ('scene.py', 'portal_profile.py', 'cell.py'):
    data = blob(PREFIX + name)
    assert (ROOT / PREFIX / name).read_bytes() == data, name
    baseline[name] = {'bytes': len(data), 'sha256': sha(data)}
    if name in ('scene.py', 'portal_profile.py'):
        assert (portal / 'baseline' / PREFIX / name).read_bytes() == data
assert (scene / 'scene.original.py').read_bytes() == blob(PREFIX + 'scene.py')
assert (portal / 'support/cell.py').read_bytes() == blob(PREFIX + 'cell.py')

# Independently inspect the actual candidate helper, not a copied behavioral model.
helper = ast.parse((scene / 'scene_owner.py').read_bytes())
functions = [node for node in helper.body if isinstance(node, ast.FunctionDef)]
assert [node.name for node in functions] == ['own_preview']
assert not any(isinstance(node, (ast.Try, ast.While, ast.For, ast.AsyncFor, ast.With)) for node in ast.walk(helper))
cleanup = next(node for node in functions[0].body if isinstance(node, ast.FunctionDef))
assert [node.value.func.value.id for node in cleanup.body[:2]] == ['controls', 'preview']
assert all(isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and node.value.func.attr == 'close'
           for node in cleanup.body[:2])
assert isinstance(cleanup.body[-1], ast.If)
assert isinstance(cleanup.body[-1].test.ops[0], ast.Is)

control_receipts = {}
for family in ('portal', 'scene'):
    paired = [read(RUN / ('%s-root-controls-py%d-v1.json' % (family, major))) for major in (2, 3)]
    assert paired[0]['python'] == [2, 7, 13] and paired[1]['python'] == [3, 13, 13]
    if family == 'scene':
        assert paired[0]['completed'] and paired[1]['completed']
        assert paired[0]['cases'] == paired[1]['cases'] and len(paired[0]['cases']) == 58
    else:
        for key, count in [('formula_rows', 8), ('dispatch_rows', 9), ('historical_V4_formula_rows', 21), ('invalid_GUI_rejected', 12)]:
            assert paired[0][key] == paired[1][key] and len(paired[0][key]) == count
        assert all(row['passed'] for row in paired)
    control_receipts[family] = []
    for major in (2, 3):
        relative = '%s-root-controls-py%d-v1.json' % (family, major)
        shutil.copyfile(RUN / relative, OUT / relative)
        control_receipts[family].append({'path': relative, **stable(OUT / relative)})

receipt = {
    'source_commit': COMMIT, 'candidate_source_indexes_checked': True,
    'checked_candidate_files': checked, 'actual_Git_baseline_bytes': baseline,
    'root_actual_Py2_Py3_replays': control_receipts,
    'actual_helper_close_order_and_identity_AST_independently_checked': True,
    'product_written': False, 'merged': False, 'native_called': False,
    'water_qualification_transferred': False, 'manual_issues_closed': 0,
    'scope': 'Private source candidates and offline controls only; original scripts retain their runtime-path assumptions.',
}
shutil.copyfile(__file__, OUT / 'review_candidates_root_v1.py')
write(OUT / 'root-review.json', receipt)
write(OUT / 'index.json', {
    'source_commit': COMMIT, 'merged': False, 'manual_issues_closed': 0,
    'entries': [dict(path=path.relative_to(OUT).as_posix(), **stable(path))
                for path in sorted(OUT.rglob('*')) if path.is_file()],
})
print(json.dumps({'completed': True, 'portal_files': len(checked['portal']), 'scene_files': len(checked['scene']),
                  'archive_files': len(read(OUT / 'index.json')['entries']) + 1, 'product_written': False,
                  'index_sha256': sha((OUT / 'index.json').read_bytes())}))

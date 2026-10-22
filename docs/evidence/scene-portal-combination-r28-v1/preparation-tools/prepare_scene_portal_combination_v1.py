"""Private exact-b70 owner+portal patch application; never writes product files."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / 'scene-portal-combination-v1'
OWNER = HERE.parent / 'scene-owner-minimal-v2'
PORTAL = HERE.parent / 'portal-anchor-candidate-v1'
BASE = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
PREFIX = 'behavior_pack/modern_projection/projection/'
SCENE = PREFIX + 'scene.py'
PROFILE = PREFIX + 'portal_profile.py'
HELPER = PREFIX + 'scene_owner.py'
CELL = PREFIX + 'cell.py'
OWNERS = ('own_liquid', 'own_items', 'own_cauldrons', 'own_portals', 'own_books')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def write(base, relative, data):
    target = base / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


assert not HERE.exists(), 'Fresh private destination is required'
HERE.mkdir()
calls = []


def run(arguments, cwd):
    result = subprocess.run(arguments, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    row = {'argv': [str(arg) for arg in arguments], 'cwd': str(cwd),
           'returncode': result.returncode, 'stdout': result.stdout.decode('utf8', 'replace'),
           'stderr': result.stderr.decode('utf8', 'replace')}
    calls.append(row)
    record(HERE / 'git-application-invocations.json', calls)
    return result


production_before = {name: sha((ROOT / name).read_bytes()) for name in (SCENE, PROFILE)}
source_blobs = {}
for name in (SCENE, PROFILE, CELL):
    blob = run(['git', 'show', BASE + ':' + name], ROOT)
    assert blob.returncode == 0, name
    source_blobs[name] = blob.stdout
    if name in (SCENE, PROFILE):
        write(HERE / 'baseline', name, blob.stdout)
        write(HERE / 'combined', name, blob.stdout)
write(HERE, 'support/cell.py', source_blobs[CELL])
assert source_blobs[SCENE] == (OWNER / 'scene.original.py').read_bytes()
assert source_blobs[SCENE] == (PORTAL / 'baseline' / SCENE).read_bytes()
assert source_blobs[PROFILE] == (PORTAL / 'baseline' / PROFILE).read_bytes()
assert source_blobs[CELL] == (PORTAL / 'support/cell.py').read_bytes()
assert run(['git', 'init', '--quiet'], HERE / 'combined').returncode == 0

inputs = []
applied = True
for label, directory in [('five-owner', OWNER), ('portal-anchor', PORTAL)]:
    patch = directory / 'candidate.patch'
    content = patch.read_bytes()
    write(HERE, 'inputs/' + label + '.patch', content)
    row = {'label': label, 'source': str(patch), 'sha256': sha(content),
           'source_index': str(directory / ('ready-index.json' if label == 'five-owner' else 'index.json'))}
    row['source_index_sha256'] = sha(Path(row['source_index']).read_bytes())
    check = run(['git', 'apply', '--check', str(patch)], HERE / 'combined')
    row['check_returncode'] = check.returncode
    if check.returncode:
        applied = False
        inputs.append(row)
        break
    actual = run(['git', 'apply', str(patch)], HERE / 'combined')
    row['apply_returncode'] = actual.returncode
    inputs.append(row)
    if actual.returncode:
        applied = False
        break
    if label == 'five-owner':
        assert (HERE / 'combined' / SCENE).read_bytes() == (OWNER / 'scene.candidate.py').read_bytes()
        write(HERE, 'intermediate/scene.owner-only.py', (HERE / 'combined' / SCENE).read_bytes())

record(HERE / 'input-sources.json', {'git_base': BASE, 'application_order': inputs,
    'default_git_apply': True, 'relaxed_or_force_flags': False,
    'baseline_files': {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in source_blobs.items()}})
if not applied:
    record(HERE / 'feasibility.json', {'both_patches_applied': False, 'conflict_not_forced': True,
        'product_unchanged': production_before == {name: sha((ROOT / name).read_bytes()) for name in production_before},
        'MC_started': False, 'qualified': False})
    print(json.dumps({'both_patches_applied': False, 'directory': str(HERE)}))
    sys.exit(0)

for name in (SCENE, PROFILE, HELPER):
    compile((HERE / 'combined' / name).read_bytes(), name, 'exec')

def tree(data):
    return ast.parse(data)


def named_function(parsed, name):
    rows = [node for node in ast.walk(parsed) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(rows) == 1, (name, len(rows))
    return rows[0]


old = tree(source_blobs[SCENE])
combined = tree((HERE / 'combined' / SCENE).read_bytes())
owner_candidate = tree((OWNER / 'scene.candidate.py').read_bytes())
portal_candidate = tree((PORTAL / 'candidate' / SCENE).read_bytes())
restored = copy.deepcopy(combined)
for name in OWNERS:
    assert ast.dump(named_function(combined, name)) == ast.dump(named_function(owner_candidate, name))
    named_function(restored, name).body = copy.deepcopy(named_function(old, name).body)
assert ast.dump(named_function(combined, 'portal_view')) == ast.dump(named_function(portal_candidate, 'portal_view'))
named_function(restored, 'portal_view').body = copy.deepcopy(named_function(old, 'portal_view').body)
helper_imports = [node for node in restored.body if isinstance(node, ast.ImportFrom)
                  and node.module == 'scene_owner' and node.level == 1]
assert len(helper_imports) == 1
assert [(alias.name, alias.asname) for alias in helper_imports[0].names] == [('own_preview', None)]
restored.body.remove(helper_imports[0])
assert ast.dump(restored) == ast.dump(old), 'Combined Scene escaped approved AST regions'
assert (HERE / 'combined' / PROFILE).read_bytes() == (PORTAL / 'candidate' / PROFILE).read_bytes()
assert (HERE / 'combined' / HELPER).read_bytes() == (OWNER / 'scene_owner.py').read_bytes()

# Generate a new composition patch. Scene content keeps its exact original CRLF.
patch_text = ''
for name in (SCENE, PROFILE, HELPER):
    before = source_blobs.get(name, b'')
    after = (HERE / 'combined' / name).read_bytes()
    patch_text += ''.join(difflib.unified_diff(before.decode('utf8').splitlines(True),
        after.decode('utf8').splitlines(True), fromfile='a/' + name if before else '/dev/null',
        tofile='b/' + name, lineterm='\n'))
write(HERE, 'combined.patch', patch_text.encode('utf8'))
for name in (SCENE, PROFILE):
    write(HERE / 'replay', name, source_blobs[name])
assert run(['git', 'init', '--quiet'], HERE / 'replay').returncode == 0
assert run(['git', 'apply', '--check', str(HERE / 'combined.patch')], HERE / 'replay').returncode == 0
assert run(['git', 'apply', str(HERE / 'combined.patch')], HERE / 'replay').returncode == 0
for name in (SCENE, PROFILE, HELPER):
    assert (HERE / 'replay' / name).read_bytes() == (HERE / 'combined' / name).read_bytes()

record(HERE / 'ast-and-apply.json', {
    'both_patches_applied': True, 'composition_patch_replayed_byte_exactly': True,
    'actual_application_order': ['five-owner', 'portal-anchor'],
    'Scene_AST_identical_except': ['five original owner bodies', 'sole scene_owner own_preview import',
                                 'portal_view optional GUI-offset hook with legacy fallback'],
    'five_owner_AST_matches_sealed_candidate': True, 'portal_view_AST_matches_sealed_candidate': True,
    'portal_profile_bytes_match_sealed_candidate': True, 'helper_bytes_match_sealed_candidate': True,
    'source_files': {name: {'sha256': sha((HERE / 'combined' / name).read_bytes()),
                          'bytes': (HERE / 'combined' / name).stat().st_size} for name in (SCENE, PROFILE, HELPER)},
    'combined_patch_sha256': sha((HERE / 'combined.patch').read_bytes()),
    'product_before': production_before,
    'product_after': {name: sha((ROOT / name).read_bytes()) for name in production_before},
    'MC_started': False, 'source_qualification_transferred': False,
    'native_qualified': False, 'manual_closed': 0, 'main_repository_mutated': False})
assert production_before == {name: sha((ROOT / name).read_bytes()) for name in production_before}
print(json.dumps({'both_patches_applied': True, 'whole_Scene_AST_region_check': True,
                  'replay_byte_exact': True, 'directory': str(HERE)}))

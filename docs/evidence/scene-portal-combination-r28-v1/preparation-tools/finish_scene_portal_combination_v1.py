"""Continue an actual successful two-patch apply after an EOL-only raw assertion."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / 'scene-portal-combination-v1'
OWNER = HERE.parent / 'scene-owner-minimal-v2'
PORTAL = HERE.parent / 'portal-anchor-candidate-v1'
BASE = 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
PREFIX = 'behavior_pack/modern_projection/projection/'
SCENE = PREFIX + 'scene.py'
PROFILE = PREFIX + 'portal_profile.py'
HELPER = PREFIX + 'scene_owner.py'
OWNERS = ('own_liquid', 'own_items', 'own_cauldrons', 'own_portals', 'own_books')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def write(name, data):
    target = HERE / name
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), name
    target.write_bytes(data)


def normalized(data):
    return data.replace(b'\r\n', b'\n')


calls = json.loads((HERE / 'git-application-invocations.json').read_text(encoding='utf8'))


def run(args, cwd):
    result = subprocess.run(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    calls.append({'argv': [str(arg) for arg in args], 'cwd': str(cwd), 'returncode': result.returncode,
                  'stdout': result.stdout.decode('utf8', 'replace'), 'stderr': result.stderr.decode('utf8', 'replace')})
    record('git-application-invocations.json', calls)
    return result


source_blobs = {name: (HERE / 'baseline' / name).read_bytes() for name in (SCENE, PROFILE)}
product_before = {name: sha((ROOT / name).read_bytes()) for name in (SCENE, PROFILE)}
assert all(call['returncode'] == 0 for call in calls)
assert len([call for call in calls if call['argv'][1:3] == ['apply', '--check']]) == 2
assert len([call for call in calls if call['argv'][1] == 'apply' and '--check' not in call['argv']]) == 2
config = run(['git', 'config', '--show-origin', '--get', 'core.autocrlf'], HERE / 'combined')
assert config.returncode == 0


def named_function(tree, name):
    found = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(found) == 1
    return found[0]


old = ast.parse(source_blobs[SCENE])
combined = ast.parse((HERE / 'combined' / SCENE).read_bytes())
owner_candidate = ast.parse((OWNER / 'scene.candidate.py').read_bytes())
portal_candidate = ast.parse((PORTAL / 'candidate' / SCENE).read_bytes())
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
assert ast.dump(restored) == ast.dump(old)

eol_rows = []
for name, sealed in [(PROFILE, PORTAL / 'candidate' / PROFILE), (HELPER, OWNER / 'scene_owner.py')]:
    actual = (HERE / 'combined' / name).read_bytes()
    prior = sealed.read_bytes()
    assert normalized(actual) == normalized(prior)
    assert ast.dump(ast.parse(actual)) == ast.dump(ast.parse(prior))
    eol_rows.append({'path': name, 'sealed_path': str(sealed), 'sealed_sha256': sha(prior),
                     'actual_sha256': sha(actual), 'raw_byte_equal': actual == prior,
                     'LF_normalized_equal': True, 'AST_identical': True,
                     'sealed_CRLF_count': prior.count(b'\r\n'), 'actual_CRLF_count': actual.count(b'\r\n'),
                     'actual_bytes_retained': True})
record('eol-observation.json', {'actual_git_config_stdout': config.stdout.decode('utf8'), 'files': eol_rows,
    'patches_not_altered': True, 'no_force_or_relaxed_apply': True,
    'explanation': 'Default Git core.autocrlf=true converts newly written helper and portal profile to CRLF; actual output is retained.'})
record('preparation-history.json', {
    'initial_generator': str(HERE.parent / 'prepare_scene_portal_combination_v1.py'),
    'initial_generator_returncode': 1,
    'failed_assertion': 'Applied portal_profile raw bytes equal sealed portal candidate bytes',
    'failure_after_both_actual_git_apply_returned_zero': True,
    'reason': 'Actual default Git output has CRLF; sealed portal profile/helper use LF. Normalized bytes and complete AST match.',
    'correction': 'Retain actual bytes and explicitly audit EOL differences; no patch or source forced to match.',
    'continued_by': str(Path(__file__).resolve())})

patch_text = ''
for name in (SCENE, PROFILE, HELPER):
    before, after = source_blobs.get(name, b''), (HERE / 'combined' / name).read_bytes()
    if name != SCENE:
        before, after = normalized(before), normalized(after)
    patch_text += ''.join(difflib.unified_diff(before.decode('utf8').splitlines(True),
        after.decode('utf8').splitlines(True), fromfile='a/' + name if before else '/dev/null',
        tofile='b/' + name, lineterm='\n'))
write('combined.patch', patch_text.encode('utf8'))
for name in (SCENE, PROFILE):
    write('replay/' + name, source_blobs[name])
assert run(['git', 'init', '--quiet'], HERE / 'replay').returncode == 0
assert run(['git', 'apply', '--check', str(HERE / 'combined.patch')], HERE / 'replay').returncode == 0
assert run(['git', 'apply', str(HERE / 'combined.patch')], HERE / 'replay').returncode == 0
for name in (SCENE, PROFILE, HELPER):
    assert (HERE / 'replay' / name).read_bytes() == (HERE / 'combined' / name).read_bytes()
    compile((HERE / 'combined' / name).read_bytes(), name, 'exec')

# Create a fresh actual-owner driver, explicitly accepting only the separately
# audited portal callback region and resolving every candidate read to combined/.
driver = (OWNER / 'verify_actual_owner_controls.py').read_text(encoding='utf8')
adaptations = []


def change(source, old, new, label):
    assert source.count(old) == 1, label
    adaptations.append({'label': label, 'old': old, 'new': new})
    return source.replace(old, new, 1)


driver = change(driver, "def raw(name):\n    with open(os.path.join(HERE, name), 'rb') as source:",
    "SOURCE_PATHS = {'scene.original.py': 'baseline/" + SCENE + "',\n"
    "                'scene.candidate.py': 'combined/" + SCENE + "',\n"
    "                'scene_owner.py': 'combined/" + HELPER + "',\n"
    "                'scene.portal-only.py': 'inputs/scene.portal-only.py'}\n\n"
    "def raw(name):\n    with open(os.path.join(HERE, SOURCE_PATHS.get(name, name)), 'rb') as source:",
    'Resolve original and combined actual source files')
old_assert = "assert ast.dump(restored) == ast.dump(original_ast), 'Change escaped five owner bodies/helper import'"
new_assert = """def unique_function(tree, name):
    nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(nodes) == 1
    return nodes[0]
portal_only = parsed('scene.portal-only.py')
assert ast.dump(unique_function(candidate_ast, 'portal_view')) == ast.dump(unique_function(portal_only, 'portal_view'))
unique_function(restored, 'portal_view').body = copy.deepcopy(unique_function(original_ast, 'portal_view').body)
assert ast.dump(restored) == ast.dump(original_ast), 'Combined Scene escaped five owner bodies/import and sealed portal hook'"""
driver = change(driver, old_assert, new_assert, 'Normalize exact sealed portal callback before whole-module AST comparison')
driver = change(driver, "'whole_module_AST_identical_except_five_owner_bodies_and_helper_import': True,",
    "'whole_module_AST_identical_except_five_owner_bodies_helper_import_and_sealed_portal_hook': True,\n"
    "    'executed_source': 'combined private source, not sealed owner-only candidate',\n"
    "    'source_path_bindings': SOURCE_PATHS,", 'Explicit combined-source receipt boundary')
driver = change(driver, "'scope': 'Original and private candidate actual Scene prefix",
    "'scope': 'Exact b70 and combined private source actual Scene prefix", 'Label execution scope')
write('inputs/scene.portal-only.py', (PORTAL / 'candidate' / SCENE).read_bytes())
write('verify_combined_owner_controls.py', driver.encode('utf8'))

# Portal controls are the real prior driver with candidate paths redirected to
# combined/, fresh source/patch provenance, and explicit receipt scope.
portal_driver = (PORTAL / 'verify_candidate.py').read_text(encoding='utf8')
portal_driver = change(portal_driver, "HERE = os.path.dirname(os.path.abspath(__file__))",
    "HERE = os.path.dirname(os.path.abspath(__file__))\n"
    "if sys.version_info[0] < 3:\n    HERE = HERE.decode(sys.getfilesystemencoding() or 'mbcs')", 'Py2 Unicode filesystem path')
portal_driver = change(portal_driver, "for variant in ('baseline', 'candidate'):",
    "for variant in ('baseline', 'combined'):", 'Compile actual combined paths')
portal_driver = change(portal_driver, "candidate = load_profile('candidate')", "candidate = load_profile('combined')",
    'Execute actual combined profile module')
portal_driver = change(portal_driver, "changed_scene = source_function(raw('candidate/' + PREFIX + 'scene.py'), 'portal_view')",
    "changed_scene = source_function(raw('combined/' + PREFIX + 'scene.py'), 'portal_view')", 'Extract actual combined callback')
portal_driver = change(portal_driver, "changed_tree = ast.parse(raw('candidate/' + PREFIX + 'portal_profile.py'))",
    "changed_tree = ast.parse(raw('combined/' + PREFIX + 'portal_profile.py'))", 'Inspect actual combined profile AST')
portal_driver = change(portal_driver, "raw('candidate.patch')", "raw('combined.patch')", 'Bind composition patch')
portal_driver = change(portal_driver, "'passed': True, 'python': list(sys.version_info[:3]),",
    "'passed': True, 'executed_source': 'combined private source, not sealed portal-only candidate',\n"
    "        'composition_base': '" + BASE + "', 'python': list(sys.version_info[:3]),", 'Label combined-source portal receipt')
write('verify_combined_portal_controls.py', portal_driver.encode('utf8'))
record('driver-adaptations.json', {'owner_original_sha256': sha((OWNER / 'verify_actual_owner_controls.py').read_bytes()),
    'portal_original_sha256': sha((PORTAL / 'verify_candidate.py').read_bytes()), 'adaptations': adaptations,
    'lifecycle_or_formula_expectations_modified': False})
record('provenance.json', {'files': [{'path': name, 'base_sha256': sha(source_blobs[name]),
    'candidate_sha256': sha((HERE / 'combined' / name).read_bytes())} for name in (SCENE, PROFILE)],
    'cell_sha256': sha((HERE / 'support/cell.py').read_bytes()),
    'patch_sha256': sha((HERE / 'combined.patch').read_bytes()), 'git_base': BASE,
    'candidate_path': 'combined', 'original_sealed_candidates_unchanged': True})
record('ast-and-apply.json', {'both_patches_applied': True, 'composition_patch_replayed_byte_exactly': True,
    'actual_application_order': ['five-owner', 'portal-anchor'],
    'Scene_AST_identical_except': ['five original owner bodies', 'sole scene_owner own_preview import',
                                 'portal_view optional GUI-offset hook with legacy fallback'],
    'five_owner_AST_matches_sealed_candidate': True, 'portal_view_AST_matches_sealed_candidate': True,
    'portal_profile_and_helper_AST_and_LF_normalized_bytes_match_sealed': True,
    'actual_EOL_differences_explicitly_recorded': True,
    'source_files': {name: {'sha256': sha((HERE / 'combined' / name).read_bytes()),
        'bytes': (HERE / 'combined' / name).stat().st_size} for name in (SCENE, PROFILE, HELPER)},
    'combined_patch_sha256': sha((HERE / 'combined.patch').read_bytes()),
    'product_before': product_before, 'product_after': {name: sha((ROOT / name).read_bytes()) for name in product_before},
    'MC_started': False, 'source_qualification_transferred': False, 'native_qualified': False,
    'manual_closed': 0, 'main_repository_product_mutated': False})
assert product_before == {name: sha((ROOT / name).read_bytes()) for name in product_before}
print(json.dumps({'both_actual_patches_applied': True, 'whole_Scene_AST_region_check': True,
    'replay_byte_exact': True, 'fresh_control_drivers_prepared': True, 'product_unchanged': True}))

"""Seal and independently replay the failed long-title native book control."""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / '.runtime/lectern-body-candidate-r21'
PROJECT = ROOT / '.runtime/projects/root-signed-book-r21-v1'
RUNTIME = HERE / 'runtime-native-oracle-v1'
MANIFEST = ROOT / '.runtime/signed-book-r21/source-manifest.json'
SOURCE_MANIFEST_SHA256 = 'cc57450722012534f51238d4442a96021ea26bd447066f1a0f6bef953f342d25'
HOST_SHA256 = '7fdcb301e1f90e4b0e0b84e35e3521e61b7ba3b953a9a31e6a0cb150df7c5c6c'
LOOT = 'behavior_pack/loot_tables/modern_projection/r21_signed_book.json'
NBT = 'behavior_pack/modern_projection/projection/nbt_spatial.py'
FRAME_NAMES = ('native_empty_0', 'native_empty_1')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def replay(package, output):
    report = load(package / 'raw/report.json')
    host = ast.parse((package / 'host/probe_native_book_oracle.py').read_bytes())
    templates = {}
    for node in host.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('SERVER', 'ACQUIRE_INSERT'):
                templates[name] = eval(compile(ast.Expression(node.value), '<archived-template>', 'eval'),
                                       {'__builtins__': {}}, templates)
    acquire = ast.parse(templates['ACQUIRE_INSERT'])
    title_assertions = [node for node in acquire.body if isinstance(node, ast.Assert) and
        isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Call) and
        isinstance(node.test.left.func, ast.Name) and node.test.left.func.id == 'scalar' and
        len(node.test.left.args) == 2 and isinstance(node.test.left.args[1], ast.Constant) and
        node.test.left.args[1].value == 'title']
    assert len(title_assertions) == 1
    title_assertion = title_assertions[0]
    requested = load(package / 'sources' / LOOT)['pools'][0]['entries'][0]['functions'][0]
    assert ast.literal_eval(title_assertion.test.comparators[0]) == requested['title']
    spawn_lines = [node.lineno for node in ast.walk(acquire) if isinstance(node, ast.Call) and
                   isinstance(node.func, ast.Attribute) and node.func.attr == 'SpawnItemToPlayerInv']
    assert len(spawn_lines) == 1 and title_assertion.lineno < spawn_lines[0]
    error_prefix = 'MCDKError: '
    assert report['error'].startswith(error_prefix)
    native_error = json.loads(report['error'][len(error_prefix):])
    error_text = native_error['content'][0]['text']
    value_prefix = 'Code execution failed: '
    assert error_text.startswith(value_prefix)
    observed = ast.literal_eval(error_text[len(value_prefix):].split('\nTraceback', 1)[0])
    helpers = ast.parse((package / 'sources' / NBT).read_bytes())
    functions = [node for node in helpers.body if isinstance(node, ast.FunctionDef) and
                 node.name in ('field_key', 'scalar')]
    assert len(functions) == 2
    namespace = {'tags': copy.deepcopy(observed)}
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<archived-nbt-helpers>', 'exec'), namespace)
    try:
        exec(compile(ast.Module(body=[title_assertion], type_ignores=[]), '<original-title-assertion>', 'exec'), namespace)
    except AssertionError:
        rejected = True
    else:
        rejected = False
    assert rejected
    scalar = namespace['scalar']
    assert scalar(observed, 'title') == 'R21 Native Autho' != requested['title']
    assert scalar(observed, 'author') == requested['author'] == 'R21 Native Loot'
    assert [scalar(page, 'text') for page in observed['pages']] == requested['pages']
    output.mkdir(parents=True)
    crops, images = [], []
    for name in FRAME_NAMES:
        path = package / 'raw' / (name + '.png')
        receipt = load(package / 'raw' / (name + '.capture.json'))
        with Image.open(path) as original:
            assert original.size == (receipt['width'], receipt['height'])
            rgb = original.convert('RGB')
            width, height = rgb.size
            box = (width // 2 - 240, height // 2 - 180, width // 2 + 240, height // 2 + 280)
            crop = rgb.crop(box)
            crop.save(output / (name + '.crop.png'))
            crops.append(crop)
            images.append({'name': name, 'size': list(rgb.size), 'crop_box': list(box),
                'raw_sha256': sha(path), 'raw_pixels_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
                'crop_pixels_sha256': hashlib.sha256(crop.tobytes()).hexdigest()})
    sheet = Image.new('RGB', (crops[0].width * 2, crops[0].height))
    for index, crop in enumerate(crops):
        sheet.paste(crop, (index * crop.width, 0))
    sheet.save(output / 'empty-native-controls.png')
    result = {'schema': 1, 'request': requested, 'observed_native_tags': observed,
        'original_title_assertion_replayed': True, 'original_title_assertion_failed': rejected,
        'title_assertion_before_inventory_write': True, 'requested_title': requested['title'],
        'native_title': scalar(observed, 'title'), 'author_and_two_pages_preserved': True,
        'captures': images, 'authored_captures': 0, 'native_book_oracle_qualified': False,
        'production_qualified': False, 'no_resize_alignment_recolor_or_pixel_fitting': True}
    save(output / 'analysis.json', result)
    return result


def credential_keys(value):
    forbidden = {'token', 'authorization', 'access_token', 'api_key', 'password', 'secret'}
    if isinstance(value, dict):
        return sum(str(key).lower() in forbidden for key in value) + sum(
            credential_keys(entry) for entry in value.values())
    if isinstance(value, list):
        return sum(credential_keys(entry) for entry in value)
    return 0


def verify(package):
    manifest = load(package / 'manifest.json')
    for name, row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    assert all(credential_keys(load(path)) == 0 for path in package.rglob('*.json'))
    report = load(package / 'raw/report.json')
    assert report['completed'] is False and report['restored'] is True and report['source_unchanged'] is True
    assert report['cleanup_errors'] == [] and report['native_book_pixel_oracle_qualified'] is False
    assert [row['label'] for row in report['captures']] == list(FRAME_NAMES)
    assert 'insert' not in report
    assert report['inventory_restore']['restored'] is True
    assert report['inventory_restore']['before'] == report['inventory_restore']['after']
    assert len(report['inventory_restore']['before']) == 36
    assert report['world_restore']['restored'] is True
    frozen = load(package / 'frozen/source-manifest.json')
    prepared = load(package / 'frozen/prepared-v2.json')
    assert sha(package / 'frozen/source-manifest.json') == SOURCE_MANIFEST_SHA256
    assert sha(package / 'host/probe_native_book_oracle.py') == prepared['host_sha256'] == HOST_SHA256
    assert report['binding']['host_sha256'] == HOST_SHA256
    assert report['binding']['source_digest'] == frozen['files_sha256'] == prepared['source_digest']
    assert hashlib.sha256(json.dumps(frozen['files'], ensure_ascii=True).encode('ascii')).hexdigest() == frozen['files_sha256']
    sources = {row['path']: row for row in frozen['files']}
    for path in (package / 'sources').rglob('*'):
        if path.is_file():
            relative = path.relative_to(package / 'sources').as_posix()
            assert sha(path) == sources[relative]['sha256']
    for name, expected in report['binding']['dependencies'].items():
        assert sha(package / 'host/dependencies' / name) == expected
    for name in FRAME_NAMES:
        receipt = load(package / 'raw' / (name + '.capture.json'))
        assert receipt['reliable'] and receipt['native_resolution'] and not receipt['agent_activation_allowed']
        assert sha(package / 'raw' / (name + '.png')) == receipt['sha256']
        assert receipt['game_identity'] == report['session']['game_identity']
    exits = load(package / 'lifecycle/exact-exit.json')
    assert exits['completed'] and all(row['state'] == 'exited' for row in exits['processes'].values())
    assert exits['processes']['game']['exit_code_hex'] == '0xC0000409'
    assert exits['processes']['mcdk']['exit_code_hex'] == '0x00000000'
    lifecycle = load(package / 'lifecycle/summary.json')
    assert lifecycle['force_used'] is False and lifecycle['normal_stop_returncode'] == 1
    assert lifecycle['finalize_returncode'] == 0 and lifecycle['finalize_state'] == 'stopped'
    with tempfile.TemporaryDirectory(prefix='native-book-failed-replay-') as directory:
        replay(package, Path(directory) / 'review')
        for path in (Path(directory) / 'review').iterdir():
            assert sha(path) == sha(package / 'review' / path.name), path.name
    return {'files': len(manifest['files']), 'captures': 2, 'authored_captures': 0,
        'credential_json_keys': 0, 'replayed_original_failure_and_native_pixels': True,
        'manifest_sha256': sha(package / 'manifest.json'),
        'raw_report_sha256': sha(package / 'raw/report.json'),
        'native_book_oracle_qualified': False, 'production_qualified': False}


def pack(output):
    assert not output.exists() and sha(MANIFEST) == SOURCE_MANIFEST_SHA256
    frozen = load(MANIFEST)
    for row in frozen['files']:
        assert sha(PROJECT / row['path']) == row['sha256'], row['path']
    session = load(HERE / 'native-oracle-start-v1.json')
    finalized = load(HERE / 'native-oracle-finalize-v1.stdout.json')
    assert finalized['state'] == 'stopped' and finalized['ready'] is False
    report = load(RUNTIME / 'report.json')
    assert all(session[key] == value for key, value in report['session'].items())
    paths = {'host/' + Path(__file__).name: Path(__file__),
        'host/probe_native_book_oracle.py': HERE / 'probe_native_book_oracle.py',
        'frozen/source-manifest.json': MANIFEST,
        'frozen/prepared-v1.json': HERE / 'native-book-oracle-prepared-v1.json',
        'frozen/prepared-v2.json': HERE / 'native-book-oracle-prepared-v2.json',
        'frozen/owner-only-v2.patch': HERE / 'native-book-oracle-owner-v2.patch',
        'frozen/prelaunch.json': HERE / 'native-oracle-prelaunch-v1.json',
        'lifecycle/exact-exit.json': HERE / 'native-oracle-exit-observation-v1.json',
        'lifecycle/normal-stop.stderr.txt': HERE / 'native-oracle-stop-v1.stderr.txt',
        'host/NATIVE_BOOK_ORACLE.md': HERE / 'NATIVE_BOOK_ORACLE.md'}
    for name in ('.mcdev.json', LOOT, NBT):
        paths['sources/' + name] = PROJECT / name
    for name in report['binding']['dependencies']:
        paths['host/dependencies/' + name] = ROOT / 'tools' / name
    for source in RUNTIME.iterdir():
        if source.is_file():
            paths['raw/' + source.name] = source
    for relative, source in paths.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    launch = {key: session[key] for key in ('id','owner','project','created_at','game_pid',
                                           'game_identity','mcdk_pid','mcdk_identity')}
    launch['noactivation'] = {key: session['noactivation'][key] for key in
        ('requested','dll','mcdk','user_foreground_allowed','agent_activation_allowed')}
    save(output / 'lifecycle/launch.json', launch)
    save(output / 'lifecycle/summary.json', {'normal_stop_requested': True,
        'normal_stop_returncode': 1, 'force_used': False, 'finalize_returncode': 0,
        'finalize_state': finalized['state'], 'exact_observer_completed': True,
        'original_game_identity_absent_at_finalize': True,
        'original_mcdk_identity_absent_at_finalize': True,
        'normal_game_shutdown_qualified': False,
        'limit': 'Normal stop timed out; retained exact handle later observed game 0xC0000409. Cause unclassified.'})
    (output / '.gitattributes').write_text('* -text -diff whitespace=cr-at-eol\n', encoding='ascii')
    replay(output, output / 'review')
    (output / 'README.md').write_text('''# Failed Long-Title Native Lectern Book Oracle

This package preserves an actual strict native-data failure. It is neither
book pixel parity nor an adjudicated product-book pixel failure. Two raw,
native-resolution empty-lectern PNGs and capture receipts are unchanged.
Both originals were opened and show the complete empty native lectern and
cyan support. No authored-book image exists and native book qualification
remains false.

The frozen loot request is R21 Native Authored Book A, author R21 Native
Loot, with the two original nonempty authored pages. Native GetLootItems
returned title R21 Native Autho while preserving author and both pages.
The exact original title assertion failed before SpawnItemToPlayerInv.
No authored item was inserted. The source, original host and failed report
were not changed to accept truncation. A separate short-title follow-up is
only prepared and is not executed evidence in this package.

The attempt plus finally restoration took 12.766562 seconds. All 36 inventory
slots match before/after, world air restoration passed, camera/environment
restoration completed and cleanup errors are empty. All 3033 frozen source
files were verified unchanged when packing. The complete original source
manifest is included; only config, request loot and the exact NBT helpers
are bundled from that project. This package is an offline evidence replay,
not a standalone game project or a runtime reproduction.

Normal stop returned 1. Exact retained handles observed game 0xC0000409 and
MCDK 0; original identities were absent before ordinary finalize returned 0
and state stopped. No force was used. Fixture restoration passed; ordinary
game shutdown is not qualified and the exit cause is unclassified. Launch
and lifecycle fields are explicitly allowlisted; full credential-bearing
session stdout is excluded and every packaged JSON is checked for credential
keys. Source/raw originals remain intact at their original local paths.

Replay with Python 3 and Pillow, without a game, original project paths or
Windows APIs:

python -B -X utf8 host/pack_native_lectern_book_failed_r21.py --verify PACKAGE

Replay verifies every payload hash and source/host/receipt binding, parses
the actual SDK error via JSON and Python literal parsers, re-executes the
archived title assertion with archived scalar helpers, and confirms its
position before actual inventory insertion. It rebuilds both unscaled
native-pixel crops and the two-image sheet; analysis and PNG bytes must
match. No alignment, resize, recolor, mask or pixel fitting is applied.
Successful replay retains the failure and grants no production, powered
appearance, book-pixel, projection-parity or lifecycle qualification.
''', encoding='ascii')
    manifest = {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'captures': 2, 'authored_captures': 0, 'native_book_oracle_qualified': False,
        'production_qualified': False, 'normal_game_shutdown_qualified': False,
        'full_source_manifest_included': True, 'full_game_project_bundled': False,
        'source_digest': frozen['files_sha256'], 'files': {}}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            manifest['files'][path.relative_to(output).as_posix()] = {
                'sha256': sha(path), 'bytes': path.stat().st_size}
    save(output / 'manifest.json', manifest)
    return verify(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify.resolve()) if args.verify else pack(args.output.resolve())))

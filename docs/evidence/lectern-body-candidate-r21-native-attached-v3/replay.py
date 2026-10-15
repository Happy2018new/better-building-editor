"""Portable, bounded replay of the reviewed native attached-book reference."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OWNER = 'book-r20-native-oracle-attached-v3'
SESSION = 'c56d014517a1432ba7ceae2533486b5e'
HOST_SHA = 'c4d3fad841f0718bb81cf74aeca93893be892c6d5c3ae917445348a6d691e9fe'
SOURCE_MANIFEST_SHA = '9248eaf7a60689d33dc912083440e1d89937350b46528624657e74d44aa75f7e'
REPORT_SHA = '535323f720c151d60a03f2c5e96bb0bd7e987e5edc72dbef82bd310bcfb41bfa'
FRAMES = ('native_attached_empty', 'native_attached_authored')
IMAGE_SHAS = ('69118b6562300e0003234ca0a6ae6ae79a3d4f3eb3ce35337c20bd77ab3bc221',
              'eb1cfd42b65952511c891f650976301c97f4d5bf1d6c344136d98825d064bf3d')
NBT = 'behavior_pack/modern_projection/projection/nbt_spatial.py'
LOOT = 'behavior_pack/loot_tables/modern_projection/r21_signed_book.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def credential_keys(value):
    forbidden = {'token', 'authorization', 'access_token', 'api_key', 'password', 'secret'}
    if isinstance(value, dict):
        return sum(str(key).lower() in forbidden for key in value) + sum(
            credential_keys(item) for item in value.values())
    if isinstance(value, list):
        return sum(credential_keys(item) for item in value)
    return 0


def functions(path, names, namespace):
    nodes = [node for node in ast.parse(path.read_bytes()).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<archived-data-gates>', 'exec'), namespace)


def replay(package, output=None):
    manifest = load(package / 'manifest.json')
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    for name, row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    assert all(credential_keys(load(path)) == 0 for path in package.rglob('*.json'))
    report = load(package / 'raw/report.json')
    assert sha(package / 'raw/report.json') == REPORT_SHA
    assert report['session']['id'] == SESSION and report['session']['owner'] == OWNER
    assert all(report[key] is True for key in ('completed', 'restored', 'source_unchanged',
        'native_authored_data_and_client_replication_validated'))
    assert not report['cleanup_errors'] and 'error' not in report
    assert all(report[key] is False for key in ('projection_tested', 'production_qualified',
        'causal_isolation_claimed', 'native_book_pixel_oracle_qualified'))
    assert report['elapsed_seconds'] < 120.
    assert [row['label'] for row in report['captures']] == list(FRAMES)
    assert sha(package / 'host/probe_native_book_oracle_attached_v3.py') == HOST_SHA
    assert report['binding']['host_sha256'] == HOST_SHA
    assert sha(package / 'frozen/source-manifest.json') == SOURCE_MANIFEST_SHA
    frozen = load(package / 'frozen/source-manifest.json')
    digest = hashlib.sha256(json.dumps(frozen['files'], ensure_ascii=True).encode('ascii')).hexdigest()
    assert digest == frozen['files_sha256'] == report['binding']['source_digest']
    assert len(frozen['files']) == frozen['file_count'] == 3033
    by_path = {row['path']: row for row in frozen['files']}
    for path in (package / 'sources').rglob('*'):
        if path.is_file():
            row = by_path[path.relative_to(package / 'sources').as_posix()]
            assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
    config = load(package / 'sources/.mcdev.json')
    assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
        'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    namespace = {}
    functions(package / 'sources' / NBT, ('field_key', 'scalar'), namespace)
    functions(package / 'host/probe_native_book_oracle.py',
        ('compound', 'value', 'book_signature', 'authored_data_preserved'), namespace)
    scalar = namespace['scalar']
    request = load(package / 'sources' / LOOT)['pools'][0]['entries'][0]['functions'][0]
    assert request == {'function': 'set_book_contents', 'title': 'R21 Book A',
        'author': 'R21 Native Loot', 'pages': ['First authored control.', 'Second authored control.']}
    insert = report['insert']
    expected = insert['native_loot_items'][0]['userData']
    assert all(insert[key]['userData'] == expected for key in ('submitted_native_item',
        'actual_inventory_item', 'inventory_after_use'))
    assert scalar(expected, 'title') == request['title']
    assert scalar(expected, 'author') == request['author']
    assert [scalar(page, 'text') for page in scalar(expected, 'pages')] == request['pages']
    assert insert['native_use_return'] is True and not insert['actual_enchantments']
    assert insert['item_data_manufactured'] is False and insert['nbt_setter_used'] is False
    assert report['placement']['block'] == {'name': 'minecraft:lectern', 'aux': 2}
    states = {'powered_bit': False, 'minecraft:cardinal_direction': 'north'}
    assert report['placement']['states'] == report['empty']['server']['states'] == states
    for replicated in report['replication']:
        assert namespace['book_signature'](replicated['server']['nbt']) == namespace['book_signature'](replicated['client']['nbt'])
    final = report['replication'][-1]
    assert all(namespace['authored_data_preserved'](row['nbt'], insert['actual_inventory_item'])
               for row in final.values())
    assert final['server']['states'] == states
    calls = [node.func.attr for row in report['operations'] for node in ast.walk(ast.parse(row['code']))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
    assert 'SetBlockEntityData' not in calls and calls.count('PlayerUseItemToPos') == 2
    inventory = report['inventory_restore']
    assert inventory['restored'] and inventory['before'] == inventory['after']
    assert len(inventory['before']) == 36
    world, camera = report['world_rotation_restore'], report['camera_restore']
    assert world['restored'] and all(row['after'] == {'name': 'minecraft:air', 'aux': 0} for row in world['rows'])
    assert all(abs(a-b) < .01 for a, b in zip(world['foot_before'], world['foot_after']))
    assert all(abs(a-b) < .01 for a, b in zip(world['rotation_before'], world['rotation_after']))
    assert camera['restored'] and report['environment_restore'] is True
    assert all(abs(a-b) < .02 for a, b in zip(camera['position_before'], camera['position_after']))
    assert all(abs((a-b+180.) % 360.-180.) < .02 for a, b in zip(camera['rotation_before'], camera['rotation_after']))
    assert camera['pitch_lock'] == report['original_camera']['pitch_lock']
    assert camera['yaw_lock'] == report['original_camera']['yaw_lock']
    assert all(row['memory']['commit_available_bytes'] >= 6*1024**3 and
        row['handles']['status'] == 'live' and row['handles']['handle_count'] < 200000
        for row in report['resource_boundaries'])
    rows, crops = [], []
    camera_signature = None
    for label, expected_sha, capture in zip(FRAMES, IMAGE_SHAS, report['captures']):
        path = package / 'raw' / (label + '.png')
        receipt = load(package / 'raw' / (label + '.capture.json'))
        assert receipt == capture['receipt'] and receipt['sha256'] == sha(path) == expected_sha
        assert receipt['reliable'] and receipt['native_resolution'] and not receipt['agent_activation_allowed']
        assert receipt['guarded_no_activation'] and receipt['background_safe'] and receipt['foreground_unchanged']
        assert receipt['game_identity'] == report['session']['game_identity']
        before = capture['before']
        assert before == capture['after']
        assert before['attached_eye_position_verified'] and not before['custom_projection_active']
        assert before['custom_book_preview_groups'] == 0
        assert all(abs(before['position'][i]-(before['foot'][i]+(1.62 if i == 1 else 0))) < .02 for i in range(3))
        if camera_signature is None:
            camera_signature = before
        assert camera_signature == before
        with Image.open(path) as original:
            assert original.size == (receipt['width'], receipt['height']) == (1994, 1105)
            rgb = original.convert('RGB')
            box = (797, 405, 1197, 705)
            crop = rgb.crop(box)
            crops.append(crop)
            rows.append({'label': label, 'source_sha256': expected_sha, 'crop_box': list(box),
                'raw_pixels_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
                'crop_pixels_sha256': hashlib.sha256(crop.tobytes()).hexdigest()})
    exits = load(package / 'lifecycle/exact-process-exit.json')
    ready = load(package / 'lifecycle/launch-ready.json')
    assert exits['completed'] and exits['session'] == SESSION and exits['owner'] == OWNER
    assert ready['id'] == SESSION and ready['exact_process_handles_retained']
    for kind, code in (('game', '0xC0000409'), ('mcdk', '0x00000000')):
        row = exits['processes'][kind]
        assert row['state'] == 'exited' and row['exit_code_hex'] == code
        assert row['pid'] == ready[kind+'_pid'] and row['identity'] == ready[kind+'_identity']
    stop = load(package / 'lifecycle/ordinary-stop.result.json')
    finalization = load(package / 'lifecycle/finalize.result.json')
    assert stop['ordinary_stop_returncode'] == 1 and not stop['force']
    assert finalization['finalize_returncode'] == 0 and finalization['state'] == 'stopped'
    assert finalization['ready'] is False and not finalization['force']
    assert 'Game has not closed' in (package / 'lifecycle/ordinary-stop.stderr.txt').read_text(encoding='utf8')
    review = load(package / 'review/visual-review.json')
    assert review['full_originals_opened_by'] == ['book_r20', 'root']
    assert review['empty_has_visible_book'] is False and review['authored_has_visible_native_book'] is True
    assert review['native_reference_usable'] and not any(review[key] for key in (
        'candidate_qualified', 'scene_qualified', 'production_qualified', 'single_cause_identified'))
    sheet = Image.new('RGB', (800, 300))
    for index, crop in enumerate(crops):
        sheet.paste(crop, (400*index, 0))
    result = {'schema': 1, 'captures': rows, 'request_and_native_data_exact': True,
        'inventory_and_world_camera_restored': True, 'source_manifest_digest_replayed': digest,
        'native_reference_usable_after_recorded_visual_review': True,
        'automated_book_visibility_detector_claimed': False, 'candidate_qualified': False,
        'scene_qualified': False, 'production_qualified': False, 'single_cause_identified': False,
        'ordinary_stop_returncode': 1, 'game_exit_code': '0xC0000409', 'mcdk_exit_code': '0x00000000',
        'normal_shutdown_qualified': False, 'finalize_state': 'stopped', 'force_used': False,
        'sheet_pixels_sha256': hashlib.sha256(sheet.tobytes()).hexdigest()}
    if output is not None:
        assert not output.exists()
        output.mkdir(parents=True)
        sheet.save(output / 'native-empty-authored.png')
        save(output / 'replay.json', result)
    return result


def pack(output):
    assert not output.exists()
    project = ROOT / '.runtime/projects/book-r20-native-oracle-attached-v3'
    frozen_path = HERE / 'native-oracle-attached-v3/source-manifest.json'
    frozen = load(frozen_path)
    assert sha(frozen_path) == SOURCE_MANIFEST_SHA
    actual = {'.mcdev.json'} | {path.relative_to(project).as_posix()
        for folder in ('behavior_pack', 'resource_pack') for path in (project / folder).rglob('*') if path.is_file()}
    assert actual == {row['path'] for row in frozen['files']}
    for row in frozen['files']:
        path = project / row['path']
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
    runtime = HERE / 'runtime-native-oracle-attached-v3'
    lifecycle = HERE / 'native-oracle-attached-v3-launch-amendment-v1'
    paths = {'replay.py': Path(__file__), 'frozen/source-manifest.json': frozen_path}
    for name in ('report.json',) + tuple(label + suffix for label in FRAMES for suffix in ('.png', '.capture.json')):
        paths['raw/' + name] = runtime / name
    for name in ('probe_native_book_oracle.py', 'probe_native_book_oracle_short_v2.py',
                 'probe_native_book_oracle_attached_v3.py', 'launch_native_book_attached_v3_amendment.py'):
        paths['host/' + name] = HERE / name
    for name in ('prelaunch.json', 'launch-ready.json', 'exact-process-exit.json',
                 'ordinary-stop.result.json', 'ordinary-stop.stderr.txt', 'finalize.result.json'):
        paths['lifecycle/' + name] = lifecycle / name
    for name in ('.mcdev.json', NBT, LOOT):
        paths['sources/' + name] = project / name
    for relative, source in paths.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    save(output / 'review/visual-review.json', {'schema': 1,
        'full_originals_opened_by': ['book_r20', 'root'], 'empty_has_visible_book': False,
        'authored_has_visible_native_book': True, 'native_reference_usable': True,
        'observation': 'Native V-shaped pages, cover and position on lectern are clearly visible.',
        'candidate_qualified': False, 'scene_qualified': False, 'production_qualified': False,
        'single_cause_identified': False, 'source_files_reverified_at_pack': 3033,
        'original_process_identities_absent_before_finalize': True})
    (output / '.gitattributes').write_text('* -text -diff whitespace=cr-at-eol\n', encoding='ascii')
    (output / 'README.md').write_text('''# Attached Native Book V3: Usable Reference Only

The agent and root independently opened both complete original images. Empty
shows no book; authored clearly shows the native V-shaped pages, cover and
position on the lectern. This removes the native-reference source blocker.
It does not qualify candidate rendering, Scene, editor UI, projection parity,
production or a single explanation for previous missing-book results.

Actual inventory lectern placement produced north aux 2. Native authored loot
and actual PlayerUseItemToPos preserve the exact title, author and both pages
in inventory and complete client/server NBT. No NBT setter or manufactured item
data is used. Every frame verifies attached eye position, inactive custom
projection and zero custom book preview groups. Camera checks are identical
before/after and across both original 1994x1105 images. Acquisition is reliable
WGC with no activation, rescaling, alignment, recoloring or fitted pixels.

Raw report, original PNGs and capture receipts remain byte-identical. The raw
acquisition report intentionally retains pixel qualification false; the separate
visual review records the two reviewers' actual observation. Offline replay
does not claim an automated book detector or rerun a native game renderer.

Probe elapsed 15.5798507 seconds. All 36 inventory slots match, fixture air and
player/camera/environment restore, and source fingerprints remain unchanged.
Each boundary passed canonical 6 GiB commit and 200000 owned-handle gates.
Packing independently rehashed every one of the 3033 cold-clone source files.
The full manifest is bundled; only config, native request loot and exact NBT
helpers are included as source bytes. Portable replay verifies that manifest's
digest and the bundled source subset. The full game project and native runtime
dependency closure are intentionally not bundled.

One ordinary close returned 1. Retained exact handles recorded MC 0xC0000409
and MCDK 0 at 06:17:41; both identities were independently absent before normal
finalize returned 0/stopped/ready false. No force was used. Normal game shutdown
is unqualified and exit cause remains unclassified. Credential-bearing startup
and finalize stdout are excluded; every packaged JSON is checked for forbidden
credential keys. Original failed v1/v2 evidence remains unchanged.

Replay using Python 3 and Pillow, without Windows APIs, original source paths,
game, NumPy or repository imports:

python -B -X utf8 replay.py --verify PACKAGE

Optionally create a fresh output directory containing an unscaled side-by-side
crop and replay JSON:

python -B -X utf8 replay.py --verify PACKAGE --output FRESH_REPLAY_OUTPUT

Replay checks payload hashes, exact native item/NBT equality with archived
parser/data-gate functions, source manifest binding, placement, camera and
absence of custom owners, restoration/resources and abnormal exact exit. The
same fixed crop is used for both images; originals remain the visual authority.
No diagnostic matrix, cold window or runtime action is authorized by this pack.
''', encoding='ascii')
    files = {path.relative_to(output).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
             for path in sorted(output.rglob('*')) if path.is_file()}
    save(output / 'manifest.json', {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'native_reference_usable_after_visual_review': True, 'candidate_qualified': False,
        'scene_qualified': False, 'production_qualified': False, 'single_cause_identified': False,
        'normal_shutdown_qualified': False, 'full_source_project_bundled': False, 'files': files})
    return replay(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--pack', type=Path)
    action.add_argument('--verify', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.pack:
        assert args.output is None
        result = pack(args.pack)
    else:
        result = replay(args.verify, args.output)
    print(json.dumps(result, ensure_ascii=True), flush=True)

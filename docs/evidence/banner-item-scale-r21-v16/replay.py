"""Portable standard-library replay of the one-shot V16 banner scale control."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

OWNER = 'shield-r20-v16-banner-scale-control'
SESSION = 'd80ea2a571984f288dad7d336029354b'
DIGEST = '504c79130e8cc3836418a6cd19a8fcafd5ccee7443c29f1927d75837d960d1b4'
HOST = 'ff79a792435dac90b9b1f321a8aa12bde2e72c312526118d99ad416638d99355'
FRAMES = ('01-unbound', '02-bound-small', '03-same-binding-scale-one')
SHAS = ('3e4ca4d0dc64f53abf70286b934721265bef09db2c842ce3f9254067ae58b694',
        '9ed533e77807061497f8462b6746fdf9356a0ca657a80675e7894b121df671fc',
        '8c44acaefb4210d4caaae1e6950f51a4c0257c8fe6e163e1ce35b3b2bf498361')
RELOADS = ('auto_hot_reload_mods', 'auto_hot_reload_ui',
           'auto_hot_reload_shaders', 'auto_hot_reload_materials')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='ascii') as stream:
        stream.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')


def no_credentials(value):
    if isinstance(value, dict):
        assert not {'token', 'authorization', 'access_token', 'api_key', 'password', 'secret'} & {
            str(key).lower() for key in value}
        for item in value.values():
            no_credentials(item)
    elif isinstance(value, list):
        for item in value:
            no_credentials(item)


def png(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, payload, kinds, dimensions = 8, bytearray(), [], None
    while offset < len(data):
        length = struct.unpack('>I', data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        body = data[offset+8:offset+8+length]
        crc = struct.unpack('>I', data[offset+8+length:offset+12+length])[0]
        assert len(body) == length and zlib.crc32(kind + body) & 0xffffffff == crc
        kinds.append(kind)
        if kind == b'IHDR':
            dimensions = struct.unpack('>IIBBBBB', body)
        if kind == b'IDAT':
            payload.extend(body)
        offset += length + 12
        if kind == b'IEND':
            assert length == 0 and offset == len(data)
            break
    assert kinds[0] == b'IHDR' and kinds[-1] == b'IEND'
    width, height, depth, color, compression, filtering, interlace = dimensions
    assert (width, height, depth, compression, filtering, interlace) == (1994, 1105, 8, 0, 0, 0)
    assert color in (2, 6)
    raw = zlib.decompress(payload)
    stride = width * (3 if color == 2 else 4) + 1
    assert len(raw) == stride * height
    assert all(raw[row * stride] <= 4 for row in range(height))
    return {'width': width, 'height': height, 'sha256': sha(path),
            'decompressed_scanlines_sha256': hashlib.sha256(raw).hexdigest()}


def verify_project(project, plan):
    paths = [path for folder in ('behavior_pack', 'resource_pack')
             for path in (project / folder).rglob('*') if path.is_file()
             and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')]
    paths += list((project / 'tools').glob('*.py'))
    paths += list((project / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
    actual = {path.relative_to(project).as_posix(): sha(path) for path in sorted(paths)}
    assert actual == plan['files']
    assert sha(project / '.mcdev.json') == plan['config_sha256']
    return len(actual)


def replay(package, project=None):
    manifest = load(package / 'manifest.json')
    actual = {path.relative_to(package).as_posix() for path in package.rglob('*') if path.is_file()}
    assert actual == set(manifest['files']) | {'manifest.json'}
    for name, row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    for path in package.rglob('*.json'):
        no_credentials(load(path))
    plan = load(package / 'frozen/plan.json')
    launcher = load(package / 'frozen/launcher-inputs.json')
    digest = hashlib.sha256(json.dumps(plan['files'], sort_keys=True,
        separators=(',', ':')).encode('ascii')).hexdigest()
    assert digest == plan['source_sha256'] == launcher['source_sha256'] == DIGEST
    assert sha(package / 'frozen/plan.json') == launcher['plan_sha256']
    assert plan['phases'] == {'banner': ['patterned']} and plan['poses'] == {'yaw90': {'yaw': 90., 'pitch': 0.}}
    assert plan['initial_attachment_scale'] == .0625 and plan['only_scale_update'] == 1.
    assert plan['no_rebind'] and plan['left_slot_unchanged'] and plan['maximum_images'] == 3
    for name, digest in plan['host_sha256'].items():
        assert sha(package / 'host' / name) == digest
    assert sha(package / 'host/host.py') == HOST
    for name, digest in launcher['dependency_sha256'].items():
        assert sha(package / 'dependencies' / name) == digest
    for name, digest in plan['artifact_sha256'].items():
        assert sha(package / 'frozen' / name) == digest
    assert sha(package / 'sources/.mcdev.json') == plan['config_sha256']
    config = load(package / 'sources/.mcdev.json')
    assert all(config[key] is False for key in RELOADS)
    for path in (package / 'sources').rglob('*'):
        if path.is_file() and path.name != '.mcdev.json':
            assert sha(path) == plan['files'][path.relative_to(package / 'sources').as_posix()]
    ready = load(package / 'lifecycle/ready-summary.json')
    versions = load(package / 'raw/runtime-version-config-check.json')
    assert ready['id'] == versions['session'] == SESSION and ready['owner'] == versions['owner'] == OWNER
    assert versions['passed'] and versions['exact_handles_retained_before_this_probe']
    assert versions['versions'] == {'client': '1.21.130.0', 'server': '1.21.130.0'}
    assert all(versions['reloads'][key] is False for key in RELOADS)
    inputs = load(package / 'frozen/inputs.json')
    item = inputs['items']['patterned']
    assert set(inputs['items']) == {'patterned'}
    assert item['newItemName'] == 'minecraft:banner' and item['newAuxValue'] == 4 and not item['isEnchanted']
    patterns = item['userData']['Patterns']
    assert [(row['Color']['__value__'], row['Pattern']['__value__']) for row in patterns] == [(1, 'bo'), (14, 'cr'), (11, 'mc')]
    assert all(row['Color']['__type__'] == 3 and row['Pattern']['__type__'] == 8 for row in patterns)
    receipts = [load(path) for path in sorted((package / 'receipts').glob('*.json'))]
    expected = [('server', 'journal'), ('client', 'setup'), ('client', 'mount'), ('client', 'bind'),
                ('client', 'scale'), ('client', 'restore'), ('server', 'restore'), ('server', 'absent')]
    assert len(receipts) == len(expected)
    for receipt, (side, action) in zip(receipts, expected):
        assert receipt['action'] == action and receipt['phase'] == 'banner' and 'error' not in receipt
        assert receipt['owner'] == OWNER and receipt['source_sha256'] == DIGEST
        for kind in ('game', 'mcdk'):
            for suffix in ('pid', 'identity'):
                assert receipt[kind + '_' + suffix] == ready[kind + '_' + suffix] == versions[kind + '_' + suffix]
        code = receipt['code']
        assert hashlib.sha256(code.encode('ascii')).hexdigest() == receipt['code_sha256']
        assert code.endswith((package / 'host' / (side + '.py')).read_text(encoding='ascii'))
        assigned = {}
        for node in ast.parse(code).body[:8]:
            if isinstance(node, ast.Assign):
                assigned[node.targets[0].id] = ast.literal_eval(node.value)
        assert assigned['ACTION'] == action and assigned['INPUTS'] == inputs
        assert assigned['LABELS'] == ['patterned'] and assigned['CONFIG'] == {'pose': 'yaw90'}
        assert assigned['POSES'] == plan['poses'] and assigned['MODELS'] == plan['host_models']
    journal, setup, mount, bind, scale, client_restore, server_restore, absent = [row['result'] for row in receipts]
    actor = journal['actors']['patterned']
    assert setup['rows'][0]['actor'] == actor and setup['rows'][0]['set_model_result'] >= 0
    assert setup['rows'][0]['client_current_dimension'] == 0 and setup['rows'][0]['native_material_result']
    assert mount['screen'] == [499., 277.]
    assert mount['layout'][0]['position'] == [8., 88.63999938964844]
    assert mount['layout'][0]['size'] == [235.5, 177.27999877929688]
    binding = bind['bindings'][0]
    assert len(bind['bindings']) == 1 and binding['item'] == item and binding['input_unmodified']
    assert binding['scale'] == .0625 and binding['rotation'] == [0., 0., 0.]
    assert scale['identity'] == binding['identity'] == 0 and scale['actor'] == actor
    assert scale['returned'] and not scale['rebound'] and scale['old_scale'] == .0625 and scale['scale'] == 1.
    for row in (mount, bind, scale):
        assert row['render'][0]['params'] == {'entity_id': actor, 'scale': 1.4, 'render_depth': -50,
            'init_rot_z': 0., 'init_rot_y': 90., 'init_rot_x': 0.}
        assert row['render'][0]['returned']
    assert client_restore['restored'] and client_restore['controls'] == client_restore['bindings'] == 0
    assert client_restore['models_reset'] and client_restore['camera_untouched'] and client_restore['inventory_blocks_scene_untouched']
    assert server_restore['destroy_requested'] and server_restore['journal_retained']
    assert absent['actors_absent'] and absent['journal_removed'] and absent['foot_before'] == absent['foot_after']
    assert absent['actors']['patterned'] == {'position': None, 'engine_type': None, 'entity': actor}
    image_rows = []
    signature = None
    for label, digest in zip(FRAMES, SHAS):
        path = package / 'raw' / (label + '.png')
        capture = load(package / 'raw' / (label + '.capture.json'))
        assert sha(path) == capture['sha256'] == digest
        assert capture['ok'] and capture['reliable'] and capture['native_resolution']
        assert not capture['agent_activation_allowed'] and not capture['activation_fallback']
        assert capture['guarded_no_activation'] and capture['background_safe'] and capture['foreground_unchanged']
        assert capture['owner'] == OWNER and capture['game_identity'] == ready['game_identity']
        assert capture['frame']['frame_qpc_100ns'] >= capture['frame']['request_qpc_100ns']
        current = {key: capture['window'][key] for key in ('hwnd', 'pid', 'x', 'y', 'width', 'height')}
        if signature is None:
            signature = current
        assert signature == current
        image_rows.append(png(path))
    start = load(package / 'lifecycle/start-request.json')
    assert start['resources']['commit']['commit_available_bytes'] >= 6 * 1024 ** 3
    assert len(start['resources']['games']) <= 1 and not start['replay_allowed']
    exact = load(package / 'lifecycle/exact-exit.json')
    assert exact['completed'] and exact['session'] == SESSION and exact['owner'] == OWNER
    assert exact['opened_at'] < versions['at'] < receipts[0]['at']
    stop = load(package / 'lifecycle/stop-result.json')
    final_request = load(package / 'lifecycle/finalize-request.json')
    final = load(package / 'lifecycle/finalize-result.json')
    assert not stop['completed'] and not stop['force'] and stop['error']['type'] == 'RuntimeError'
    assert 'Game has not closed' in stop['error']['message']
    assert not any(final_request['process_alive'].values()) and not final_request['force']
    assert final['completed'] and final['state'] == 'stopped' and not any(final['process_alive'].values()) and not final['force']
    for kind, exit_code in (('game', '0xC0000409'), ('mcdk', '0x00000000')):
        row = exact['processes'][kind]
        assert row['pid'] == ready[kind + '_pid'] and row['identity'] == ready[kind + '_identity']
        assert row['state'] == 'exited' and row['exit_code_hex'] == exit_code
        assert row['observed_at'] < final_request['at']
    review = load(package / 'review.json')
    assert review['full_originals_opened_by'] == ['shield_r20', 'root']
    assert review['same_binding_scale_control_visible']
    assert not any(review[key] for key in ('frame_pose_qualified', 'proportions_qualified',
        'thickness_qualified', 'scene_depth_qualified', 'production_qualified', 'normal_shutdown_qualified'))
    checked = verify_project(project, plan) if project is not None else None
    return {'passed': True, 'owner': OWNER, 'session': SESSION, 'captures': image_rows,
        'source_manifest_files': len(plan['files']), 'source_manifest_digest': DIGEST,
        'external_frozen_files_rehashed': checked, 'same_item_same_binding_scale_only': True,
        'restored_and_finalized': True, 'game_exit_code': '0xC0000409', 'mcdk_exit_code': '0x00000000',
        'normal_shutdown_qualified': False, 'frame_pose_qualified': False, 'proportions_qualified': False,
        'thickness_qualified': False, 'scene_depth_qualified': False, 'production_qualified': False}


def build(output):
    root = Path(__file__).resolve().parents[1]
    runtime = root / '.runtime/banner-scale-control-r21-v1'
    source = root / '.runtime/banner-scale-control-r21'
    plan = load(runtime / 'plan.json')
    launcher = load(runtime / 'launcher-inputs.json')
    project = Path(plan['project'])
    count = verify_project(project, plan)
    assert not output.exists()
    files = {'replay.py': Path(__file__)}
    for path in source.glob('*.py'):
        files['host/' + path.name] = path
    for name in ('plan.json', 'launcher-inputs.json', 'inputs.json', 'layout-estimate.json', 'offline-check.json'):
        files['frozen/' + name] = runtime / name
    files['raw/runtime-version-config-check.json'] = runtime / 'runtime-version-config-check.json'
    for path in (runtime / 'runtime-images').iterdir():
        if path.is_file():
            files['raw/' + path.name] = path
    for path in (runtime / 'runtime-receipts').glob('*.json'):
        files['receipts/' + path.name] = path
    for name in ('start-request.json', 'start-result.json', 'ready-summary.json', 'exact-exit.json',
                 'stop-request.json', 'stop-result.json', 'finalize-request.json', 'finalize-result.json', 'start.stderr.txt'):
        files['lifecycle/' + name] = runtime / 'runtime-launch' / name
    for name, digest in launcher['dependency_sha256'].items():
        assert sha(root / name) == digest, name
        files['dependencies/' + name] = root / name
    files['sources/.mcdev.json'] = project / '.mcdev.json'
    for name in plan['files']:
        if 'd19ff5bff710ac9e' in name or name in ('resource_pack/ui/PyreactBase.json',
            'resource_pack/netease_models.json', 'resource_pack/materials/entity.material'):
            files['sources/' + name] = project / name
    for name, path in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    save(output / 'review.json', {'schema': 1, 'full_originals_opened_by': ['shield_r20', 'root'],
        'same_binding_scale_control_visible': True, 'unbound_negative_has_no_banner_attachment': True,
        'small_binding_adds_tiny_horizontal_patterned_banner': True,
        'scale_one_adds_large_patterned_banner_with_short_stalk': True,
        'current_pose': 'horizontal and tilted; does not match upright frame item pose',
        'paperdoll_right_control_boundary_crossed': True, 'full_item_inside_native_window': True,
        'frame_pose_qualified': False, 'proportions_qualified': False, 'thickness_qualified': False,
        'scene_depth_qualified': False, 'production_qualified': False, 'normal_shutdown_qualified': False,
        'source_files_rehashed_at_pack': count, 'runtime_after_release': False,
        'runtime_resource_evidence_limit': 'Launch snapshot is archived. Other runtime 6 GiB gates ran in frozen code, but per-call resource snapshots were console-only.'})
    (output / 'README.md').write_text('''# V16 Banner: Same Binding Scale Control Only

Three original 1994x1105 WGC images, opened independently by shield_r20 and root,
show unbound negative, one typed patterned banner at scale 1/16, then the same
binding ID 0 changed once to scale 1.0. There is no rebind, new angle or UI refit.
Patterns bo1/cr14/mc11 and the short stalk are visible after scaling. The result
is horizontal and tilted and extends across the PaperDoll control right boundary,
while remaining inside the native window. This is not upright frame-item pose,
proportion, thickness, Scene clipping/shared depth or production qualification.
Standing/wall-banner block evidence is not used to qualify this item.

Frozen left layout [8,88.64]/[235.5,177.28], yaw90/pitch0/z0, RenderEntity scale
1.4 and depth -50 remain fixed. Complete request code and native return values,
exact process identities, versions, source/launcher/input manifests, all host
source, launcher dependency bytes and relevant resource source subset are bundled.
No complete game project or game binaries are bundled. All frozen project files
were independently rehashed during packing. Optional --frozen-project rehashes
that external project again; portable replay otherwise reads only this package.
Launch has an archived 6 GiB resource snapshot; subsequent gates executed in
frozen code, but console-only per-call resource snapshots are not reconstructed.

Client controls/bindings/models were restored before server destruction. Actual
GetPos and engine type are null; player foot is unchanged. One ordinary close
timed out. Retained exact handles recorded game 0xC0000409 and MCDK 0 at 07:45:41
local. Both identities were absent before finalize succeeded at 07:45:55. No
force or repeated close was used. Normal shutdown remains unqualified. The
spawn-to-observer-open polling gap is preserved; handle coverage is not claimed
from process spawn. Credential-bearing startup stdout/session files are excluded.

Replay with Python 3 standard library, without repository imports, Windows,
game, Pillow, NumPy, network, native DLLs or live process inspection:

    python -I -B -X utf8 replay.py --verify PACKAGE

Optional external source validation:

    python -I -B -X utf8 replay.py --verify PACKAGE --frozen-project PROJECT

Replay validates all payload hashes, PNG CRC/decompression/scanline lengths,
exact item and typed patterns, request source/hash, one binding and one scale,
fixed view/layout/identity, restore/actual absence, failed close/actual exits and
successful finalize. It replays archived evidence and does not run a renderer
or claim an automatic visual shape/thickness detector. Original images are the
visual authority. Runtime is fully released; this package authorizes no launch.
''', encoding='ascii')
    (output / '.gitattributes').write_text('* -text -diff whitespace=cr-at-eol\n', encoding='ascii')
    manifest = {path.relative_to(output).as_posix(): {'sha256': sha(path), 'bytes': path.stat().st_size}
                for path in sorted(output.rglob('*')) if path.is_file()}
    save(output / 'manifest.json', {'schema': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
        'owner': OWNER, 'source_files_rehashed_at_pack': count, 'files': manifest})
    return replay(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--build', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--frozen-project', type=Path)
    args = parser.parse_args()
    result = build(args.build) if args.build is not None else replay(args.verify, args.frozen_project)
    print(json.dumps(result, ensure_ascii=True), flush=True)

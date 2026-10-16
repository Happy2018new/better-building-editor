"""Archive and independently replay the five frozen world-layer controls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

FRAMES = ('native_two', 'native_lower', 'projected_full', 'projected_hidden', 'projected_shown')
OWNER = 'book-r20-context-hidden-v1'
SESSION = '7148a861201a474789f20f51219b2b6f'
HOST_SHA = 'baca5f6372a4031543b9a294cb97df8ed9ff822605c88cd83e239d4eb3eb30c2'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def credentials(value):
    if isinstance(value, dict):
        assert not {'token', 'authorization', 'access_token', 'api_key', 'password', 'secret'} & {str(k).lower() for k in value}
        for item in value.values():
            credentials(item)
    elif isinstance(value, list):
        for item in value:
            credentials(item)


def png(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed, dimensions = 8, bytearray(), None
    while offset < len(data):
        length = struct.unpack('>I', data[offset:offset+4])[0]
        kind, body = data[offset+4:offset+8], data[offset+8:offset+8+length]
        assert zlib.crc32(kind + body) & 0xffffffff == struct.unpack('>I', data[offset+8+length:offset+12+length])[0]
        if kind == b'IHDR':
            dimensions = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            compressed.extend(body)
        offset += length + 12
        if kind == b'IEND':
            break
    assert offset == len(data) and dimensions[:2] == (1994, 1105)
    width, height, depth, color, compression, filtering, interlace = dimensions
    assert depth == 8 and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0)
    raster = zlib.decompress(compressed)
    stride = width * (3 if color == 2 else 4) + 1
    assert len(raster) == height * stride and all(raster[i] <= 4 for i in range(0, len(raster), stride))
    return hashlib.sha256(raster).hexdigest()


def replay(package):
    manifest = load(package / 'manifest.json')
    assert {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()} == set(manifest['files']) | {'manifest.json'}
    for name, row in manifest['files'].items():
        path = package / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    for path in package.rglob('*.json'):
        credentials(load(path))
    report = load(package / 'raw/report.json')
    assert report['session']['id'] == SESSION and report['session']['owner'] == OWNER
    assert all(report[k] is True for k in ('completed', 'restored', 'source_unchanged'))
    assert not report['cleanup_errors'] and not report.get('error') and report['elapsed_seconds'] < 120
    assert all(report[k] is False for k in ('pixel_acceptance_claimed', 'production_qualified', 'candidate_gate_changed'))
    assert report['binding']['host_sha256'] == sha(package / 'host/probe_context_hidden_v1.py') == HOST_SHA
    frozen = load(package / 'frozen/source-manifest.json')
    assert sha(package / 'frozen/source-manifest.json') == report['binding']['source_manifest_sha256']
    digest = hashlib.sha256(json.dumps(frozen['files'], ensure_ascii=True).encode('ascii')).hexdigest()
    assert len(frozen['files']) == 3144 and digest == frozen['files_sha256'] == report['binding']['source_digest']
    indexed = {row['path']: row for row in frozen['files']}
    for path in (package / 'sources').rglob('*'):
        if path.is_file():
            row = indexed[path.relative_to(package / 'sources').as_posix()]
            assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
    config = load(package / 'sources/.mcdev.json')
    assert all(config[k] is False for k in ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    identities = set()
    for phase, expected in (('full', [4421, 8517, 16709, 20805]), ('hidden', [4421]), ('shown', [4421, 8517, 16709, 20805])):
        row = report['phases'][phase]
        state = row['state']
        assert state['same_document'] and state['source_unchanged'] and state['active'] and not state['preparing']
        assert state['hidden'] == ([1] if phase == 'hidden' else [])
        identities.add((state['editor_id'], state['document_id']))
        assert len(row['active_native_receipts']) == 1
        materials = row['active_native_receipts'][0]['materials']
        assert materials == [{'indices': expected, 'material': ['minecraft:cyan_concrete', 0]}]
    assert len(identities) == 1 and set(report['captures']) == set(FRAMES)
    rasters, cameras = {}, []
    for label in FRAMES:
        row = report['captures'][label]
        receipt = load(package / 'raw' / (label + '.capture.json'))
        path = package / 'raw' / (label + '.png')
        assert receipt == row['receipt'] and receipt['sha256'] == sha(path)
        assert all(receipt[k] for k in ('reliable', 'native_resolution', 'guarded_no_activation', 'background_safe', 'foreground_unchanged'))
        assert receipt['agent_activation_allowed'] is False and receipt['game_identity'] == report['session']['game_identity']
        assert row['before'] == row['after']
        cameras.append(row['before'])
        rasters[label] = png(path)
    assert all(camera == cameras[0] for camera in cameras)
    assert report['world_restore']['restored'] and all(row['after'] == {'name': 'minecraft:air', 'aux': 0} for row in report['world_restore']['rows'])
    assert all(report[k] is True for k in ('camera_restore', 'environment_restore', 'session_restore', 'projection_stop'))
    assert all(row['memory']['commit_available_bytes'] >= 6*1024**3 and row['handles']['status'] == 'live' and row['handles']['handle_count'] < 200000 for row in report['resource_boundaries'])
    ready, exits = load(package / 'lifecycle/launch-ready.json'), load(package / 'lifecycle/exact-process-exit.json')
    assert ready['exact_process_handles_retained'] and exits['completed'] and exits['session'] == SESSION
    for kind, code in (('game', '0xC0000409'), ('mcdk', '0x00000000')):
        row = exits['processes'][kind]
        assert row['state'] == 'exited' and row['exit_code_hex'] == code
        assert row['identity'] == ready[kind+'_identity'] and row['pid'] == ready[kind+'_pid']
    stop, final = load(package / 'lifecycle/ordinary-stop-returncode.json'), load(package / 'lifecycle/finalize-summary.json')
    assert stop == {'returncode': 1, 'force': False, 'ordinary_stop_request_count': 1}
    assert 'Game has not closed' in (package / 'lifecycle/ordinary-stop.stderr.txt').read_text(encoding='utf8')
    assert final['returncode'] == 0 and final['state'] == 'stopped' and final['ready'] is False and final['force'] is False
    assert final['finalize_after_both_exited'] and all(value is None for value in final['identities'].values())
    return {'verified_files': len(manifest['files']), 'png_filtered_raster_sha256': rasters, 'source_files': 3144, 'same_editor_and_document': True, 'world_only': True, 'normal_shutdown_qualified': False, 'ui_qualified': False, 'candidate_qualified': False, 'production_qualified': False}


def pack(output):
    assert not output.exists()
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    project = root / '.runtime/projects/book-r20-context-hidden-v1'
    frozen = here / 'context-hidden-v1/source-manifest.json'
    rows = load(frozen)['files']
    for row in rows:
        path = project / row['path']
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
    paths = {'replay.py': Path(__file__), 'frozen/source-manifest.json': frozen}
    runtime = here / 'runtime-context-hidden-v1'
    for name in ('report.json',) + tuple(label+suffix for label in FRAMES for suffix in ('.png', '.capture.json')):
        paths['raw/'+name] = runtime / name
    for name in ('probe_context_hidden_v1.py', 'launch_context_hidden_v1_amendment.py', 'launch_native_book_attached_v3_amendment.py'):
        paths['host/'+name] = here / name
    for name in ('prelaunch.json', 'launch-ready.json', 'exact-process-exit.json', 'ordinary-stop-returncode.json', 'ordinary-stop.stderr.txt', 'finalize-summary.json', 'independent-identity-absence.json'):
        paths['lifecycle/'+name] = here / 'context-hidden-v1-launch-amendment-v1' / name
    for name in ('.mcdev.json',) + tuple('behavior_pack/modern_projection/projection/'+name+'.py' for name in ('bridge', 'occupancy', 'occupancy_shader', 'render_context', 'world_projection')):
        paths['sources/'+name] = project / name
    for name, path in paths.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    save(output / 'visual-review.json', {'full_originals_opened_by': ['book_r20', 'root'], 'observed': 'Two cyan blocks; lower-only native; projected full; hidden with complete lower top and sides; shown restores upper and occludes shared top. Stone reference retained.', 'first_frame_background_loading_differs': True, 'quantitative_image_similarity_claimed': False, 'world_marker_only': True, 'lectern_book_scene_ui_qualified': False, 'production_qualified': False, 'normal_shutdown_qualified': False, 'full_frozen_source_rehashed_at_pack': 3144})
    (output / 'README.md').write_text('# Hidden-layer world marker controls\n\nRun `python -I -B replay.py --verify .` with Python 3 and the standard library.\nFive original PNGs and capture receipts, full raw report/restoration and frozen\nsource manifest are preserved. Both agents opened all five originals.\nThe first native frame retains background loading differences; no full-frame\nfit or numerical appearance equivalence is claimed. Replay validates recorded\nreceipts, PNG bytes/CRC/decompression, source binding, same editor/document,\ncontext indices, resources, restoration and exact process lifecycle.\nOnly the cyan world hide/show path is supported. Lectern/book/Scene/UI and\nproduction qualification remain open. One ordinary stop timed out; game\nexited 0xC0000409, MCDK exited 0, then metadata finalize succeeded. No force.\nRaw start/stop/finalize stdout containing session credentials is excluded.\n', encoding='ascii')
    (output / '.gitattributes').write_text('* -text -diff\n', encoding='ascii')
    save(output / 'manifest.json', {'schema': 1, 'files': {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(output.rglob('*')) if p.is_file()}})
    return replay(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pack', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    print(json.dumps(pack(args.pack) if args.pack else replay(args.verify), sort_keys=True))

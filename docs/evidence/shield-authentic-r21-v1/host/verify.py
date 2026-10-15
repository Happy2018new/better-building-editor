"""Verify authentic native-shield comparison records and unedited WGC images."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder):
    records = folder / 'records' if (folder / 'records').exists() else folder
    images = folder / 'images' if (folder / 'images').exists() else folder
    source = read(records / 'inputs.json')
    authentic = source['items']['authentic']
    assert authentic == source['authentic_raw']['item']
    assert authentic['userData']['Base'] == {'__type__': 3, '__value__': 4}
    assert authentic['userData']['Damage'] == {'__type__': 3, '__value__': 0}
    assert authentic['newAuxValue'] == 0 and source['userdata_copied_exactly']
    assert not source['production_qualified']
    calls = sorted(path for path in records.glob('[0-9][0-9]-*.json')
                   if not path.name.endswith('.capture.json'))
    assert len(calls) == 15
    for path in calls:
        row = read(path)
        assert hashlib.sha256(row['code'].encode('utf8')).hexdigest() == row['code_sha256'], path.name
        assert 'result' in row and 'error' not in row, path.name
    controls = read(records / '03-client-mount_native.json')['result']['controls']
    ui = {row['label']: row for row in controls if row['native_ui']}
    assert set(ui) == {'plain', 'authentic', 'sword'}
    assert all(row['returned'] for row in ui.values())
    assert ui['authentic']['payload'] == authentic
    bindings = read(records / '04-client-bind.json')['result']['bindings']
    assert len(bindings) == 3 and all(row['identity'] >= 0 and row['input_unmodified'] for row in bindings)
    bound = {row['label']: row for row in bindings}
    assert bound['authentic']['item'] == authentic
    assert all(row['rotation'] == [90., 0., 0.] and row['scale'] == 1. / 16. for row in bindings)
    first = read(records / 'first-complete.json')
    assert len(first['images']) == 2 and first['visual_review_pending']
    gate = read(records / 'remaining-started.json')
    assert gate['first_two_visually_reviewed'] and gate['native_positive_accepted']
    remaining = read(records / 'remaining-complete.json')
    assert len(remaining['images']) == 7 and not remaining['production_qualified']
    assert not remaining['workspace_common_depth_tested']
    frames = read(records / '08-server-frames.json')['result']
    assert frames['inventory_restored'] and len(frames['frames']) == 2
    assert frames['frames'][1]['label'] == 'authentic'
    assert frames['frames'][1]['nbt']['Item']['tag'] == authentic['userData']
    for row in frames['frames']:
        assert row['nbt']['ItemRotation']['__value__'] == 0.
    client = read(records / '14-client-restore.json')['result']
    assert all(client[key] for key in ('restored', 'editor_restored', 'controls_removed',
                                      'workspace_restored', 'bindings_removed'))
    for key in ('position', 'rotation'):
        assert max(abs(a - b) for a, b in zip(client['camera_before'][key], client['camera_after'][key])) < .05
    assert client['camera_before']['fov'] == client['camera_after']['fov']
    server = read(records / '15-server-restore.json')['result']
    assert all(server[key] for key in ('restored', 'inventory_restored', 'selected_restored', 'actors_removed'))
    assert server['guard_cells_restored'] == 96 and server['foot_before'] == server['foot_after']
    assert not server['removed_fixture_drops']
    assert read(records / 'remaining-restoration.json') == {'success': True, 'errors': []}
    assert read(records / 'remaining-source-final.json') == {'unchanged': True}
    for row in first['images'] + remaining['images']:
        path = images / row['image']
        receipt = read(records / path.with_suffix('.capture.json').name)
        assert sha(path) == row['sha256'] == receipt['sha256']
        assert receipt['ok'] and receipt['reliable'] and receipt['native_resolution']
        assert receipt['owner'] == 'shield-r20-v7-authentic'
        assert receipt['game_pid'] == 39728 and receipt['game_identity'] == '134365633584760870'
        assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
        assert not receipt['agent_activation_allowed'] and not receipt['activation_fallback']
        assert receipt['guard_before']['window_noactivate'] and receipt['guard_after']['window_noactivate']
        with Image.open(path) as picture:
            assert picture.size == (receipt['width'], receipt['height']) == (1994, 1105)
    with Image.open(images / '01-native-ui-unbound.png') as picture:
        pixels = list(picture.convert('RGB').crop((940, 90, 1060, 315)).getdata())
        ui_white = sum(min(color) > 160 and max(color) - min(color) < 25 for color in pixels)
        ui_blue = sum(b > 35 and b > r * 1.5 and b > g * 1.2 for r, g, b in pixels)
    with Image.open(images / '04-bound-back.png') as picture:
        pixels = list(picture.convert('RGB').crop((865, 533, 931, 563)).getdata())
        bone_blue = sum(b > 35 and b > r * 1.5 and b > g * 1.2 for r, g, b in pixels)
    assert ui_white > 3000 and bone_blue > 200 and ui_blue == 0
    exact = read(records / 'exact-exit.json')
    assert exact['completed'] and not exact['process_or_window_mutation']
    assert exact['processes']['game']['exit_code'] == 0xC0000409
    assert exact['processes']['mcdk']['exit_code'] == 0
    for path in records.glob('stop-[0-9][0-9].json'):
        assert not read(path)['forced']
    manifest_path = folder / 'manifest.json'
    if manifest_path.exists():
        manifest = read(manifest_path)
        files = {path.relative_to(folder).as_posix(): path for path in folder.rglob('*')
                 if path.is_file() and path != manifest_path}
        assert set(files) == set(manifest['files'])
        for name, path in files.items():
            assert sha(path) == manifest['files'][name]['sha256'], name
            assert path.stat().st_size == manifest['files'][name]['bytes'], name
    return {'verified': True, 'native_userdata_exact': True, 'bound_native_shield_positive': True,
        'native_ui_white_pixels': ui_white, 'native_ui_blue_pixels': ui_blue,
        'bone_blue_pixels': bone_blue, 'native_ui_base_matches_bone': False,
        'native_frame_pattern_front_accepted': False, 'unedited_wgc_images': 9,
        'execute_code_records': 15, 'guard_cells_restored': 96,
        'game_exit': '0xC0000409', 'mcdk_exit': 0, 'normal_lifecycle_accepted': False,
        'workspace_common_depth_accepted': False, 'banner_item_shape_accepted': False,
        'production_qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    print(json.dumps(verify(parser.parse_args().folder)))

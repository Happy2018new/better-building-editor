"""Portable offline replay of the bounded portal v12 evidence package."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zipfile
import zlib

os.environ['OPENBLAS_NUM_THREADS'] = '1'
EXPECTED_DIGEST = 'a568dddc531e7eea610d24f18b12369adddb6de081105f52834611d7f8217918'
EXPECTED_COMMIT = 'fc5d70252fe4105c53f3ac13e8338ffd8f9e0c33'
OWNER = 'portal-r21-native-candidate-v12'
LABELS = tuple(family + '_' + route for family in ('end_gateway', 'end_portal')
               for route in ('editor', 'full', 'missing'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def snapshot_digest(files):
    return sha(json.dumps(files, sort_keys=True, separators=(',', ':')).encode('ascii'))


def png_rgb(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed, size, channels = 8, bytearray(), None, None
    while offset < len(data):
        length = struct.unpack_from('>I', data, offset)[0]
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        expected = struct.unpack_from('>I', data, offset + 8 + length)[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == expected, (path.name, kind)
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            assert depth == 8 and color in (2, 6) and (compression, filtering, interlace) == (0, 0, 0)
            size, channels = (width, height), 3 if color == 2 else 4
        elif kind == b'IDAT':
            compressed.extend(payload)
        offset += length + 12
        if kind == b'IEND':
            break
    assert offset == len(data) and size is not None
    stride = size[0] * channels
    decoded = zlib.decompress(compressed)
    assert len(decoded) == (stride + 1) * size[1]
    rows, previous = [], bytearray(stride)
    for y in range(size[1]):
        start = y * (stride + 1)
        filter_type, row = decoded[start], bytearray(decoded[start + 1:start + 1 + stride])
        assert filter_type <= 4
        if filter_type:
            for x in range(stride):
                a, b = row[x - channels] if x >= channels else 0, previous[x]
                c = previous[x - channels] if x >= channels else 0
                if filter_type == 1:
                    predictor = a
                elif filter_type == 2:
                    predictor = b
                elif filter_type == 3:
                    predictor = (a + b) // 2
                else:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    predictor = a if pa <= pb and pa <= pc else b if pb <= pc else c
                row[x] = (row[x] + predictor) & 255
        rows.append(row)
        previous = row
    return size, channels, rows


def visibility(rows, channels, mask):
    count, dark, cyan, white, totals = 0, 0, 0, 0, [0, 0, 0]
    for y, start, end in mask['row_runs']:
        row = rows[y]
        for x in range(start, end):
            rgb = row[x * channels:x * channels + 3]
            maximum, minimum = max(rgb), min(rgb)
            is_dark = maximum < 95
            count += 1
            dark += is_dark
            cyan += is_dark and maximum - minimum > 8 and rgb[1] > rgb[0] + 4 and rgb[2] > rgb[0] + 4
            white += minimum > 240
            for axis in range(3):
                totals[axis] += rgb[axis]
    return {'dark_pixels': dark, 'colored_dark_pixels': cyan, 'interior_pixels': count,
            'face': mask['face'], 'dark_ratio': dark / count, 'colored_dark_ratio': cyan / count,
            'white_ratio': white / count, 'mean_rgb': [value / count for value in totals],
            'visible': dark / count > .65 and cyan / count > .005 and white / count < .02}


def placeholders(value):
    if isinstance(value, dict):
        return ('__repr__' in value and '__type__' in value) or any(map(placeholders, value.values()))
    return isinstance(value, list) and any(map(placeholders, value))


def calls(path):
    with zipfile.ZipFile(path) as archive:
        return {name: json.loads(archive.read(name)) for name in archive.namelist()}


def document_from_request(request):
    tree = ast.parse(request['code'])
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'json'
                and node.func.attr == 'loads' and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            value = json.loads(node.args[0].value)
            if isinstance(value, dict) and 'chunks' in value and 'palette' in value:
                return value
    return None


def verify(package, frozen_project=None):
    manifest = load(package / 'manifest.json')
    actual_files = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    assert actual_files == set(manifest['files']) | {'manifest.json'}
    for relative, expected in manifest['files'].items():
        data = (package / relative).read_bytes()
        assert sha(data) == expected['sha256'] and len(data) == expected['bytes'], relative
    binding = load(package / 'source-binding.json')
    assert binding['source_commit'] == EXPECTED_COMMIT
    frozen = load(package / 'control/launch-inputs.json')['files']
    assert len(frozen) == 3692 and snapshot_digest(frozen) == EXPECTED_DIGEST
    assert binding['source_contract_sha256'] == EXPECTED_DIGEST
    for relative, expected in binding['included_frozen_sources'].items():
        assert sha((package / 'source/project' / relative).read_bytes()) == expected == frozen[relative]
    for relative, expected in binding['commit_files'].items():
        assert sha((package / 'source/commit' / relative).read_bytes()) == expected
    actual_differences = {}
    for relative, expected in binding['selected_runtime_files'].items():
        data = (package / 'source/project' / relative).read_bytes()
        assert sha(data) == expected
        commit_data = (package / 'source/commit' / relative).read_bytes()
        if sha(data) != sha(commit_data):
            actual_differences[relative] = {'commit_sha256': sha(commit_data), 'runtime_sha256': sha(data),
                'equal_after_crlf_normalization': data.replace(b'\r\n', b'\n') == commit_data.replace(b'\r\n', b'\n')}
    assert actual_differences == binding['commit_runtime_byte_differences']
    assert len(binding['commit_files']) == 17
    aliases = ('modern_projection_portal_native_end_gateway', 'modern_projection_portal_native_end_gateway_world',
               'modern_projection_portal_native_end_portal', 'modern_projection_portal_native_end_portal_world')
    runtime_materials = load(package / 'source/project/resource_pack/materials/entity.material')['materials']
    commit_materials = load(package / 'source/commit/resource_pack/materials/entity.material')['materials']
    runtime_models = load(package / 'source/project/resource_pack/models/netease_models.json')
    commit_models = load(package / 'source/commit/resource_pack/models/netease_models.json')
    for alias in aliases:
        assert runtime_materials[alias + ':entity_for_skeleton_alpha'] == commit_materials[alias + ':entity_for_skeleton_alpha']
        assert runtime_models[alias] == commit_models[alias]
    for relative in binding['commit_files']:
        if ('/shaders/glsl/' in relative or '/models/modern_projection/portal/' in relative
                or '/textures/models/modern_projection/portal/' in relative):
            assert (package / 'source/project' / relative).read_bytes() == (package / 'source/commit' / relative).read_bytes()
    config_path = package / 'source/project/.mcdev.json'
    prepared = load(package / 'control/prepared-summary.json')
    assert sha(config_path.read_bytes()) == prepared['config_sha256']
    config = load(config_path)
    assert all(config[key] is False for key in ('auto_hot_reload_materials', 'auto_hot_reload_mods',
                                               'auto_hot_reload_shaders', 'auto_hot_reload_ui'))
    assert not prepared['native_gate'] and not prepared['old_default_profile_changed']
    assert prepared['source_contract_sha256'] == EXPECTED_DIGEST
    assert prepared['source_count'] == 3692 and prepared['normal_time']
    if frozen_project is not None:
        paths = [p for folder in ('behavior_pack', 'resource_pack') for p in (frozen_project / folder).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')]
        paths += list((frozen_project / 'tools').glob('*.py'))
        paths += list((frozen_project / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
        actual = {p.relative_to(frozen_project).as_posix(): sha(p.read_bytes()) for p in paths}
        assert actual == frozen and snapshot_digest(actual) == EXPECTED_DIGEST
        assert sha((frozen_project / '.mcdev.json').read_bytes()) == prepared['config_sha256']
    dependency = load(package / 'control/host-dependency-amendment.json')
    for relative, expected in dependency['files'].items():
        assert sha((package / 'source/host-dependencies' / relative).read_bytes()) == expected
    assert sha((package / 'source/hosts/portal_native_candidate_host_r21_v12.py').read_bytes()) == dependency['original_host_sha256']
    assert sha((package / 'source/hosts/run_portal_v12_frozen_host_dependencies.py').read_bytes()) == dependency['runner_sha256']
    amendment = load(package / 'control/json-readback-host-amendment.json')
    assert sha((package / 'source/hosts/run_portal_v12_json_readback_amendment.py').read_bytes()) == amendment['runner_sha256']
    assert amendment['last_six_image_attempt_in_this_session'] and not amendment['native_gate']
    imported = load(package / 'control/json-readback-validate-import.json')
    assert imported['rpc_calls_at_import'] == imported['wgc_calls_at_import'] == 0
    assert not imported['unfrozen_live_root_tools_imported'] and not imported['qualification']
    assert len(imported['offline_fixtures']) == 2
    assert all(row['complete_document_equal'] and not row['transport_placeholders'] for row in imported['offline_fixtures'])
    for receipt_name in ('amended-validate-import.json', 'amended-capture-import.json',
                         'json-readback-validate-import.json', 'json-readback-capture-import.json'):
        for relative, expected in load(package / 'control' / receipt_name)['loaded_host_sources'].items():
            if relative.startswith('.runtime/projects/portal-r21-native-candidate-v12/'):
                target = package / 'source/project' / relative.split('portal-r21-native-candidate-v12/', 1)[1]
            else:
                assert relative.startswith('.runtime/portal-native-candidate-host-dependencies-r21-v12/')
                target = package / 'source/host-dependencies' / relative.split('host-dependencies-r21-v12/', 1)[1]
            assert sha(target.read_bytes()) == expected, relative
    original_error = (package / 'attempts/import/capture.stderr.txt').read_text(encoding='utf8')
    assert 'analyze_intrinsic_glint_ui_r21' in original_error and 'ModuleNotFoundError' in original_error
    failed = load(package / 'attempts/transport/report.json')
    assert not failed['completed'] and not failed['captures'] and failed['restored'] and failed['source_unchanged']
    assert not failed['cleanup_errors'] and placeholders(failed['rows']['end_gateway']['load']['source'])
    failed_calls = calls(package / 'attempts/transport/calls.zip')
    assert len([name for name in failed_calls if name.endswith('-request.json')]) == 12
    report = load(package / 'observed/report.json')
    review = load(package / 'observed/runtime-review.json')
    assert all(report[key] for key in ('completed', 'restored', 'source_unchanged', 'normal_time'))
    assert not report['cleanup_errors'] and not report['qualification'] and not report['pixel_acceptance']
    assert report['source_contract_sha256'] == review['source_contract_sha256'] == EXPECTED_DIGEST
    assert report['owner'] == OWNER and set(report['captures']) == set(LABELS)
    assert report['memory_metric'] == 'CommitLimit-CommitTotal' and not report['physical_memory_is_a_gate']
    boundaries = report['memory_boundaries']
    assert len(boundaries) == 144
    for row in boundaries:
        assert row['commit_available_bytes'] == row['commit_limit_bytes'] - row['commit_total_bytes']
        assert row['passed'] and row['commit_available_bytes'] >= 6 * 1024 ** 3
    assert min(row['commit_available_bytes'] for row in boundaries) == 6785515520
    assert report['player_before']['foot'] == report['player_restore']['foot']
    assert all(row['actual']['name'] == 'minecraft:air' for row in report['player_restore']['platforms'])
    success_calls = calls(package / 'observed/calls.zip')
    documents = []
    for name, request in success_calls.items():
        if not name.endswith('-request.json'):
            continue
        document = document_from_request(request)
        if document is not None:
            result = success_calls[name.replace('-request.json', '-result.json')]
            assert document == result['source'] and not placeholders(result['source'])
            assert request['code'].endswith('_result=json.dumps(_result)\n')
            documents.append(document)
    assert len(documents) == 2
    for family, document in zip(('end_gateway', 'end_portal'), documents):
        assert report['rows'][family]['load']['source'] == document
    masks = load(package / 'observed/pixel-masks.json')
    verified_pixels = {}
    ready = load(package / 'control/ready-summary.json')
    for label in LABELS:
        entry = report['captures'][label]
        receipt = load(package / 'observed' / (label + '.capture.json'))
        assert receipt == entry['capture']
        assert all(receipt[key] for key in ('ok', 'reliable', 'foreground_unchanged', 'native_resolution'))
        assert receipt['backend'] == 'Windows.Graphics.Capture'
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert str(receipt['game_identity']) == ready['game_identity'] and receipt['game_pid'] == ready['game_pid']
        assert receipt['owner'] == OWNER
        before, after = entry['before'], entry['after']
        assert all(before[key] == after[key] for key in ('camera', 'rotation', 'screen', 'editor_camera', 'editor_depth'))
        image_path = package / 'observed' / (label + '.png')
        assert sha(image_path.read_bytes()) == review['images'][label]['sha256']
        assert sha((package / 'observed' / (label + '.capture.json')).read_bytes()) == review['images'][label]['capture_receipt_sha256']
        size, channels, rows = png_rgb(image_path)
        assert list(size) == review['images'][label]['size'] == [1994, 1105]
        if label in masks['images']:
            measured = visibility(rows, channels, masks['images'][label])
            assert measured == entry['visibility'] and measured['visible'], label
            verified_pixels[label] = measured
    watcher = load(package / 'control/watcher-before-capture.json')
    assert watcher['read_error_preserved'] and watcher['watcher_errors_cumulative_in_source']
    assert watcher['subsequent_exact_session_coverage_observed']
    for sample in watcher['samples']:
        assert sample['errors'] and any('[Errno 13]' in error for error in sample['errors'])
        assert sample['host_sha256'] == binding['watcher_source_sha256']
        assert not sample['other_assertions'] and not sample['known_assert_recoveries']
        assert any(row['id'] == watcher['session'] and row['game_pid'] == ready['game_pid'] for row in sample['eligible_sessions'])
    preserved_watcher = load(package / 'control/watcher-after-exit-status.json')
    assert preserved_watcher['errors'] and any('[Errno 13]' in error for error in preserved_watcher['errors'])
    assert not preserved_watcher['eligible_sessions']
    invalid = load(package / 'control/normal-close-result.json')
    valid = load(package / 'control/actual-normal-close-result.json')
    assert invalid['returncode'] == 2 and invalid['normal_close_request_count'] == 0
    assert invalid['cli_validation_failed_before_operation'] and not invalid['force_used']
    assert 'unrecognized arguments: --wait 60' in (package / 'control/normal-close.stderr.txt').read_text(encoding='utf8')
    assert valid['returncode'] == 1 and valid['normal_close_request_count'] == 1 and not valid['force_used']
    exit_receipt = load(package / 'control/exact-exit-observation.json')
    assert exit_receipt['completed'] and not exit_receipt['process_or_window_mutation']
    for kind in ('game', 'mcdk'):
        process = exit_receipt['processes'][kind]
        assert process['state'] == 'exited' and str(process['identity']) == ready[kind + '_identity']
        assert process['pid'] == ready[kind + '_pid']
    assert exit_receipt['processes']['game']['exit_code_hex'] == '0xC0000409'
    assert exit_receipt['processes']['mcdk']['exit_code_hex'] == '0x00000000'
    finalized = load(package / 'control/finalize-summary.json')
    assert finalized['returncode'] == 0 and finalized['state'] == 'stopped' and not finalized['ready']
    assert finalized['both_exact_identities_absent_before_finalize'] and finalized['runtime_released']
    assert finalized['normal_close_request_count'] == 1 and not finalized['force_used']
    assert not finalized['normal_exit_accepted'] and finalized['game_exit_code'] == '0xC0000409'
    compile_report = load(package / 'control/compile.json')
    axes_report = load(package / 'control/ui-axes.json')
    assert compile_report['passed'] and len(compile_report['cases']) == 16
    for name, expected in compile_report['source_sha256'].items():
        assert sha((package / 'source/project/resource_pack/shaders/glsl' / name).read_bytes()) == expected
    assert axes_report['result']['passed'] and axes_report['result']['fixtures'] == 816
    assert not axes_report['native_ui_matrix_bindings_observed'] and not axes_report['qualification']
    assert axes_report['shader_sha256'] == compile_report['source_sha256']['modern_projection_portal_native_ui.vertex']
    return {'verified': True, 'portable': True, 'source_commit': EXPECTED_COMMIT,
            'source_contract_sha256': EXPECTED_DIGEST, 'frozen_manifest_entries': len(frozen),
            'actual_frozen_project_bytes_verified': frozen_project is not None,
            'included_frozen_source_files': len(binding['included_frozen_sources']),
            'manifest_files': len(manifest['files']), 'six_original_pngs_verified': True,
            'world_pixel_measurements_recomputed': verified_pixels,
            'failed_attempts_preserved': 2, 'watcher_startup_errno13_preserved': True,
            'normal_close_operations': 1, 'normal_game_exit_accepted': False,
            'qualification': False, 'native_default_enabled': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--frozen-project', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.verify.resolve(), args.frozen_project), indent=2))


if __name__ == '__main__':
    main()

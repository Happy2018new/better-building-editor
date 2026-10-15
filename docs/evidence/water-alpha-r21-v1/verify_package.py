"""Verify or independently replay the preserved single-launch alpha controls."""
import argparse
import ast
from collections import deque
from configparser import ConfigParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys
import tempfile
from types import ModuleType

ROOT = Path(__file__).resolve().parent
CONTRACT = 'cb2b32de68b69f435d69b59cf296d8492d88984ddb96e10f020d7fdbd0aef806'
CASES = ['wet_oak_fence', 'wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs']
ADMISSIONS = ('native_shape_accepted', 'native_uv_accepted', 'native_alpha_accepted', 'product_style_accepted')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def local_frame(frame, group):
    return ROOT / 'captures' / group / PureWindowsPath(frame['path']).name


def commit_gate(state, minimum):
    assert state['passed'] is True and state['minimum_commit_gib'] == minimum
    commit = state['commit']
    assert commit['commit_available_bytes'] == commit['commit_limit_bytes'] - commit['commit_total_bytes']
    assert commit['commit_available_bytes'] >= minimum * 1024 ** 3


def verify_frames(frames, group, binding, capture_sha):
    for label, frame in frames.items():
        path = local_frame(frame, group)
        receipt = read(path.with_suffix('.capture.json'))
        assert sha(path) == frame['sha256'] == receipt['sha256'], label
        assert path.stat().st_size == frame['bytes'] == receipt['bytes']
        for key, value in receipt.items():
            assert frame[key] == value, (label, key)
        assert receipt['schema'] == 3 and receipt['ok'] is True and receipt['reliable'] is True
        assert receipt['background_safe'] is True and receipt['foreground_unchanged'] is True
        assert receipt['foreground_before'] == receipt['foreground_after']
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['guarded_no_activation'] is True and receipt['noactivation_requested'] is True
        assert all(receipt[key]['window_noactivate'] is True for key in ('guard_before', 'guard_after'))
        assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
        assert receipt['helper']['sha256'] == capture_sha
        assert [receipt['width'], receipt['height']] == [1994, 1105]
        for key in ('owner', 'game_pid', 'game_identity', 'session_file'):
            assert receipt[key] == binding[key], (label, key)


def pure_nodes(path, functions):
    tree = ast.parse(path.read_bytes(), filename=str(path))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
    assert {node.name for node in nodes} == set(functions)
    assert all(not node.decorator_list for node in nodes)
    return nodes


def load_stone_helpers():
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    shared = {'Image': Image, 'ImageChops': ImageChops, 'ImageDraw': ImageDraw,
              'ImageFilter': ImageFilter, 'deque': deque}
    # Compile the original pure function nodes without importing live-host globals.
    helpers = read(ROOT / 'code-bindings.json')['pure_helper_files']
    for name in ('verify_missing_neighbor_visuals', 'verify_camera_projection'):
        helper = helpers[name]
        path, functions = ROOT / helper['path'], helper['functions']
        nodes = pure_nodes(path, functions)
        module = ModuleType(name)
        module.__file__ = str(path)
        module.__dict__.update(shared)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), module.__dict__)
        sys.modules[name] = module
        shared.update({function: module.__dict__[function] for function in functions})


def replay(source, calibration, results):
    with tempfile.TemporaryDirectory(prefix='water-alpha-r21-replay-') as directory:
        temporary = Path(directory)
        for view in calibration['views']:
            for state in ('shown', 'hidden'):
                view[state]['path'] = str(local_frame(view[state], 'calibration'))
        rebased_calibration = temporary / 'calibration.json'
        rebased_calibration.write_text(json.dumps(calibration), encoding='ascii')
        for frame in source['captures'].values():
            frame['path'] = str(local_frame(frame, 'full'))
        source['camera_calibration'].update(path=str(rebased_calibration), sha256=sha(rebased_calibration))
        rebased_source = temporary / 'source.json'
        rebased_source.write_text(json.dumps(source), encoding='ascii')
        sys.path.insert(0, str(ROOT / 'replay/tools'))
        import numpy as np
        import analyze_liquid_workspace as workspace
        import analyze_product_water as product
        load_stone_helpers()
        original_rgb, cache = product.rgb, {}

        def decoded_rgb(path):
            key = str(Path(path).resolve(strict=True))
            if key not in cache:
                target = temporary / ('decoded-%d.npy' % len(cache))
                np.save(target, original_rgb(path), allow_pickle=False)
                cache[key] = target
            return np.load(cache[key], mmap_mode='r', allow_pickle=False)

        product.rgb = workspace.rgb = decoded_rgb
        try:
            measured = {'original': product.analyze(rebased_source),
                        'native': product.analyze(rebased_source, native_world_geometry=True)}
        finally:
            product.rgb = workspace.rgb = original_rgb
        for mode, result in measured.items():
            for key in ('evidence_valid', 'capture_failures', 'limits', 'geometry', 'transparency',
                        'animation', 'alpha_controls', 'observed_product_gates') + ADMISSIONS:
                assert result[key] == results[mode][key], (mode, key)
        assert measured['native']['geometry_oracle']['model'] == results['native']['geometry_oracle']['model']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest = read(ROOT / 'manifest.json')
    assert manifest['diagnostic_only'] is True and manifest['production_qualified'] is False
    assert manifest['standalone_offline_replay'] is True
    assert manifest['capture_host_suspensions'] == manifest['game_suspensions'] == manifest['window_actions'] == []
    assert manifest['complete_launch_source_archive_included'] is False
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes'], name
        assert sha(path) == expected['sha256'], name
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files'])
    plan, bindings = read(ROOT / 'plan.json'), read(ROOT / 'code-bindings.json')
    assert read(ROOT / 'plan-receipt.json')['plan_sha256'] == sha(ROOT / 'plan.json')
    assert plan['owner'] == 'water-r21-alpha-v1' and plan['production_qualified'] is False
    assert plan['source_contract_sha256'] == CONTRACT
    assert plan['launch_inputs_sha256'] == sha(ROOT / 'launch-inputs.json')
    assert plan['launch_config_sha256'] == sha(ROOT / 'launch-mcdev.json')
    for original, packaged in bindings['frozen_host_files'].items():
        assert sha(ROOT / packaged) == plan['host_files_sha256'][original], original
    launch = read(ROOT / 'launch-inputs.json')
    sources = launch['source_sha256']
    assert len(sources) == manifest['source_receipts_files'] == 3093
    contract = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
    assert contract == CONTRACT == launch['source_contract_sha256']
    for packaged, original in bindings['launch_bound_files'].items():
        assert sha(ROOT / packaged) == sources[original], original
    for name, helper in bindings['pure_helper_files'].items():
        actual, launched = (pure_nodes(ROOT / helper[key], helper['functions']) for key in ('path', 'launch_path'))
        assert {node.name: ast.dump(node) for node in actual} == {node.name: ast.dump(node) for node in launched}, name
    config = read(ROOT / 'launch-mcdev.json')
    assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                               'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    attempt = read(ROOT / 'launch-attempt.json')
    assert attempt['one_use'] is True and attempt['plan_sha256'] == sha(ROOT / 'plan.json')
    commit_gate(attempt['preflight'], 9.)
    assert attempt['preflight']['games'] == attempt['preflight']['same_project_live'] == []
    for name in ('after-launch.json', 'calibration-preflight-1.json', 'full-alpha4-preflight-1.json'):
        commit_gate(read(ROOT / name), 6.)
    start = read(ROOT / 'start.json')
    assert start['ready'] is True and start['state'] == 'ready'
    launch_execution = read(ROOT / 'launch-execution.json')
    assert launch_execution['returncode'] == 0 and json.loads(launch_execution['stdout']) == start
    source, calibration = read(ROOT / 'full-alpha4.json'), read(ROOT / 'calibration.json')
    binding = source['session_binding']
    for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file'):
        assert start[key] == binding[key], key
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert source['cleanup_errors'] == [] and source['routes'] == manifest['routes'] == ['full']
    assert source['cases'] == manifest['cases'] == CASES
    assert len(source['captures']) == manifest['captures']['full'] == 56 and len(source['rows']) == 24
    assert source['source_contract_sha256'] == CONTRACT
    assert source['launch_source_sha256'] == source['source_file_sha256_before'] == source['source_file_sha256_after'] == sources
    assert source['frozen'] is True and source['alpha_controls_requested'] is True
    assert source['visibility_controls_requested'] is True and not source['flow_bursts']
    assert not source['production_default_requested'] and all(source[key] is False for key in ADMISSIONS)
    assert source['camera_calibration']['sha256'] == sha(ROOT / 'calibration.json')
    assert all(calibration[key] is True for key in ('passed', 'completed', 'restored',
        'environment_restored', 'capture_options_restored', 'projection_restored',
        'camera_restored', 'visual_restored', 'editor_restored'))
    assert calibration['cleanup_errors'] == []
    assert calibration['native_projection']['session_binding'] == binding
    assert calibration['native_projection']['source_contract_sha256'] == CONTRACT
    calibration_frames = {view['view'] + '_' + state: view[state]
                          for view in calibration['views'] for state in ('shown', 'hidden')}
    assert len(calibration_frames) == manifest['captures']['calibration'] == 6
    capture_sha = plan['host_files_sha256'][next(name for name in plan['host_files_sha256'] if name.endswith('native_wgc_capture.exe'))]
    verify_frames(source['captures'], 'full', binding, capture_sha)
    verify_frames(calibration_frames, 'calibration', binding, capture_sha)
    for name in ('calibration', 'full-alpha4'):
        execution, restored = read(ROOT / (name + '-execution.json')), read(ROOT / (name + '-restored.json'))
        assert execution['returncode'] == 0 and execution['stderr'] == ''
        assert restored['completed'] is True and restored['restored'] is True
        assert restored['report_sha256'] == sha(ROOT / (name + '.json'))
        assert restored['source_contract_sha256'] == CONTRACT and restored['minimum_runtime_commit_met'] is True
        commit_gate({'passed': True, 'minimum_commit_gib': 6., 'commit': restored['commit']}, 6.)
    execution = read(ROOT / 'full-alpha4-execution.json')
    for option, value in (('--max-handles', '210000'), ('--max-seconds', '600'), ('--route', 'full')):
        assert execution['argv'][execution['argv'].index(option) + 1] == value
    assert '--alpha-controls' in execution['argv'] and '--frozen' in execution['argv']
    results = {mode: read(ROOT / ('full-alpha4-' + mode + '-analysis.json')) for mode in ('original', 'native')}
    for result in results.values():
        assert result['source_sha256'] == sha(ROOT / 'full-alpha4.json')
        assert result['analyzer_sha256'] == sha(ROOT / 'replay/tools/analyze_product_water.py')
        assert result['evidence_valid'] is True and result['capture_failures'] == []
        assert result['production_qualified'] is False and result['diagnostic_only'] is True
        assert all(result[key] is False for key in ADMISSIONS)
        assert result['geometry'] == result['animation'] == {}
        assert result['observed_product_gates'] == {'geometry': False, 'transparency': True, 'animation': False}
        assert len(result['alpha_controls']) == 4
        for row in result['alpha_controls'].values():
            assert row['complete'] is True and row['passed'] is True and row['geometry_unchanged'] is True
            for region in row['regions'].values():
                assert region['default_rgb_rmse'] == 0. and region['passed'] is True
    native = results['native']['geometry_oracle']
    assert native['helper_sha256'] == sha(ROOT / 'replay/tools/water_native_projection.py')
    assert native['calibration_sha256'] == sha(ROOT / 'calibration.json')
    assert native['model']['session_binding'] == binding and native['model']['source_contract_sha256'] == CONTRACT
    review = read(ROOT / 'full-alpha4-review.json')
    assert review['source_sha256'] == sha(ROOT / 'full-alpha4.json')
    assert review['evidence_valid'] is True and review['restored'] is True
    assert review['production_qualified'] is False and review['automatic_missing_route'] is False
    assert review['alpha_controls'] == {mode: {key: row['passed'] for key, row in result['alpha_controls'].items()}
                                        for mode, result in results.items()}
    first, second = (read(ROOT / ('stop-attempt-%d-execution.json' % attempt)) for attempt in (1, 2))
    assert first['returncode'] == 1 and 'Game has not closed' in first['stderr']
    assert second['returncode'] == 0 and second['stderr'] == ''
    assert all('--force' not in stop['argv'] for stop in (first, second))
    stopped = json.loads(second['stdout'])
    assert stopped['state'] == 'stopped' and stopped['ready'] is False
    observer = read(ROOT / 'exit-observer.json')
    assert observer['completed'] is True and observer['process_or_window_mutation'] is False
    assert observer['session'] == binding['id'] and observer['owner'] == binding['owner']
    for kind, code in (('game', 0xC0000409), ('mcdk', 0)):
        row = observer['processes'][kind]
        assert row['pid'] == stopped[kind + '_pid'] == start[kind + '_pid']
        assert row['identity'] == stopped[kind + '_identity'] == start[kind + '_identity']
        assert row['state'] == 'exited' and row['exit_code'] == code
        assert row['exit_code_hex'] == '0x%08X' % code
    wer = ConfigParser(interpolation=None, strict=False, delimiters=('=',))
    wer.optionxform = str
    wer.read_string('[report]\n' + (ROOT / 'exit-Report.wer').read_text(encoding='utf-16'))
    event = wer['report']
    assert event['EventType'] == 'BEX64' and event['Sig[3].Value'] == 'ucrtbase.dll'
    assert event['Sig[7].Value'] == 'c0000409'
    assert event['ReportIdentifier'] == '708c5be0-5432-4b23-a21a-1c0abf287e7d'
    assert int(event['AppSessionGuid'].split('-')[0], 16) == binding['game_pid']
    exited = datetime.fromisoformat(observer['processes']['game']['observed_at']).astimezone(timezone.utc)
    event_seconds = (int(event['EventTime']) - 116444736000000000) / 10000000.
    assert int(binding['game_identity']) < int(event['EventTime']) and 0 <= exited.timestamp() - event_seconds < 60
    if args.pixels:
        replay(source, calibration, results)
    maxima = {mode: max(phase['endpoint_rgb_rmse'] for row in result['alpha_controls'].values()
                       for region in row['regions'].values() for phase in region['phases'].values())
              for mode, result in results.items()}
    print(json.dumps({'verified': True, 'pixels_replayed': args.pixels, 'captures': manifest['captures'],
        'source_receipt_files': len(sources), 'alpha_passes': {mode: len(result['alpha_controls']) for mode, result in results.items()},
        'maximum_endpoint_rgb_rmse': maxima, 'default_vs_045_rgb_rmse': 0.,
        'exact_exit_codes': {kind: row['exit_code_hex'] for kind, row in observer['processes'].items()},
        'production_qualified': False}))


if __name__ == '__main__':
    main()

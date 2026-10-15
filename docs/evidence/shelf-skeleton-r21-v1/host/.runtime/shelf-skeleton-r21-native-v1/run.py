"""Prepare and control the single owned shelf skeleton candidate; no automatic launch."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
CONTROL = Path(__file__).resolve().parent
PROJECT = ROOT/'.runtime/projects/shelf-r21-skeleton-world-v1'
ASSETS = ROOT/'.runtime/shelf-skeleton-r21-v1'
OWNER = 'root-shelf-r20-skeleton-world-v1'
SCRIPTS = ROOT/'.agents/skills/pyreact-debugging/scripts'
sys.path[:0] = [str(SCRIPTS), str(ROOT/'tools')]
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from freeze_intrinsic_glint_project_r21 import fingerprint
from generate_liquid_product_resources import merge_registry
from _session import load_session, process_identity
import instances


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2)+'\n', encoding='ascii')


def generic_launcher():
    spec = importlib.util.spec_from_file_location('shelf_frozen_launcher', ROOT/'.runtime/start_shelf_baked_r21.py')
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    launcher.PROJECT, launcher.OUTPUT, launcher.OWNER = PROJECT, CONTROL/'launch', OWNER
    return launcher


def host_sources():
    names = ['tools/probe_shelf_skeleton_world_r21.py', 'tools/probe_liquid_pose_channel.py',
        'tools/probe_native_palette_body_r16.py', 'tools/probe_shelf_body_matrix_r20.py',
        'tools/probe_shelf_native_shape_r17.py', 'tools/probe_product_water.py',
        'tools/context_test_environment.py', 'tools/capture_native_window.py',
        'tools/diagnose_window_dpi.py', 'tools/census_intrinsic_glint_ui_r21.py',
        'tools/watch_intrinsic_glint_exit_r21.py', 'tools/freeze_intrinsic_glint_project_r21.py',
        '.runtime/start_shelf_baked_r21.py']
    names.extend('.agents/skills/pyreact-debugging/scripts/'+name for name in
                 ('instances.py', '_session.py', '_window.py', 'mcdk.py'))
    names.append(Path(__file__).relative_to(ROOT).as_posix())
    return {name: sha(ROOT/name) for name in names}


def prepare():
    if PROJECT.exists() or (CONTROL/'frozen.json').exists():
        raise ValueError('The cold clone and freeze must be fresh')
    asset_contract = json.loads((ASSETS/'contract.json').read_bytes())
    for relative, digest in asset_contract['output_sha256'].items():
        if sha(ASSETS/relative) != digest:
            raise ValueError('The offline candidate resource changed: '+relative)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    archive = CONTROL/'source.tar'
    subprocess.run(['git', 'archive', '--format=tar', '--output', str(archive), revision,
                    'behavior_pack', 'resource_pack'], cwd=ROOT, check=True)
    PROJECT.mkdir(parents=True)
    with tarfile.open(archive) as source:
        source.extractall(PROJECT, filter='data')
    shutil.copyfile(ROOT/'.mcdev.json', PROJECT/'.mcdev.json')
    baseline = fingerprint(PROJECT)
    models = json.loads((ASSETS/'resource_pack/models/netease_models.json').read_bytes())
    materials = json.loads((ASSETS/'resource_pack/materials/entity.material').read_bytes())['materials']
    materials.pop('version')
    merge_registry(PROJECT/'resource_pack/models/netease_models.json', models)
    merge_registry(PROJECT/'resource_pack/materials/entity.material', materials, nested=True)
    for source in sorted((ASSETS/'resource_pack').rglob('*')):
        if source.is_file() and source.name not in ('netease_models.json', 'entity.material'):
            destination = PROJECT/source.relative_to(ASSETS)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    config = json.loads((PROJECT/'.mcdev.json').read_bytes())
    if any(config.get('auto_hot_reload_'+name) is not False for name in ('mods', 'ui', 'shaders', 'materials')):
        raise ValueError('All four automatic reload options must remain disabled')
    if '3.10.0.420447' not in config.get('game_executable_path', ''):
        raise ValueError('The cold clone must use the target engine')
    files = fingerprint(PROJECT)
    prior = {row['path']: row['sha256'] for row in baseline}
    changed = [row['path'] for row in files if prior.get(row['path']) != row['sha256']]
    if any(name.startswith('behavior_pack/') for name in changed):
        raise ValueError('The skeleton overlay must not change behavior code')
    receipt = json.loads((ROOT/'.runtime/shelf-mesh-inputs-r21-v2-full/oak_0_south_world.capture.json').read_bytes())
    capture = Path(receipt['helper']['path'])
    if sha(capture) != receipt['helper']['sha256']:
        raise ValueError('The known WGC executable changed')
    report = {'schema_version': 1, 'owner': OWNER, 'project': str(PROJECT),
        'source_commit': revision, 'source_archive_sha256': sha(archive),
        'source_config_sha256': sha(ROOT/'.mcdev.json'),
        'files': files, 'files_sha256': hashlib.sha256(json.dumps(files, ensure_ascii=True).encode('ascii')).hexdigest(),
        'host_sources': host_sources(), 'overlay_changed_paths': changed,
        'asset_contract_sha256': sha(ASSETS/'contract.json'), 'game_launched': False,
        'capture_exe': str(capture), 'capture_exe_sha256': sha(capture),
        'scope': 'Single oak/unpowered world shelf; first south selector only; no product behavior changes'}
    save(CONTROL/'frozen.json', report)
    print(json.dumps({'prepared': True, 'files': len(files), 'files_sha256': report['files_sha256'],
                      'source_commit': revision, 'overlay_paths': len(changed), 'game_launched': False}))


def verify():
    report = json.loads((CONTROL/'frozen.json').read_bytes())
    if report['owner'] != OWNER or report['files'] != fingerprint(PROJECT):
        raise RuntimeError('The frozen cold project changed')
    if report['host_sources'] != host_sources():
        raise RuntimeError('A frozen host source changed')
    if sha(ASSETS/'contract.json') != report['asset_contract_sha256']:
        raise RuntimeError('The offline resource contract changed')
    if sha(Path(report['capture_exe'])) != report['capture_exe_sha256']:
        raise RuntimeError('The capture executable changed')
    return report


def session():
    return json.loads((CONTROL/'launch/start-summary.json').read_bytes())


def review(direction, report_path, opened):
    if not opened:
        raise ValueError('Root must open the raw native, empty and selector images first')
    report = json.loads(report_path.read_bytes())
    if report['direction'] != direction or report['phase'] != 'selection' or report['session']['owner'] != OWNER:
        raise ValueError('Review must identify this owner and the selection phase')
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Selection must complete and restore before visual admission')
    if not report.get('selector_readback', {}).get('passed'):
        raise ValueError('The material selector did not pass')
    output = CONTROL/(direction+'-review.json')
    if output.exists():
        raise ValueError('A visual review receipt already exists for this direction')
    save(output, {'root_visual_review_accepted': True, 'direction': direction,
        'source_report': str(report_path.resolve()), 'source_report_sha256': sha(report_path),
        'selector_sha256': sha(Path(report['captures']['selector']['path'])),
        'scope': 'Admission to next diagnostic modes only; native appearance qualification remains false'})
    print(json.dumps({'review_receipt': str(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'preflight', 'start', 'capture', 'review', 'stop', 'finalize'))
    parser.add_argument('--scheduled-by-root', action='store_true')
    parser.add_argument('--phase', choices=('selection', 'details'), default='selection')
    parser.add_argument('--direction', choices=('south', 'west'), default='south')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--i-opened-native-empty-selector', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        return
    if args.action in ('stop', 'finalize'):
        started = session()
        data = load_session(started['session_file'], OWNER, live=False)
        if args.action == 'finalize':
            exact = json.loads((CONTROL/'launch/exact-exit.json').read_bytes())
            if not exact.get('completed') or any(process_identity(data[key+'_pid']) == data[key+'_identity'] for key in ('game', 'mcdk')):
                raise RuntimeError('Finalize requires both exact observed identities to have exited')
        try:
            result = instances.stop(data, force=False)
            save(CONTROL/('normal-'+args.action+'.json'), {'completed': True, 'state': result['state'], 'force': False})
        except Exception as error:
            save(CONTROL/('normal-'+args.action+'.json'), {'completed': False, 'error': str(error), 'force': False})
            raise
        return
    frozen = verify()
    if args.action == 'preflight':
        commit, games = commit_at_boundary(), generic_launcher().live_games()
        print(json.dumps({'frozen': True, 'files': len(frozen['files']), 'files_sha256': frozen['files_sha256'],
                          'commit': commit, 'live_games': games, 'launch_admissible': not games and commit['commit_available_bytes'] >= 6*1024**3}))
        return
    if args.action == 'review':
        if args.report is None:
            parser.error('Provide the exact selection report')
        review(args.direction, args.report, args.i_opened_native_empty_selector)
        return
    if args.action == 'start':
        if not args.scheduled_by_root:
            parser.error('A root runtime grant is required')
        launcher = generic_launcher()
        if launcher.live_games():
            raise RuntimeError('Exclusive MC/WGC scheduling requires zero live games before launch')
        sys.argv = [sys.argv[0], '--launch']
        launcher.main()
        started = session()
        if started['state'] != 'ready':
            raise RuntimeError('The private game did not become ready')
        from watch_intrinsic_glint_exit_r21 import watch
        watch(Path(started['session_file']), OWNER, CONTROL/'launch/exact-exit.json')
        return
    started = session()
    load_session(started['session_file'], OWNER, live=True)
    output = CONTROL/'captures'/(args.direction+'-'+args.phase)
    command = [sys.executable, '-B', '-X', 'utf8', str(ROOT/'tools/probe_shelf_skeleton_world_r21.py'),
        '--session', started['session_file'], '--owner', OWNER, '--capture-exe', frozen['capture_exe'],
        '--output', str(output), '--direction', args.direction, '--phase', args.phase]
    if args.phase == 'details':
        command += ['--review', str(CONTROL/(args.direction+'-review.json'))]
    if args.direction != 'south':
        command += ['--south-review', str(CONTROL/'south-review.json')]
    subprocess.run(command, cwd=ROOT, check=True)
    verify()


if __name__ == '__main__':
    main()

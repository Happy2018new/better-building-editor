"""Cold water validation with native projection and unchanged desktop state."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = Path(os.environ.get('MCDEV_WATER_R20_OUTPUT', str(ROOT / '.runtime/water-r20-final-v2')))
OWNER = os.environ.get('MCDEV_WATER_R20_OWNER', 'water-r20-v2')
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='ascii')


def prepare(resume=False):
    sys.path.insert(0, str(ROOT / 'tools'))
    from probe_product_water import snapshot_sources, snapshot_digest
    if OUTPUT.exists() and not resume:
        raise ValueError('Fresh evidence directory required')
    OUTPUT.mkdir(exist_ok=True)
    frozen, previous = snapshot_sources(ROOT), snapshot_sources(PROJECT)
    if set(previous) - set(frozen):
        raise ValueError('Unexpected previous clone-only source files')
    archive_path = ROOT / '.runtime/water-r20-native-v1/launch-sources.zip'
    if archive_path.exists() and not resume:
        raise ValueError('V1 source archive already exists')
    if not resume:
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in previous:
                archive.write(PROJECT / name, name)
    changed = sorted(name for name, value in frozen.items() if previous.get(name) != value)
    for name in changed:
        target = PROJECT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    for folder in ('tools/data', 'tools/native_wgc'):
        for source in (ROOT / folder).rglob('*'):
            if source.is_file():
                target = PROJECT / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    if frozen != snapshot_sources(ROOT) or frozen != snapshot_sources(PROJECT):
        save('freeze-rejected.json', {'root_changes': sorted(name for name, value in snapshot_sources(ROOT).items()
            if frozen.get(name) != value), 'clone_changes': sorted(name for name, value in snapshot_sources(PROJECT).items()
            if frozen.get(name) != value)})
        raise RuntimeError('Source changed during freeze')
    save('sync.json', {'changed_paths': changed, 'source_files': len(frozen),
        'source_contract_sha256': snapshot_digest(frozen), 'root_equals_cold_project': True,
        'v1_launch_archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest()})
    save('launch-inputs.json', {'schema': 1, 'project': str(PROJECT), 'source_sha256': frozen,
        'source_contract_sha256': snapshot_digest(frozen)})
    save('plan.json', {'schema': 1, 'production_qualified': False, 'window_actions': [],
        'source_contract_sha256': snapshot_digest(frozen),
        'native_api_same_session': True, 'native_pixel_center_subtraction': .5,
        'preserve_analytic_oracle_results': True,
        'phases': ['calibration', 'pool', 'frozen_matrix', 'animation_biome_occupancy', 'budgets', 'default_cold']})
    print(json.dumps({'prepared': True, 'files': len(frozen), 'changed': len(changed),
        'source_contract_sha256': snapshot_digest(frozen)}))


def launch():
    spec = importlib.util.spec_from_file_location('v1_host', ROOT / '.runtime/water-r20.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUTPUT, module.OWNER = OUTPUT, OWNER
    diagnostic = module.diagnostic()
    return module.launch(diagnostic)


def bound_environment():
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    environment = dict(os.environ, MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER,
        MCDEV_ALLOW_USER_FOREGROUND='1')
    return bound, environment


def execute(name, command):
    bound, environment = bound_environment()
    result = subprocess.run(command, env=environment, capture_output=True, text=True, encoding='utf8')
    save(name + '-execution.json', {'argv': command, 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr})
    print(json.dumps({'phase': name, 'returncode': result.returncode,
        'stderr': result.stderr[-4000:] if result.returncode else ''}), flush=True)
    return result.returncode


def calibration():
    return execute('calibration', [sys.executable, '-X', 'utf8', str(PROJECT / 'tools/verify_camera_projection.py'),
        str(OUTPUT / 'calibration.json'), '--native-resolution', '--skyward-tilted', '--fixture-lift-y', '64',
        '--native-api', '--native-capture-exe', str(CAPTURE)])


def probe(name, options):
    bound, environment = bound_environment()
    command = [sys.executable, '-X', 'utf8', str(PROJECT / 'tools/probe_product_water.py'),
        '--session', bound['session_file'], '--owner', OWNER, '--capture-exe', str(CAPTURE),
        '--launch-inputs', str(OUTPUT / 'launch-inputs.json'), '--output', str(OUTPUT / (name + '.json')),
        '--camera-calibration', str(OUTPUT / 'calibration.json'), '--world-fixture-lift-y', '64',
        '--world-view-scale', '.5', '--pool-view-scale', '.5', '--max-seconds', '1200'] + options
    return execute(name, command)


def pool():
    return probe('pool', ['--frozen', '--visibility-controls', '--opaque-side-controls',
        '--native-side-projection', '--measure-budgets', '--route', 'full', '--route', 'missing', '--case', 'pool'])


def editor_pool():
    return probe('editor-pool', ['--frozen', '--visibility-controls', '--opaque-side-controls',
        '--measure-budgets', '--route', 'editor', '--case', 'pool'])


def frozen_core():
    cases = ('source', 'low', 'flow_east', 'flow_south', 'flow_west', 'flow_north',
             'falling', 'diagonal', 'drop_north')
    options = ['--frozen', '--visibility-controls', '--measure-budgets']
    for case in cases:
        options.extend(('--case', case))
    return probe('frozen-core', options)


def main():
    mode = sys.argv[1]
    if mode == 'next-session':
        if OUTPUT.exists():
            raise ValueError('Fresh next-session output required')
        OUTPUT.mkdir()
        for name in ('launch-inputs.json', 'plan.json'):
            shutil.copy2(ROOT / '.runtime/water-r20-final-v2' / name, OUTPUT / name)
        save('ordering.json', {'cold_editor_first': True, 'window_actions': [],
            'hypothesis': 'World/calibration camera or renderer state suppresses subsequent editor PaperDoll water despite live model IDs and correct uniforms.'})
        return 0
    if mode == 'editor-pool':
        return editor_pool()
    if mode == 'frozen-core':
        return frozen_core()
    if mode == 'refreeze':
        return prepare(resume=True)
    if mode in ('prepare', 'launch', 'calibration', 'pool'):
        return globals()[mode]()
    if mode in ('status', 'stop'):
        bound, environment = bound_environment()
        return execute(mode, [sys.executable, '-X', 'utf8',
            str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'), mode,
            '--session', bound['session_file'], '--owner', OWNER])
    raise ValueError(mode)


if __name__ == '__main__':
    raise SystemExit(main())

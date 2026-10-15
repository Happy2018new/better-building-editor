"""Fresh owner-bound water oracle attempt without any desktop window action."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-native-v1'
OWNER = 'water-r20'
sys.path.insert(0, str(ROOT / 'tools'))


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def prepare():
    from probe_product_water import snapshot_sources, snapshot_digest
    if PROJECT.exists() or OUTPUT.exists():
        raise ValueError('Fresh project and evidence output required')
    OUTPUT.mkdir(parents=True)
    frozen = snapshot_sources(ROOT)
    for name in frozen:
        target = PROJECT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    for folder in ('tools/data', 'tools/native_wgc'):
        for source in (ROOT / folder).rglob('*'):
            if source.is_file():
                target = PROJECT / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    config = json.loads((ROOT / '.mcdev.json').read_bytes())
    for name in tuple(config):
        if name.startswith('auto_hot_reload_'):
            config[name] = False
    config.update(world_type=2, world_seed=20261015, game_mode=1)
    (PROJECT / '.mcdev.json').write_text(json.dumps(config, indent=2) + '\n', encoding='ascii')
    if frozen != snapshot_sources(ROOT) or frozen != snapshot_sources(PROJECT):
        raise RuntimeError('Source changed while copying')
    save('launch-inputs.json', {'schema': 1, 'project': str(PROJECT),
        'source_sha256': frozen, 'source_contract_sha256': snapshot_digest(frozen)})
    prior = diagnostic()
    plan = json.loads((ROOT / '.runtime/water-final-r19-world-v6/plan.json').read_bytes())
    plan.update(tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        diagnostic_only=True, production_qualified=False, project=str(PROJECT), owner=OWNER,
        frozen_source_contract=snapshot_digest(frozen),
        hypothesis='Cold owned session produces fresh background pixels and native API coordinates without activation, resize, desktop input, or z-order changes.',
        window_actions=[], render_retry_delays_seconds=[.5, 1., 2.])
    save('plan.json', plan)
    save('plan-receipt.json', {'sha256': hashlib.sha256((OUTPUT / 'plan.json').read_bytes()).hexdigest(), 'prelaunch': True})
    print(json.dumps({'prepared': True, 'files': len(frozen), 'source_contract_sha256': snapshot_digest(frozen)}))


def diagnostic():
    spec = importlib.util.spec_from_file_location('r19_v6', ROOT / '.runtime/water-native-projection-r19-v6.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUTPUT = module.prior.OUTPUT = module.prior.runner.OUTPUT = OUTPUT
    module.prior.PROJECT = module.prior.runner.PROJECT = PROJECT
    module.prior.runner.OWNER = OWNER
    os.environ['MCDEV_WATER_FINAL_OUTPUT'] = str(OUTPUT)
    sys.path.insert(0, str(PROJECT / 'tools'))
    return module


def render_ready(module):
    from capture_native_window import capture
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    value = capture(bound['session_file'], OWNER, OUTPUT / 'render_ready.png', module.prior.runner.CAPTURE)
    save('render-ready.json', {'nonblank': True, 'capture': value,
        'pixel_freshness_pending': True, 'window_actions': []})


def launch(module):
    runner = module.prior.runner
    if (OUTPUT / 'start.json').exists():
        raise ValueError('Launch receipt already exists')
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    command = [sys.executable, '-X', 'utf8', str(runner.INSTANCES), 'start',
        '--project', str(PROJECT), '--owner', OWNER, '--name', OUTPUT.name,
        '--game-exe', config['game_executable_path'], '--preset', 'ui', '--mcdk', str(runner.MCDK),
        '--noactivate-dll', str(runner.DLL), '--noactivate-sha256',
        '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        '--noactivate-mcdk-sha256', 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        '--wait', '180']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf8')
    save('launch-explicit-version.json', {'argv': command, 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr})
    if result.stdout.strip():
        bound = json.loads(result.stdout)
        save('start.json', bound)
        print(json.dumps({key: bound.get(key) for key in ('ready', 'game_pid', 'mcdk_pid', 'id', 'session_file', 'error')}))
    else:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main():
    mode = sys.argv[1]
    if mode == 'prepare':
        return prepare()
    module = diagnostic()
    if mode == 'launch':
        return launch(module)
    if mode == 'render-ready':
        return render_ready(module)
    if mode == 'calibration':
        return module.prior.calibration()
    if mode == 'world':
        return module.world()
    if mode == 'analyze':
        return module.prior.analyze()
    return module.prior.runner.run(mode)


if __name__ == '__main__':
    raise SystemExit(main())

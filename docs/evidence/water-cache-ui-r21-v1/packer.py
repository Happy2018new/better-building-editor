"""Copy the bounded water experiment record without connecting to a game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/water-cache-ui-r21-v1')
    args = parser.parse_args()
    output = args.output.resolve()
    assert not output.exists(), 'Use a new output; original evidence is immutable'
    output.mkdir(parents=True)
    copied = {}

    def copy(source, relative):
        source = ROOT / source
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert target.read_bytes() == source.read_bytes()
        copied[relative] = source.relative_to(ROOT).as_posix()

    ab = '.runtime/water-r21-depth-cache-ab-v1/'
    for name in ('ab-report.json', 'ab-report-runtime-hashlib-retry-v1.json',
                 'baseline_viewport.py', 'exit-watcher.json', 'launch-attempt.json',
                 'launch-inputs.json', 'launch-mcdev.json', 'launch-postflight.json',
                 'launch-ready.json', 'launch-result.json', 'operational-amendment-v1.json',
                 'operational-amendment-v2.json', 'plan-receipt.json', 'plan.json',
                 'process-exits.json', 'process-exits.stdout.txt', 'process-exits.stderr.txt'):
        copy(ab + name, 'cache/' + name)
    for name in ('host.py', 'embedded_ab.py', 'offline_compare.py', 'offline-comparison.json',
                 'README.md', 'check_embedded.py'):
        copy('.runtime/water-r21-depth-cache-v1/' + name, 'cache/frozen/' + name)
    for name in ('host.py', 'amendment.json', 'normal_close.py', 'normal-close.json'):
        copy('.runtime/water-r21-depth-cache-runtime-retry-v1/' + name, 'cache/retry/' + name)
    ui = '.runtime/water-ui-submit-r21-v1/'
    for name in ('candidate.py', 'runtime.py', 'runtime_engine.py', 'receipt_retry.py',
                 'receipt_retry_v2.py', 'runtime-ab-receipt-amendment.json',
                 'runtime-operational-amendment-v2.json', 'analyze_runtime.py', 'RUN.md',
                 'README.md', 'check.py', 'check_runtime.py'):
        copy(ui + name, 'ui/source/' + name)
    copy(ui + 'result/report.json', 'ui/failed/report.json')
    for source in sorted((ROOT / ui / 'result-v2').iterdir()):
        if source.is_file():
            copy(source.relative_to(ROOT), 'ui/result/' + source.name)
    for name in ('liquid_viewport.py', 'liquid_render.py', 'liquid_transport.py'):
        relative = 'behavior_pack/modern_projection/projection/' + name
        copy('.runtime/projects/water-depth-cache-r21/' + relative, 'source/frozen/' + name)
    copy('.runtime/projects/water-depth-cache-r21/.mcdev.json', 'source/frozen/.mcdev.json')
    copy('tools/replay_water_cache_ui_evidence_r21.py', 'replay.py')
    copy('tools/pack_water_cache_ui_evidence_r21.py', 'packer.py')
    copy('tools/check_water_cache_ui_evidence_r21.py', 'check.py')
    copy('docs/WATER_CACHE_UI_R21.md', 'README.md')
    (output / '.gitattributes').write_text('* -text\n', encoding='ascii')
    (output / 'origins.json').write_text(json.dumps(copied, indent=2, sort_keys=True) + '\n', encoding='ascii')
    manifest = {'schema': 1, 'offline_only': True, 'files': {}}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            manifest['files'][path.relative_to(output).as_posix()] = {
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps({'package': str(output), 'files': len(manifest['files']),
                      'bytes': sum(row['bytes'] for row in manifest['files'].values()),
                      'manifest_sha256': hashlib.sha256((output / 'manifest.json').read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()

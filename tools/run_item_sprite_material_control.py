"""Run an owned item comparison with only global native material overrides removed."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
MATERIAL = ROOT/'resource_pack/materials/entity.material'
KEYS = ('netease_block_as_entity_transparency', 'sign:entity_static')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main(run_id):
    folder = ROOT/'.runtime'/('item-material-control-'+run_id)
    folder.mkdir(parents=True, exist_ok=False)
    if (ROOT/'.mcdev.json').exists():
        raise RuntimeError('Owned worktree already has an active launch configuration')
    original = MATERIAL.read_bytes()
    variant = json.loads(original)
    omitted = {key:variant['materials'].pop(key) for key in KEYS}
    variant_bytes = (json.dumps(variant, ensure_ascii=True, indent=2)+'\n').encode('ascii')
    (folder/'original_entity.material').write_bytes(original)
    (folder/'variant_entity.material').write_bytes(variant_bytes)
    report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
              'original_sha256': digest(original), 'variant_sha256': digest(variant_bytes),
              'omitted_overrides': omitted, 'material_restored': False}
    error = None
    try:
        MATERIAL.write_bytes(variant_bytes)
        command = [sys.executable, '-X', 'utf8', str(ROOT/'tools/run_item_sprite_product.py'),
                   '--run-id', run_id, '--world', '--closeup', '--native-reference']
        with (folder/'runner_stdout.txt').open('wb') as stdout, (folder/'runner_stderr.txt').open('wb') as stderr:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        report['runner_returncode'] = result.returncode
        run_folder = ROOT/'.runtime'/('item-product-r14-'+run_id)
        report['runner_report'] = str(run_folder/'report.json')
        if (run_folder/'report.json').exists():
            command = [sys.executable, '-X', 'utf8', str(ROOT/'tools/analyze_item_sprite_closeup.py'),
                       str(run_folder/'report.json'), str(run_folder/'animation-v1')]
            with (folder/'analyzer_stdout.txt').open('wb') as stdout, (folder/'analyzer_stderr.txt').open('wb') as stderr:
                result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
            report['analyzer_returncode'] = result.returncode
            report['analysis'] = str(run_folder/'animation-v1/analysis.json')
    except Exception as caught:
        error = caught
        report['error'] = type(caught).__name__+': '+str(caught)
    finally:
        report['variant_unchanged_before_restore'] = digest(MATERIAL.read_bytes()) == digest(variant_bytes)
        if report['variant_unchanged_before_restore']:
            MATERIAL.write_bytes(original)
            report['material_restored'] = MATERIAL.read_bytes() == original
        else:
            report['restore_error'] = 'Material changed outside owned diagnostic; original backup retained'
        (folder/'report.json').write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    print(json.dumps(report, ensure_ascii=True))
    if error:
        raise error
    return 0 if report['material_restored'] and report.get('runner_returncode') == 0 else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for char in args.run_id):
        parser.error('run-id must contain only ASCII letters, numbers, hyphens or underscores')
    sys.exit(main(args.run_id))

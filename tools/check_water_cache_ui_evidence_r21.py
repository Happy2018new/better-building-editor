"""Detached replay plus semantic tampering checks for the water package."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

os.environ['OPENBLAS_NUM_THREADS'] = '1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='water-r21-independent-') as temp:
        package = Path(temp) / 'portable'
        shutil.copytree(args.package.resolve(), package)
        completed = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8',
            str(package / 'replay.py'), '--package', str(package)], cwd=temp,
            capture_output=True, text=True, encoding='utf-8', check=True)
        receipt = json.loads(completed.stdout)
        spec = importlib.util.spec_from_file_location('water_offline_replay', package / 'replay.py')
        replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(replay)
        rejected = []
        for key, value in (('game_sha_computed', True), ('production_qualified', True)):
            path = package / 'cache/ab-report-runtime-hashlib-retry-v1.json'
            original, index_original = path.read_bytes(), (package / 'manifest.json').read_bytes()
            report = json.loads(original)
            report[key] = value
            path.write_text(json.dumps(report, sort_keys=True) + '\n', encoding='ascii')
            manifest = json.loads(index_original)
            manifest['files'][path.relative_to(package).as_posix()] = {
                'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            (package / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True) + '\n', encoding='ascii')
            try:
                replay.verify(package)
            except AssertionError:
                rejected.append(key)
            else:
                raise AssertionError('Semantic tampering accepted: ' + key)
            finally:
                path.write_bytes(original)
                (package / 'manifest.json').write_bytes(index_original)
        print(json.dumps({'detached_replay': receipt, 'semantic_tampering_rejected_after_rehash': rejected}))


if __name__ == '__main__':
    main()

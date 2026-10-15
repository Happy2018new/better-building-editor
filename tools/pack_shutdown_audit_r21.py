"""Promote and verify the fixed portable shutdown audit without copying binaries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MANIFEST = '9c335271a031729c350e90d7ef59e7a66b0e70877ea7661ea1bf5db8df322800'
RELATIVE_OUTPUT = Path('docs/evidence/shutdown-cpp-exception-r21-v1')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package_files(source):
    manifest_bytes = (source / 'manifest.json').read_bytes()
    if digest(manifest_bytes) != EXPECTED_MANIFEST:
        raise ValueError('The reviewed portable manifest differs')
    manifest = json.loads(manifest_bytes)
    files = {}
    for name, expected in manifest['files'].items():
        path = (source / name).resolve()
        if not path.is_relative_to(source):
            raise ValueError('Package path escapes source: ' + name)
        data = path.read_bytes()
        if len(data) != expected['size'] or digest(data) != expected['sha256']:
            raise ValueError('Reviewed source byte identity differs: ' + name)
        files[name] = data
    files['manifest.json'] = manifest_bytes
    actual = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
    if actual != set(files):
        raise ValueError('Unexpected files outside reviewed manifest')
    return files


def verify(directory, check_original_inputs):
    command = [sys.executable, '-I', '-B', '-X', 'utf8', str(directory / 'verify.py')]
    if check_original_inputs:
        command.append('--check-original-inputs')
    result = subprocess.run(command, cwd=tempfile.gettempdir(), capture_output=True,
                            text=True, encoding='utf-8', check=False)
    if result.returncode:
        raise RuntimeError('Portable verification failed:\n' + result.stdout + result.stderr)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / '.runtime/shutdown-audit-r21-portable-v1')
    parser.add_argument('--output', type=Path, default=ROOT / RELATIVE_OUTPUT)
    parser.add_argument('--check-original-inputs', action='store_true')
    parser.add_argument('--verify-staged', action='store_true')
    args = parser.parse_args()
    args.source, args.output = args.source.resolve(), args.output.resolve()
    if not args.output.is_relative_to(ROOT / 'docs/evidence'):
        parser.error('--output must stay under this repository docs/evidence')
    source_files = package_files(args.source)
    source_result = verify(args.source, args.check_original_inputs)
    if args.verify_staged:
        prefix = args.output.relative_to(ROOT).as_posix() + '/'
        listing = subprocess.run(['git', 'ls-files', '--stage', '-z', '--', prefix],
                                 cwd=ROOT, capture_output=True, check=True).stdout
        entries = [item.decode('utf-8') for item in listing.split(b'\0') if item]
        staged = {}
        for entry in entries:
            metadata, name = entry.split('\t', 1)
            mode, oid, stage = metadata.split()
            if stage != '0' or mode != '100644':
                raise ValueError('Unmerged/non-file staged package entry: ' + name)
            relative = name[len(prefix):]
            data = subprocess.run(['git', 'cat-file', 'blob', oid], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            if relative not in source_files or data != source_files[relative]:
                raise ValueError('Staged bytes differ from reviewed package: ' + relative)
            staged[relative] = data
        if set(staged) != set(source_files):
            raise ValueError('The staged package path set differs')
        with tempfile.TemporaryDirectory(prefix='shutdown-audit-staged-') as temporary:
            exported = Path(temporary)
            for name, data in staged.items():
                target = exported / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            replay = verify(exported, args.check_original_inputs)
        result = {'staged_blob_files_verified': len(staged), 'source': source_result, 'staged_export': replay}
    else:
        if args.output.exists():
            raise ValueError('Refusing to overwrite existing evidence: ' + str(args.output))
        args.output.mkdir(parents=True)
        for name, data in source_files.items():
            target = args.output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if package_files(args.output) != source_files:
            raise ValueError('Promoted package bytes differ')
        result = {'copied_files': len(source_files), 'output': str(args.output),
                  'source': source_result, 'promoted': verify(args.output, args.check_original_inputs)}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

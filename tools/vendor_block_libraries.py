"""Build a pinned, self-contained private copy of the two pure block libraries."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / 'tools/data/block_library_lock.json'
PACKAGES = {'nemc-block-states': 'nemc_block_states',
            'nemc-block-renderer': 'nemc_block_renderer'}
PACKAGE_INIT = b'"""Pinned pure block libraries; no host or engine initialization."""\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root)] + list(arguments), stderr=subprocess.PIPE)


def runtime_path(value, package):
    """Only a single Python module directly inside the named package is allowed."""
    if (not isinstance(value, str) or not re.fullmatch(
            re.escape(package) + r'/[A-Za-z_][A-Za-z_0-9]*\.py', value)):
        raise ValueError('Unsafe runtime package path: %r' % value)
    return value


def checked_digest(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('Invalid SHA-256: ' + label)
    return value


def checked_commit(root, lock):
    commit = lock.get('commit')
    if (lock.get('branch') != 'main' or not isinstance(commit, str) or
            not re.fullmatch(r'[0-9a-f]{40}', commit)):
        raise ValueError('Library must pin a main commit: ' + str(root))
    expected = {'HEAD': commit, 'refs/heads/main': commit}
    for revision, target in expected.items():
        if git(root, 'rev-parse', '--verify', revision).decode('ascii').strip() != target:
            raise ValueError('Library commit mismatch: ' + str(root) + ' ' + revision)
    if git(root, 'branch', '--show-current').decode('ascii').strip() != 'main':
        raise ValueError('Library checkout must be on main: ' + str(root))


def source_bytes(root, relative, expected, commit):
    path = root / relative
    # Reject symlinks and Windows junctions, even if their bytes happen to match.
    if not path.is_file() or path.resolve() != path:
        raise ValueError('Missing or redirected library file: ' + relative)
    raw = path.read_bytes()
    if digest(raw) != checked_digest(expected, relative):
        raise ValueError('Library file SHA-256 mismatch: ' + relative)
    if git(root, 'show', commit + ':' + relative) != raw:
        raise ValueError('Library file differs from pinned Git blob: ' + relative)
    return raw


def inspect_library(root, repository, lock):
    package = PACKAGES[repository]
    if lock.get('package') != package:
        raise ValueError('Unexpected library package: ' + repository)
    checked_commit(root, lock)
    files = lock.get('runtime_files')
    if not isinstance(files, dict) or package + '/__init__.py' not in files:
        raise ValueError('Runtime file list must contain the package initializer: ' + repository)
    for path in files:
        runtime_path(path, package)
    package_root = root / package
    if not package_root.is_dir() or package_root.resolve() != package_root:
        raise ValueError('Missing or redirected package directory: ' + package)
    actual = {path.relative_to(root).as_posix() for path in package_root.rglob('*.py')}
    if actual != set(files):
        raise ValueError('Runtime file inventory mismatch: ' + repository)
    payload = {path: source_bytes(root, path, expected, lock['commit'])
               for path, expected in sorted(files.items())}
    manifest_raw = source_bytes(root, 'snapshot_manifest.json', lock.get('manifest_sha256'), lock['commit'])
    manifest = json.loads(manifest_raw)
    for module in manifest['modules']:
        path = runtime_path(module['destination'], package)
        if files.get(path) != module['sha256']:
            raise ValueError('Manifest module is not in the pinned runtime: ' + path)
    payload['manifests/' + repository + '.json'] = manifest_raw
    payload['licenses/' + repository + '.txt'] = source_bytes(
        root, 'LICENSE', lock.get('license_sha256'), lock['commit'])
    return payload, manifest


def build(states, renderer, output, lock_path=DEFAULT_LOCK):
    """Validate everything before writing a new output directory; never overwrite."""
    roots = {'nemc-block-states': Path(states).resolve(),
             'nemc-block-renderer': Path(renderer).resolve()}
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output directory already exists: ' + str(output))
    for root in roots.values():
        if output == root or root in output.parents or output in root.parents:
            raise ValueError('Output must be separate from both source repositories')
    lock_raw = Path(lock_path).read_bytes()
    lock = json.loads(lock_raw)
    if lock.get('schema_version') != 1 or set(lock.get('libraries', {})) != set(PACKAGES):
        raise ValueError('Lock must describe exactly the two block libraries')
    payload = {'__init__.py': PACKAGE_INIT, 'block_library_lock.json': lock_raw}
    manifests = {}
    for repository, root in roots.items():
        files, manifest = inspect_library(root, repository, lock['libraries'][repository])
        payload.update(files)
        manifests[repository] = manifest
    binding = manifests['nemc-block-renderer']['states_binding']
    states_raw = payload['manifests/nemc-block-states.json']
    if binding.get('snapshot_manifest_sha256') != digest(states_raw):
        raise ValueError('Renderer binding does not match the pinned state manifest')
    # All copied bytes have been verified against both the lock and Git objects.
    receipt = {'schema_version': 1, 'lock_sha256': digest(lock_raw),
               'tool_sha256': digest(Path(__file__).read_bytes()),
               'library_commits': {name: row['commit'] for name, row in lock['libraries'].items()},
               'runtime_python_files': sum(len(row['runtime_files']) for row in lock['libraries'].values()),
               'runtime_python_bytes': sum(len(payload[path]) for row in lock['libraries'].values()
                                           for path in row['runtime_files']),
               'files_sha256': {path: digest(raw) for path, raw in sorted(payload.items())},
               'host_runtime_integrated': False, 'native_or_GPU_qualification_granted': False}
    payload['vendor_manifest.json'] = encoded(receipt)
    output.mkdir(parents=True, exist_ok=False)
    for relative, raw in sorted(payload.items()):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as target:
            target.write(raw)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--states', type=Path, required=True, help='Read-only state repository checkout')
    parser.add_argument('--renderer', type=Path, required=True, help='Read-only renderer repository checkout')
    parser.add_argument('--output', type=Path, required=True, help='New independent private package directory')
    parser.add_argument('--lock', type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()
    result = build(args.states, args.renderer, args.output, args.lock)
    print(json.dumps({'output': str(args.output.resolve()), 'lock_sha256': result['lock_sha256'],
                      'runtime_python_files': result['runtime_python_files'],
                      'runtime_python_bytes': result['runtime_python_bytes'],
                      'host_runtime_integrated': False}, sort_keys=True))


if __name__ == '__main__':
    main()

"""Replay an exact archived liquid scorer in an isolated cold filesystem tree.

Only recorded file locations are redirected. Original bytes, SHA bindings,
thresholds and every scorer predicate remain intact. No game or SDK is started.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative_path(root, value):
    """Keep every archive and materialized path inside its declared tree."""
    text = str(value).replace('\\', '/')
    relative = PurePosixPath(text)
    if (not text or relative.is_absolute() or PureWindowsPath(text).is_absolute()
            or '..' in relative.parts or ':' in text):
        raise ValueError('Archive path must be a contained relative path: ' + text)
    path = (root / Path(*relative.parts)).resolve(strict=True)
    if not path.is_relative_to(root.resolve(strict=True)) or not path.is_file():
        raise ValueError('Archive reference leaves its root: ' + text)
    return path


def original_key(value):
    text = str(value).replace('\\', '/')
    if PureWindowsPath(text).is_absolute():
        return text.casefold()
    if PurePosixPath(text).is_absolute():
        return text
    raise ValueError('Recorded original reference must be absolute: ' + text)


def source_name(value):
    name = str(value).replace('\\', '/')
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or PureWindowsPath(name).is_absolute()
            or '..' in relative.parts or ':' in name or relative.as_posix() != name
            or not name.endswith('.py')):
        raise ValueError('Invalid source closure path: ' + name)
    return name


def source_records(manifest):
    records = manifest['files']
    if isinstance(records, dict):
        return records
    # Mixed archives also contain captures and reports. Only explicitly
    # recorded project sources belong to the executable dependency closure.
    if not manifest.get('frozen_project') and any('project_relative_path' not in row for row in records):
        raise ValueError('Source closure row lacks its project path')
    rows = [row for row in records if 'project_relative_path' in row]
    names = [source_name(row['project_relative_path']) for row in rows]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate source closure project path')
    return dict(zip(names, rows))


class Archive:
    def __init__(self, root, index_name='archive-index.json'):
        self.root = Path(root).resolve(strict=True)
        self.index_path = relative_path(self.root, index_name)
        index = json.loads(self.index_path.read_bytes())
        if index.get('schema') != 1 or not isinstance(index.get('files'), list):
            raise ValueError('Unknown archive index')
        self.index = index
        self.by_original, self.by_relative = {}, {}
        for row in index['files']:
            name = row['archive_path']
            path = relative_path(self.root, name)
            if digest(path) != row['sha256'] or path.stat().st_size != row['bytes']:
                raise ValueError('Archived original bytes changed: ' + name)
            keys = [original_key(row['original_path'])]
            if row.get('frozen_original_path'):
                keys.append(original_key(row['frozen_original_path']))
            keys = set(keys)
            if name in self.by_relative or any(key in self.by_original for key in keys):
                raise ValueError('Ambiguous archive original/path binding')
            for key in keys:
                self.by_original[key] = path
            self.by_relative[name] = path
        self.indexed_original = dict(self.by_original)
        self.source_alias_manifest = None
        if index.get('frozen_project') is not None:
            frozen = str(index['frozen_project']).replace('\\', '/')
            original_key(frozen)
            project = PureWindowsPath(frozen) if PureWindowsPath(frozen).is_absolute() else PurePosixPath(frozen)
            aliases = []
            for name, row in source_records(index).items():
                alias = str(project / name)
                key = original_key(alias)
                path = self.by_relative[row['archive_path']]
                previous = self.by_original.get(key)
                if previous is not None and previous != path:
                    raise ValueError('Derived project alias conflicts with an original archive binding: ' + alias)
                self.by_original[key] = path
                aliases.append({'project_relative_path': name, 'derived_original_path': alias,
                                'indexed_original_path': row['original_path'],
                                'archive_path': row['archive_path'], 'sha256': row['sha256'],
                                'bytes': row['bytes']})
            if aliases:
                self.source_alias_manifest = {
                    'schema': 1, 'rule': 'frozen_project + contained project_relative_path',
                    'archive_index_sha256': digest(self.index_path), 'sources': aliases}

    def extend(self, other):
        for key, path in other.by_original.items():
            previous = self.by_original.get(key)
            if previous is not None and digest(previous) != digest(path):
                raise ValueError('Supplement changes an original archive binding')
            self.by_original[key] = path

    def resolve(self, reference):
        path = self.by_original.get(original_key(reference['path']))
        if path is None or digest(path) != reference['sha256']:
            raise ValueError('Original reference is missing or changed: ' + reference['path'])
        return path

    def original_path(self, value):
        path = self.by_original.get(original_key(value))
        if path is None:
            raise ValueError('Original capture path is not indexed: ' + str(value))
        return path


def verify_closure(archive, closure_name, source_archive=None, additional_archives=()):
    source_archive = source_archive or archive
    manifest_path = relative_path(source_archive.root, closure_name)
    # The closure manifest is supplementary; each source must ALSO match an
    # original indexed artifact and, where declared, the original plan SHA.
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), (dict, list)):
        raise ValueError('Unknown raw source closure')
    records = source_records(manifest)
    entries = [(name, row, source_archive) for name, row in records.items()]
    for supplement in additional_archives:
        entries.extend((name, row, supplement) for name, row in source_records(supplement.index).items())
    files, original_sources = {}, {}
    for relative, row, origin_archive in entries:
        name = source_name(relative)
        path = relative_path(origin_archive.root, row['archive_path'])
        reference = {'path': row['original_path'], 'sha256': row['sha256']}
        indexed = origin_archive.indexed_original.get(original_key(row['original_path']))
        if (path != indexed or digest(archive.resolve(reference)) != row['sha256']):
            raise ValueError('Closure source is not exact indexed bytes: ' + name)
        original = original_key(row['original_path'])
        if name in files and (digest(files[name]) != row['sha256'] or original_sources[name] != original):
            raise ValueError('Supplement changes a source closure binding: ' + name)
        files[name] = path
        original_sources[name] = original
    analyzer = manifest.get('analyzer', 'tools/analyze_liquid_native_write.py')
    if analyzer != 'tools/analyze_liquid_native_write.py' or analyzer not in files:
        raise ValueError('Exact finite native-write scorer is required')
    return manifest, files, manifest_path


def semantic_result(result):
    value = deepcopy(result)
    for name in ('source', 'geometry_plan', 'analyzer'):
        value[name].pop('path', None)
    return value


@contextmanager
def isolated_cwd(directory):
    previous = Path.cwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(previous)


def worker(archive_directory, closure_name, input_name, expected_name, source_directories=()):
    archive = Archive(archive_directory)
    supplements = [Archive(directory) for directory in source_directories]
    for supplement in supplements:
        archive.extend(supplement)
    source_archive = supplements[0] if supplements else archive
    manifest, sources, manifest_path = verify_closure(archive, closure_name, source_archive, supplements[1:])
    source_path = relative_path(archive.root, input_name)
    expected_path = relative_path(archive.root, expected_name)
    if source_path not in archive.by_relative.values() or expected_path not in archive.by_relative.values():
        raise ValueError('Raw capture and expected result must be indexed')
    original = json.loads(source_path.read_bytes())
    expected = json.loads(expected_path.read_bytes())
    geometry_path = archive.resolve(original['preflight']['geometry_plan'])
    plan = json.loads(geometry_path.read_bytes())
    for name, row in plan['source_bindings'].items():
        if name not in sources or digest(sources[name]) != row['sha256']:
            raise ValueError('Original pre-capture source binding differs: ' + name)
        archive.resolve(row)
    analyzer_name = manifest.get('analyzer', 'tools/analyze_liquid_native_write.py')
    analyzer_reference = plan['native_write_visibility']['analyzer']
    if digest(sources[analyzer_name]) != digest(archive.resolve(analyzer_reference)):
        raise ValueError('Original pre-capture scorer binding differs')
    with tempfile.TemporaryDirectory(prefix='liquid-raw-replay-') as directory, isolated_cwd(directory):
        isolated = Path(directory).resolve(strict=True)
        for name, source in sources.items():
            target = isolated / Path(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if digest(target) != digest(source):
                raise ValueError('Materialized source bytes changed')
        # Imported tools must not resolve cwd-relative resources from the live
        # checkout either. This disposable worker never returns to its caller.
        # This worker is already a separate -I process. Only these exact frozen
        # project paths enter its imports; the current checkout is never added.
        sys.path[:0] = [str(isolated / 'tools'),
                       str(isolated / 'behavior_pack/modern_projection'),
                       str(isolated / '.agents/skills/pyreact-debugging/scripts')]
        scorer_path = isolated / analyzer_name
        spec = importlib.util.spec_from_file_location('_archived_liquid_native_scorer', scorer_path)
        scorer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scorer)
        scorer.sides.read_reference = archive.resolve
        raw_capture_failures = scorer.capture_failures
        raw_rgb = scorer.rgb

        def relocated_capture_failures(captures, binding):
            detached = deepcopy(captures)
            for row in detached.values():
                row['path'] = str(archive.original_path(row['path']))
            return raw_capture_failures(detached, binding)

        scorer.capture_failures = relocated_capture_failures
        scorer.rgb = lambda value: raw_rgb(archive.original_path(value))
        result = scorer.analyze(source_path)
        local_imports = {analyzer_name: digest(scorer_path)}
        for module in list(sys.modules.values()):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                if path.is_relative_to(isolated) and path.suffix == '.py':
                    name = path.relative_to(isolated).as_posix()
                    if name not in sources or digest(path) != digest(sources[name]):
                        raise ValueError('Imported source is outside the exact closure: ' + name)
                    local_imports[name] = digest(path)
        required_imports = {'tools/analyze_liquid_sides.py', 'tools/analyze_liquid_workspace.py',
                            'behavior_pack/modern_projection/projection/debug_liquid_blueprints.py'}
        if not required_imports.issubset(local_imports):
            raise ValueError('Original scorer dependencies were not audited in the frozen tree')
        if digest(scorer_path) != analyzer_reference['sha256']:
            raise ValueError('Executed scorer bytes changed')
    if semantic_result(result) != semantic_result(expected):
        raise ValueError('Original verdict, pixels or source/capture gates did not reproduce')
    return {'schema': 2, 'scope': 'Exact raw-byte offline replay; only file locations redirected',
            'reproduced': True, 'new_launches': 0, 'sdk_or_network_calls': 0,
            'replay_helper_sha256': digest(__file__),
            'host': {'python': sys.version, 'numpy': sys.modules['numpy'].__version__,
                     'pillow': sys.modules['PIL'].__version__},
            'archive_index_sha256': digest(archive.index_path),
            'source_archive_index_sha256': [digest(row.index_path) for row in supplements],
            'source_alias_manifests': [row.source_alias_manifest for row in [archive] + supplements
                                       if row.source_alias_manifest is not None],
            'source_closure_sha256': digest(manifest_path), 'original_input_sha256': digest(source_path),
            'original_result_sha256': digest(expected_path), 'imported_source_sha256': local_imports,
            'recomputed': result, 'comparison': 'All values identical except three output filesystem paths'}


def replay(archive, closure, output, input_name='original-priority.json',
           expected_name='native-visibility-analysis.json', timeout=60, source_archives=()):
    output = Path(output)
    if output.exists():
        raise ValueError('Preserve previous replay; choose a fresh output')
    command = [sys.executable, '-I', '-X', 'utf8', str(Path(__file__).resolve()), '--worker',
               '--archive', str(Path(archive).resolve(strict=True)), '--closure', closure,
               '--input', input_name, '--expected', expected_name]
    for source_archive in source_archives:
        command += ['--source-archive', str(Path(source_archive).resolve(strict=True))]
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith(('MCDEV_', 'MCDK_', 'PYTHONPATH'))}
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf8',
                            timeout=timeout, env=environment,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode:
        raise ValueError('Frozen replay refused: ' + result.stderr.strip())
    report = json.loads(result.stdout)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='ascii', newline='\n') as handle:
        handle.write(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--closure', required=True)
    parser.add_argument('--source-archive', type=Path, action='append', default=[],
                        help='Separate exact-byte supplementary source archive; original index stays immutable')
    parser.add_argument('--input', default='original-priority.json')
    parser.add_argument('--expected', default='native-visibility-analysis.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        report = worker(args.archive, args.closure, args.input, args.expected, args.source_archive)
    else:
        if args.output is None:
            parser.error('--output is required')
        report = replay(args.archive, args.closure, args.output, args.input, args.expected,
                        source_archives=args.source_archive)
    print(json.dumps(report, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

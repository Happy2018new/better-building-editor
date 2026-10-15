"""Bind a private native-UI census clone to the complete frozen shelf inputs."""
import argparse
import hashlib
import json
from pathlib import Path

RELOADS = ('auto_hot_reload_materials', 'auto_hot_reload_mods',
           'auto_hot_reload_shaders', 'auto_hot_reload_ui')


def fingerprint(project):
    paths = [project / '.mcdev.json']
    for folder in ('behavior_pack', 'resource_pack'):
        paths.extend(path for path in (project / folder).rglob('*') if path.is_file())
    return [{'path': path.relative_to(project).as_posix(), 'bytes': path.stat().st_size,
             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(paths)]


def freeze(source, clone, output):
    source, clone = source.resolve(strict=True), clone.resolve(strict=True)
    if source == clone or output.exists():
        raise ValueError('A distinct private clone and fresh manifest are required')
    original, copied = fingerprint(source), fingerprint(clone)
    if original != copied:
        raise ValueError('The private clone does not match its complete source bytes')
    config = json.loads((clone / '.mcdev.json').read_text(encoding='utf8'))
    if any(config.get(key) is not False for key in RELOADS):
        raise ValueError('All four automatic reload options must be disabled')
    report = {'schema': 1, 'source': str(source), 'clone': str(clone),
              'files': copied, 'file_count': len(copied),
              'total_bytes': sum(row['bytes'] for row in copied),
              'files_sha256': hashlib.sha256(json.dumps(copied, ensure_ascii=True).encode('ascii')).hexdigest(),
              'config': config, 'source_matches_clone': True,
              'modified_source_files': False, 'game_launched': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--clone', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = freeze(args.source, args.clone, args.output)
    print(json.dumps({key: result[key] for key in ('file_count', 'total_bytes', 'files_sha256',
                                                  'source_matches_clone', 'game_launched')}))

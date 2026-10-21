"""Verify every stored byte, complete reconstructed object, and size bound offline."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('bundle', nargs='?', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    folder = args.bundle.resolve()
    manifest = json.loads((folder / 'manifest.json').read_bytes())
    expected = {'manifest.json'}
    originals = derived = total = 0
    for row in manifest['objects']:
        chunks = []
        for part in row['parts']:
            path = (folder / part['path']).resolve()
            assert path.is_relative_to(folder)
            assert part['path'] not in expected
            expected.add(part['path'])
            raw = path.read_bytes()
            assert len(raw) == part['bytes'] < 300000
            assert sha(raw) == part['sha256']
            chunks.append(raw)
            total += len(raw)
        stored = b''.join(chunks)
        assert row['encoding'] in ('identity', 'gzip')
        raw = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
        assert len(raw) == row['content_bytes'] and sha(raw) == row['content_sha256']
        if row['original_source']:
            assert row['original_sha256'] == row['content_sha256'] and row['content_transform'] == 'none'
            originals += 1
        else:
            assert row['original_sha256'] is None and row['content_transform'] != 'none'
            derived += 1
        assert row['redacted'] is (row['content_transform'] == 'redacted')
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob('*') if path.is_file()}
    assert actual == expected, (actual - expected, expected - actual)
    assert all((folder / name).stat().st_size < 300000 for name in actual)
    print(json.dumps({'passed': True, 'objects': len(manifest['objects']), 'original_objects': originals,
                      'derived_objects': derived, 'stored_files': len(actual),
                      'stored_bytes_excluding_manifest': total,
                      'manifest_sha256': sha((folder / 'manifest.json').read_bytes()),
                      'candidate_promoted': False, 'GPU_qualified': False}))


if __name__ == '__main__':
    main()

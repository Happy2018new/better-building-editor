"""Verify exact qualified source/evidence bytes through Git's Windows checkout filters.

A temporary Git object store and an optional report are written. The project
index and source files are read-only; this grants no new GPU qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BUNDLES = ('docs/evidence/water-product-r24-v1', 'docs/evidence/coral-r24-v1')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def qualified_paths(project):
    qualification = json.loads((project / BUNDLES[0] / 'qualification.json').read_bytes())
    names = set(qualification['implementation_sha256'])
    names.update(('tools/data/liquid_product_owner_contract_v1.json',
                  'tools/data/liquid_product_resource_contract_v1.json',
                  'tools/qualify_water_product_r16.py',
                  'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py'))
    coral = json.loads((project / BUNDLES[1] / 'source-binding.json').read_bytes())
    names.update(coral['source_sha256'])
    for relative in BUNDLES:
        names.update(path.relative_to(project).as_posix()
                     for path in (project / relative).iterdir() if path.is_file())
    return sorted(names)


def verify_roundtrip(project, names):
    project = project.resolve(strict=True)
    originals = {}
    for relative in names:
        path = (project / relative).resolve(strict=True)
        if not path.is_relative_to(project):
            raise ValueError('Source is outside project: ' + relative)
        originals[relative] = path.read_bytes()
    attributes = (project / '.gitattributes').read_bytes()
    rows = []
    with tempfile.TemporaryDirectory(prefix='bbe-qualified-git-') as temporary:
        isolated = Path(temporary).resolve()
        command = ['git', '-C', str(isolated)]
        subprocess.run(command + ['init', '--quiet'], check=True, capture_output=True)
        subprocess.run(command + ['config', 'core.autocrlf', 'true'], check=True,
                       capture_output=True)
        empty = isolated / 'empty-global-attributes'
        empty.write_bytes(b'')
        subprocess.run(command + ['config', 'core.attributesfile', str(empty)], check=True,
                       capture_output=True)
        (isolated / '.gitattributes').write_bytes(attributes)
        for relative, original in originals.items():
            clean = subprocess.run(command + ['hash-object', '-w', '--path=' + relative, '--stdin'],
                                   input=original, capture_output=True, check=True)
            blob = clean.stdout.decode('ascii').strip()
            restored = subprocess.check_output(
                command + ['cat-file', '--filters', '--path=' + relative, blob])
            rows.append({'path': relative, 'bytes': len(original),
                         'original_sha256': digest(original), 'git_blob_sha1': blob,
                         'roundtrip_sha256': digest(restored), 'byte_identical': original == restored})
    return {'schema': 1, 'core_autocrlf': True,
            'global_attributes_disabled_for_portable_repo_rules': True,
            'temporary_object_store_only': True, 'project_index_modified': False,
            'gitattributes_sha256': digest(attributes), 'files_checked': len(rows),
            'all_byte_identical': all(row['byte_identical'] for row in rows),
            'gpu_qualification_granted': False, 'files': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    report = verify_roundtrip(project, qualified_paths(project))
    if args.output is not None:
        target = args.output.resolve()
        if target.exists():
            raise ValueError('Keep the previous report intact: ' + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + '\n', 'utf8')
    print(json.dumps({key: value for key, value in report.items() if key != 'files'}))
    raise SystemExit(0 if report['all_byte_identical'] else 1)


if __name__ == '__main__':
    main()

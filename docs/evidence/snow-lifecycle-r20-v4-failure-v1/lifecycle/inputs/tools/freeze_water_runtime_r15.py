"""Record an isolated water test project's immutable launch inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from probe_product_water import snapshot_digest, snapshot_sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--archive', type=Path,
                        help='Preserve all hashed launch inputs in a verified source archive')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh launch inputs')
    if args.archive and args.archive.exists():
        parser.error('Choose a fresh source archive')
    project = args.project.resolve(strict=True)
    sources = snapshot_sources(project)
    report = {'schema': 1, 'project': str(project), 'source_sha256': sources,
              'source_contract_sha256': snapshot_digest(sources)}
    if args.archive:
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.archive, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6) as archive:
            for name, expected in sorted(sources.items()):
                data = (project / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError('Launch input changed while archiving: ' + name)
                member = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(member, data, compresslevel=6)
        with zipfile.ZipFile(args.archive) as archive:
            if set(archive.namelist()) != set(sources):
                raise ValueError('Archived launch input list differs')
            for name, expected in sources.items():
                if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                    raise ValueError('Archived launch input differs: ' + name)
        report['archive'] = {'path': str(args.archive.resolve()),
                             'sha256': hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                             'bytes': args.archive.stat().st_size, 'verified_files': len(sources)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'files': len(sources), 'source_contract_sha256': report['source_contract_sha256']}))


if __name__ == '__main__':
    main()

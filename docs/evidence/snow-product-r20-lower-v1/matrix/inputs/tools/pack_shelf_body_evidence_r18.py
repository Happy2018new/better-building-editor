"""Freeze shelf candidate and shadow diagnostics without granting admission."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from generate_shelf_resources_r17 import WOODS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(report_path, destination, labels):
    report = json.loads(report_path.read_bytes())
    if not report.get('completed') or not report.get('restored') or report.get('cleanup_errors'):
        raise ValueError('Only completed, restored shelf observations may be frozen')
    if report.get('source_unchanged') is False:
        raise ValueError('Shelf sources changed during capture')
    destination.mkdir(parents=True)
    shutil.copy2(report_path, destination/'report.json')
    for label in labels:
        receipt = report['captures'][label]
        source = Path(receipt['path'])
        if not source.is_file():
            source = report_path.parent/source.name
        if receipt.get('reliable') is not True or digest(source) != receipt['sha256']:
            raise ValueError('Invalid shelf capture: '+label)
        shutil.copy2(source, destination/source.name)
        shutil.copy2(source.with_suffix('.capture.json'), destination/source.with_suffix('.capture.json').name)
    return {'report_sha256': digest(report_path), 'reported_captures': len(report['captures']),
            'preserved_labels': labels, 'omitted_labels': sorted(set(report['captures'])-set(labels))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-report', type=Path, required=True)
    parser.add_argument('--body-report', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    native = [wood+'-0-south' for wood in WOODS]
    native += ['oak-0-east', 'oak-4-south', 'oak-4-east', 'oak-4-north', 'oak-4-west',
               'oak-8-west', 'oak-16-north', 'oak-24-east']
    body = json.loads(args.body_report.read_bytes())
    observations = {
        'native': freeze(args.native_report, args.output/'native', native),
        'body': freeze(args.body_report, args.output/'body', sorted(body['captures']))}
    shutil.copytree(args.review, args.output/'review')
    root = Path(__file__).resolve().parents[1]
    for relative in ('tools/generate_shelf_resources_r17.py', 'tools/probe_shelf_native_shape_r17.py',
                     'tools/probe_native_palette_body_r16.py', 'tools/probe_liquid_pose_channel.py',
                     'tools/analyze_shelf_body_r18.py', 'tools/pack_shelf_body_evidence_r18.py',
                     'tools/data/shelf_body_java_1.21.9_reference.json'):
        target = args.output/'sources'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root/relative, target)
    for name in ('contract.json', 'reference.json'):
        shutil.copy2(args.candidate/name, args.output/('candidate-'+name))
    for relative in (
            'resource_pack/models/netease_block/preview_shelf_oak_unpowered_south.json',
            'behavior_pack/netease_blocks/preview_shelf_oak_unpowered_south.json',
            'resource_pack/textures/blocks/modern_projection_shelf_oak.png'):
        target = args.output/'candidate'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.candidate/relative, target)
    metadata = {'schema_version': 1, 'production_qualified': False,
                'engine_version': '3.10.0.420447', 'observations': observations,
                'limits': ['Native report records 52 captures; only the 20 listed native originals are packaged.',
                           'All 32 shadow/body originals are packaged. No state/UV/content/runtime admission.']}
    (args.output/'index.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='ascii', newline='\n')
    manifest = {path.relative_to(args.output).as_posix(): digest(path)
                for path in sorted(args.output.rglob('*')) if path.is_file()}
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'files': len(manifest)+1, 'captures': 32+len(native), 'production_qualified': False}))


if __name__ == '__main__':
    main()

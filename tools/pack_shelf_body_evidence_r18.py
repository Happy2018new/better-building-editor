"""Freeze shelf candidate and shadow diagnostics without granting admission."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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


def verify_matrix(folder, replay=False):
    manifest = json.loads((folder/'manifest.json').read_bytes())
    actual = {path.relative_to(folder).as_posix(): digest(path)
              for path in folder.rglob('*') if path.is_file() and path != folder/'manifest.json'}
    if manifest != actual:
        raise ValueError('Shelf matrix package differs from its manifest')
    if replay:
        with tempfile.TemporaryDirectory(prefix='shelf-matrix-replay-') as directory:
            output = Path(directory)/'review'
            subprocess.run([sys.executable, '-B', '-X', 'utf8', str(folder/'sources/analyzer.py'),
                            str(folder/'captures/report.json'), str(output)], check=True,
                           capture_output=True)
            if json.loads((output/'review.json').read_bytes()) != json.loads((folder/'review/review.json').read_bytes()):
                raise ValueError('Shelf matrix pixel replay differs from the frozen analysis')
    print(json.dumps({'files': len(actual), 'manifest_verified': True,
                      'pixels_replayed': replay, 'production_qualified': False}))


def freeze_matrix(report_path, review, project, output, experiment='direction'):
    report = json.loads(report_path.read_bytes())
    if report.get('source_unchanged') is not True:
        raise ValueError('Shelf matrix must bind unchanged project sources')
    analysis = json.loads((review/'review.json').read_bytes())
    if analysis.get('source_report_sha256') != digest(report_path):
        raise ValueError('Shelf analysis refers to another report')
    output.mkdir(parents=True, exist_ok=False)
    observation = freeze(report_path, output/'captures', sorted(report['captures']))
    shutil.copytree(review, output/'review')
    shutil.copytree(report_path.parent/'host_sources', output/'acquisition-hosts')
    host = output/'acquisition-hosts/probe_shelf_body_matrix_r20.py'
    if digest(host) != report['host_sha256']:
        raise ValueError('Shelf acquisition host differs from its recorded fingerprint')
    root = Path(__file__).resolve().parents[1]
    (output/'sources').mkdir()
    shutil.copy2(root/'tools/analyze_shelf_body_matrix_r20.py', output/'sources/analyzer.py')
    shutil.copy2(Path(__file__), output/'sources/package-builder.py')
    inputs = {}
    for relative, expected in report['source_sha256'].items():
        path = project/relative
        if digest(path) != expected:
            raise ValueError('Shelf project no longer matches acquisition: '+relative)
        if ('preview_shelf_oak_' in relative or 'modern_projection_shelf_oak.' in relative or
                relative in ('resource_pack/blocks.json', 'resource_pack/textures/terrain_texture.json')):
            target = output/'candidate-inputs'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            inputs[relative] = expected
    findings = {
        'direction': ('Engine-direction and bone controls were pixel-identical; AO remained too bright.',
                      'Engine face-directional and bone-rotation controls produce identical candidate pixels. '
                      'AO improves the brightness difference but does not close it. Native east/west middle '
                      'backing is about 0.75 times north/south; the candidate does not reproduce that difference.'),
        'baked': ('Baked north/south matched bone controls, while east/west geometry differed and was rejected.',
                  'The baked coordinate candidate matches its bone-rotation control for north/south, but '
                  'east/west differs in silhouette and apparent depth. This experiment fails geometry acceptance '
                  'and does not establish a lighting fix. Rotation sign and native face conventions remain open.')}
    finding, description = findings[experiment]
    (output/'index.json').write_text(json.dumps({
        'schema_version': 1, 'production_qualified': False, 'observation': observation,
        'experiment': experiment,
        'candidate_input_sha256': inputs,
        'limits': ['Diagnostic shelf body comparisons only; no content or product admission.',
                   'All declared project hashes are checked while packing; only relevant oak assets are copied.',
                   'Per-channel normalization does not qualify absolute lighting.',
                   finding]},
        indent=2)+'\n', encoding='ascii', newline='\n')
    (output/'README.md').write_text(
        '# Shelf direction and lighting diagnostic, R21\n\n'
        'NEMC 3.10.0.420447. All 24 original PNGs, receipts, native projected-cell corners, '
        'acquisition hosts, analysis and relevant oak candidate assets are preserved. '
        'The capture completed, restored its world/editor state and retained unchanged sources.\n\n'
        + description + ' '
        'Normalized texture comparisons are diagnostic only. Neither production routing nor '
        'three-slot item content is qualified.\n\n'
        'The portable analysis uses native physical projected-cell corners to exclude exterior '
        'background changes. Original exterior changed-pixel counts remain recorded. The complete '
        'source-hash contract is retained, but this is not a full executable product source archive.\n\n'
        'Replay with `python -B -X utf8 tools/pack_shelf_body_evidence_r18.py '
        '--output docs/evidence/shelf-direction-r21-v1 --verify --replay`.\n',
        encoding='ascii', newline='\n')
    manifest = {path.relative_to(output).as_posix(): digest(path)
                for path in output.rglob('*') if path.is_file()}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='ascii', newline='\n')
    verify_matrix(output, replay=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-report', type=Path)
    parser.add_argument('--body-report', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--matrix-report', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--experiment', choices=('direction', 'baked'), default='direction')
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.verify:
        verify_matrix(args.output, args.replay)
        return
    if args.matrix_report:
        if args.review is None or args.project is None:
            parser.error('--matrix-report requires --review and --project')
        freeze_matrix(args.matrix_report, args.review, args.project, args.output, args.experiment)
        return
    if any(value is None for value in (args.native_report, args.body_report, args.review, args.candidate)):
        parser.error('The original shelf package requires both reports, review and candidate')
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

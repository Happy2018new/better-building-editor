"""Preserve actual GPU input captures and replay their byte analysis offline."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output, replay):
    manifest = json.loads((output/'manifest.json').read_bytes())
    actual = {path.relative_to(output).as_posix(): digest(path)
              for path in output.rglob('*')
              if path.is_file() and path != output/'manifest.json' and '__pycache__' not in path.parts}
    if manifest != actual:
        raise ValueError('Shelf input package bytes differ from their manifest')
    if replay:
        native_light = json.loads((output/'index.json').read_bytes()).get('diagnostic_kind') == 'native_fragment_light'
        analyzer = ('analyze_shelf_native_light_r21.py' if native_light else
                    'analyze_shelf_light_inputs_r21.py')
        result_name = 'native-light.json' if native_light else 'inputs.json'
        with tempfile.TemporaryDirectory(prefix='shelf-input-replay-') as directory:
            destination = Path(directory)/'review'
            command = [sys.executable, '-B', '-X', 'utf8', str(output/'sources'/analyzer),
                       str(output/'captures/report.json')]
            if native_light:
                command.append(str(output/'diagnostic-inputs/shelf-native-light-contract.json'))
            subprocess.run(command + [str(destination)],
                check=True, stdout=subprocess.PIPE)
            if json.loads((destination/result_name).read_bytes()) != json.loads(
                    (output/'review'/result_name).read_bytes()):
                raise ValueError('Shelf input byte analysis differs')
            for path in destination.glob('*.png'):
                from PIL import Image, ImageChops
                with Image.open(path) as first, Image.open(output/'review'/path.name) as second:
                    if first.size != second.size or ImageChops.difference(first, second).getbbox():
                        raise ValueError('Shelf input review pixels differ: '+path.name)
    print(json.dumps({'manifest_files': len(actual), 'pixels_replayed': replay,
                      'production_qualified': False}))


def pack(report_path, review, project, lifecycle, output):
    from pack_shelf_body_evidence_r18 import freeze

    report = json.loads(report_path.read_bytes())
    native_light = (review/'native-light.json').is_file()
    result_name = 'native-light.json' if native_light else 'inputs.json'
    analysis = json.loads((review/result_name).read_bytes())
    if analysis['source_report_sha256'] != digest(report_path):
        raise ValueError('GPU input analysis refers to another capture report')
    if (not native_light and not report.get('shader_inputs')) or report.get('source_unchanged') is not True:
        raise ValueError('Completed GPU input captures must bind unchanged sources')
    for relative, expected in report['source_sha256'].items():
        if digest(project/relative) != expected:
            raise ValueError('Acquisition project changed: '+relative)
    output.mkdir(parents=True, exist_ok=False)
    observation = freeze(report_path, output/'captures', sorted(report['captures']))
    shutil.copytree(review, output/'review')
    shutil.copytree(report_path.parent/'host_sources', output/'acquisition-hosts')
    if digest(output/'acquisition-hosts/probe_shelf_body_matrix_r20.py') != report['host_sha256']:
        raise ValueError('Acquisition host does not match its report')
    filenames = ('analyze_shelf_light_inputs_r21.py', 'analyze_shelf_body_matrix_r20.py',
                     'prepare_shelf_light_inputs_r21.py', 'verify_shelf_light_inputs_r21.py',
                     'pack_shelf_light_inputs_r21.py')
    if native_light:
        filenames += ('analyze_shelf_native_light_r21.py', 'prepare_shelf_native_light_r21.py',
                      'verify_shelf_native_light_r21.py')
    for filename in filenames:
        target = output/'sources'/filename
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT/'tools'/filename, target)
    material = ('terrain.material' if report.get('shader_inputs', {}).get('route') == 'mesh' else
                'entity.material')
    diagnostic_inputs = ('shelf-input-contract.json',
            'resource_pack/shaders/glsl/modern_projection_shelf_inputs.vertex',
            'resource_pack/shaders/glsl/modern_projection_shelf_inputs.fragment',
            'resource_pack/materials/'+material)
    if native_light:
        diagnostic_inputs = ('shelf-native-light-contract.json',
            'resource_pack/shaders/glsl/modern_projection_shelf_native_light.fragment',
            'resource_pack/materials/entity.material')
        if analysis['contract_sha256'] != digest(project/diagnostic_inputs[0]):
            raise ValueError('Native light readback refers to another diagnostic contract')
    for relative in diagnostic_inputs:
        target = output/'diagnostic-inputs'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project/relative, target)
    for source in lifecycle:
        target = output/'lifecycle'/source.name
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            raise ValueError('Lifecycle filenames must be distinct')
        shutil.copy2(source, target)
    index = {'production_qualified': False, 'observation': observation,
             'diagnostic_kind': 'native_fragment_light' if native_light else 'combined_mesh_or_actor',
             'flag_readback_valid': analysis.get('flag_readback_valid', analysis.get('readback_valid')),
             'shader_inputs': report.get('shader_inputs'),
             'limits': ['Input colors are captured bytes, not HDR or lighting acceptance.',
                        'Center samples use fixed ROIs without alignment or color fitting.',
                        'Only diagnostic shader inputs are copied, not a full runnable project.']}
    (output/'index.json').write_text(json.dumps(index, indent=2)+'\n', encoding='ascii', newline='\n')
    (output/'README.md').write_text(
        '# Shelf GPU input diagnostic\n\n'
        'Original captures, receipts, acquisition hosts, diagnostic resources and fixed-ROI '
        'analysis are preserved. Capture completion does not establish shader selection or '
        'uniform delivery. The flag readback validity is ' +
        str(index['flag_readback_valid']).lower() + '. Production qualification remains false.\n\n'
        + ('This fragment-only entity_static override did not select the native shelf. '
           'The actual shelf retains wood artwork, not diagnostic stripes. Fixed-ROI '
           'texture bytes are not light or flag measurements. No west expansion was run. '
           'The native vertex shader and vertex fields were unchanged.\n\n'
           if native_light and not analysis['readback_valid'] else '') +
        'Replay from any directory with `python -I -B PACKAGE/sources/'
        'pack_shelf_light_inputs_r21.py --output PACKAGE --verify --replay`. '
        'Pillow and NumPy are required. No game or checkout is used during replay.\n',
        encoding='ascii', newline='\n')
    manifest = {path.relative_to(output).as_posix(): digest(path)
                for path in output.rglob('*') if path.is_file()}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='ascii', newline='\n')
    verify(output, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--lifecycle', type=Path, nargs='*', default=[])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(args.output, args.replay)
    else:
        if any(value is None for value in (args.report, args.review, args.project)):
            parser.error('Packing requires --report, --review and --project')
        pack(args.report, args.review, args.project, args.lifecycle, args.output)

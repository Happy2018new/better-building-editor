"""Archive and independently replay the completed shelf Skeleton and terrain inputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DETAIL_LABELS = ('native', 'empty', 'selector', 'document_normal', 'world_normal',
                 'intensity', 'tile_light', 'unlit', 'candidate')
FLAGS = (('FANCY', 'FOG', 'ALWAYS_LIT', 'ALPHA_TEST'),
         ('BLEND', 'SEASONS', 'SEASONS_FAR', 'ALLOW_FADE'),
         ('TEXEL_AA', 'ATLAS_TEXTURE', 'TEXEL_AA_FEATURE', 'AS_ENTITY_RENDERER'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True)+'\n',
                    encoding='ascii', newline='\n')


def normalized(value):
    return json.loads(json.dumps(value))


def skeleton_review(captures, direction):
    base = captures/(direction+'-details')
    images = {name: Image.open(base/(name+'.png')).convert('RGB') for name in DETAIL_LABELS}
    try:
        if len({image.size for image in images.values()}) != 1:
            raise ValueError('Raw detail dimensions differ')
        width, height = images['selector'].size
        points = [(x, y) for y in range(height) for x in range(width)
                  if (lambda c: c[0] >= 220 and c[1] <= 24 and c[2] >= 220)(images['selector'].getpixel((x, y)))]
        if not points:
            raise ValueError('The actual selector mask is empty')
        colors = {name: [{'rgb': rgb, 'pixels': count} for rgb, count in
                        Counter(image.getpixel(point) for point in points).most_common(12)]
                  for name, image in images.items()
                  if name not in ('native', 'empty', 'selector', 'unlit', 'candidate')}
        means = {name: [sum(image.getpixel(point)[channel] for point in points)/len(points)
                        for channel in range(3)] for name in ('native', 'unlit', 'candidate')
                 for image in (images[name],)}
        sample_points = [(950, 440), (940, 460), (930, 540), (1000, 587), (1000, 615)] if direction == 'south' else []
        return normalized({'direction': direction, 'actual_raw_images_opened_by_shelf_agent': True,
            'source_report_sha256': digest(base/'report.json'),
            'raw_sha256': {name: digest(base/(name+'.png')) for name in DETAIL_LABELS},
            'selector_pixels': len(points),
            'selector_bounds': [min(x for x, y in points), min(y for x, y in points),
                                max(x for x, y in points)+1, max(y for x, y in points)+1],
            'normal_and_factor_colors_on_actual_selector_mask': colors,
            'mean_rgb_on_actual_selector_mask': means,
            'sample_points': [{'point': point, 'rgb': {name: image.getpixel(point) for name, image in images.items()}}
                              for point in sample_points],
            'conclusion': 'Selector/body pose and normal diagnostic path received. Candidate wood remains visibly brighter than native.',
            'production_qualified': False,
            'limits': ['Means use the actual selector mask and are descriptive, not appearance acceptance.',
                       'Native COLOR/lightmap are not inferred from candidate actor TILE or entity fancy formula.',
                       'South alone does not establish rotated-world normals; review west independently.']})
    finally:
        for image in images.values():
            image.close()


def terrain_review(captures):
    base = captures/'south-inputs'
    with Image.open(base/'native.png').convert('RGB') as native, Image.open(base/'empty.png').convert('RGB') as empty:
        if native.size != (1994, 1105) or empty.size != native.size:
            raise ValueError('The reviewed input framing changed')
        bounds = (912, 438, 1088, 455)
        slots = []
        for slot in range(8):
            points = [(x, y) for y in range(bounds[1], bounds[3]) for x in range(bounds[0], bounds[2])
                      if x//16 % 8 == slot]
            if any(empty.getpixel(point) != (171, 210, 255) for point in points):
                raise ValueError('The strict body ROI is no longer entirely sky in the empty image')
            slots.append({'slot': slot, 'pixels': len(points), 'rgb_counts': [
                {'rgb': rgb, 'pixels': count} for rgb, count in
                Counter(native.getpixel(point) for point in points).most_common()]})
        rows = [{'y': y, 'color_left': native.getpixel((920, y)), 'color_right': native.getpixel((1048, y)),
                 'lightmap_left': native.getpixel((952, y)), 'lightmap_right': native.getpixel((1080, y)),
                 'flags': native.getpixel((984, y)), 'final_rgb': native.getpixel((1016, y))}
                for y in (440, 446, 450, 460, 470, 480, 490, 500, 510, 520, 530, 540, 550, 560, 570, 580, 585, 590, 600, 610, 620, 630)]
        markers = [(1032, 450, (255, 255, 0)), (936, 450, (255, 0, 255)),
                   (968, 450, (0, 255, 255)), (1000, 450, (255, 255, 255))]
        if any(native.getpixel((x, y)) != expected for x, y, expected in markers):
            raise ValueError('One of the four body marker/data pairs changed')
        flag_rgb = native.getpixel((984, 450))
        if any(value % 17 for value in flag_rgb):
            raise ValueError('Flags are not exact nibble bytes')
        names = [name for channel, value in zip(FLAGS, flag_rgb) for bit, name in enumerate(channel)
                 if value//17 & (1 << bit)]
    return normalized({'schema_version': 1, 'actual_both_raw_images_opened': True,
        'capture_report_sha256': digest(base/'report.json'),
        'raw_sha256': {name: digest(base/name) for name in ('native.png', 'empty.png')},
        'strict_body_sky_roi': bounds, 'strict_body_slots': slots, 'interior_marker_points': markers,
        'body_vertical_samples': rows, 'actual_flag_rgb': flag_rgb, 'actual_defined_flags': names,
        'conclusion': 'The native shelf body reads actual interpolated COLOR and texture1 lightmap; COLOR varies with height, while sampled lightmap is 237/255 neutral.',
        'production_qualified': False,
        'limits': ['This draw only, south oak unpowered over the fixture support.',
                   'COLOR is a baked/interpolated varying, not a constant per-face scalar.',
                   'No scalar fit or assumed equivalence between actor TILE and terrain lightmap follows.']})


def verify_package(output):
    index = load(output/'index.json')
    present = {path.relative_to(output).as_posix() for path in output.rglob('*')
               if path.is_file() and path.relative_to(output).as_posix() != 'index.json'}
    if present != set(index['sha256']):
        raise ValueError('The portable file set changed')
    for name, expected in index['sha256'].items():
        if digest(output/name) != expected:
            raise ValueError('Portable bytes changed: '+name)
    freeze_path = output/'records/frozen.json'
    freeze = load(freeze_path)
    for name, expected in freeze['host_sources'].items():
        if digest(output/'host'/name) != expected:
            raise ValueError('A packaged host differs from its frozen hash: '+name)
    frozen_rows = {row['path']: row['sha256'] for row in freeze['files']}
    expected_images = 24 if index['kind'] == 'skeleton-v1' else 2
    if len(list((output/'captures').glob('*/*.png'))) != expected_images:
        raise ValueError('The raw acquisition image count changed')
    for report_path in sorted((output/'captures').glob('*/report.json')):
        report = load(report_path)
        if not all(report[key] for key in ('completed', 'restored', 'source_unchanged')) or report['cleanup_errors']:
            raise ValueError('A raw acquisition did not complete and restore')
        if report['production_qualified'] is not False:
            raise ValueError('An original acquisition was relabeled as production qualified')
        if index['kind'] == 'terrain-inputs-v4' and report['frozen_manifest_sha256'] != digest(freeze_path):
            raise ValueError('Terrain acquisition freeze binding changed')
        if index['kind'] == 'skeleton-v1':
            if any(frozen_rows.get(name) != expected for name, expected in report['source_sha256'].items()):
                raise ValueError('Skeleton acquisition source differs from its frozen rows')
            if report['host_sha256'] != freeze['host_sources']['tools/probe_shelf_skeleton_world_r21.py']:
                raise ValueError('Skeleton acquisition host differs from its frozen source')
    for relative in freeze.get('overlay_changed_paths', freeze.get('changed_paths', [])):
        row = next(row for row in freeze['files'] if row['path'] == relative)
        if digest(output/'overlay'/relative) != row['sha256']:
            raise ValueError('The packaged overlay does not match its frozen resource')
    if index['kind'] == 'skeleton-v1':
        for direction in ('south', 'west'):
            if skeleton_review(output/'captures', direction) != load(output/'reviews'/(direction+'-independent-detail-review.json')):
                raise ValueError('Independent Skeleton pixel replay differs: '+direction)
        contract = load(output/'candidate/contract.json')
        if digest(output/'candidate/contract.json') != freeze['asset_contract_sha256']:
            raise ValueError('Skeleton candidate contract differs from the frozen record')
        for name, expected in contract['output_sha256'].items():
            if digest(output/'candidate'/name) != expected:
                raise ValueError('Original candidate asset changed: '+name)
    else:
        if terrain_review(output/'captures') != load(output/'reviews/body-input-review.json'):
            raise ValueError('Independent terrain input replay differs')
        compiler = load(output/'records/compile.json')
        if not compiler['passed'] or compiler['frozen_manifest_sha256'] != digest(freeze_path):
            raise ValueError('Compiler receipt is not bound to this freeze')
        source_path = output/'records/frozen-source-v3.json'
        if digest(source_path) != freeze['source_freeze_sha256']:
            raise ValueError('The parent route freeze binding changed')
        source = load(source_path)
        native_root = Path(next(name for name in source['native_sources'] if name.endswith('renderchunk.fragment'))).parents[2]
        for name, expected in source['native_sources'].items():
            if digest(output/'native'/Path(name).relative_to(native_root)) != expected:
                raise ValueError('A packaged native source differs from the route freeze')
        for name, expected in freeze['evidence_sha256'].items():
            relative = name if name.startswith('route-evidence/') else 'records/'+name
            if digest(output/relative) != expected:
                raise ValueError('A frozen input diagnostic resource changed: '+name)
    exact = load(output/'lifecycle/exact-exit.json')
    session = load(output/'lifecycle/session-stopped-redacted.json')
    if not exact['completed'] or any(row['state'] != 'exited' for row in exact['processes'].values()):
        raise ValueError('The exact exit observer is incomplete')
    if session['state'] != 'stopped' or session['id'] != exact['session'] or session['owner'] != exact['owner'] or 'token' in session:
        raise ValueError('The redacted stopped session identity differs')
    for key in ('game', 'mcdk'):
        if any(session[key+'_'+field] != exact['processes'][key][field] for field in ('pid', 'identity')):
            raise ValueError('The stopped process identity differs')
    return {'verified': True, 'kind': index['kind'], 'files': len(present),
            'raw_images': len(list((output/'captures').glob('*/*.png'))),
            'production_qualified': False, 'package_index_sha256': digest(output/'index.json')}


def pack(kind, control, output, facts):
    if output.exists():
        raise ValueError('Choose a fresh package directory')
    freeze = load(control/'frozen.json')
    project = Path(freeze['project'])
    for row in freeze['files']:
        if digest(project/row['path']) != row['sha256']:
            raise ValueError('Frozen runtime resource changed: '+row['path'])
    for name, expected in freeze['host_sources'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Frozen host source changed: '+name)
    output.mkdir(parents=True)
    (output/'.gitattributes').write_text('** -text -diff whitespace=cr-at-eol\n', encoding='ascii', newline='\n')

    def copy(source, relative):
        destination = output/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    for path in sorted((control/'captures').rglob('*')):
        if path.is_file():
            copy(path, 'captures/'+path.relative_to(control/'captures').as_posix())
    copy(control/'frozen.json', 'records/frozen.json')
    copy(control/'RUN.md', 'records/prepared-run-plan.md')
    for name in freeze['host_sources']:
        copy(ROOT/name, 'host/'+name)
    copy(Path(__file__), 'host/tools/'+Path(__file__).name)
    for name in freeze.get('overlay_changed_paths', freeze.get('changed_paths', [])):
        copy(project/name, 'overlay/'+name)
    if kind == 'skeleton-v1':
        candidate = ROOT/'.runtime/shelf-skeleton-r21-v1'
        for path in sorted(candidate.rglob('*')):
            if path.is_file():
                copy(path, 'candidate/'+path.relative_to(candidate).as_posix())
        for direction in ('south', 'west'):
            for suffix in ('review.json', 'independent-detail-review.json'):
                copy(control/(direction+'-'+suffix), 'reviews/'+direction+'-'+suffix)
        for name in ('normal-stop.json', 'normal-finalize.json'):
            copy(control/name, 'lifecycle/'+name)
        for name in ('generate_shelf_skeleton_resources_r21.py', 'verify_shelf_skeleton_r21.py'):
            copy(ROOT/'tools'/name, 'host/tools/'+name)
        copy(ROOT/'tests/test_shelf_skeleton_r21.py', 'host/tests/test_shelf_skeleton_r21.py')
    else:
        for name in ('compile.json', 'fragment-before.txt', 'fragment-after.txt', 'fragment.patch', 'NEXT.md'):
            copy(control/name, 'records/'+name)
        source = Path(freeze['source_freeze'])
        if digest(source) != freeze['source_freeze_sha256']:
            raise ValueError('Frozen source route manifest changed')
        copy(source, 'records/frozen-source-v3.json')
        for path in sorted((control/'route-evidence').rglob('*')):
            if path.is_file():
                copy(path, 'route-evidence/'+path.relative_to(control/'route-evidence').as_posix())
        native = ROOT/'docs/evidence/shelf-native-route-r21-v3/native'
        for path in sorted(native.rglob('*')):
            if path.is_file():
                copy(path, 'native/'+path.relative_to(native).as_posix())
        copy(control/'body-input-review.json', 'reviews/body-input-review.json')
        copy(ROOT/'tools/verify_biome_shader.py', 'host/tools/verify_biome_shader.py')
        copy(ROOT/'tests/test_shelf_terrain_inputs_r21.py', 'host/tests/test_shelf_terrain_inputs_r21.py')
    for name in ('start-summary.json', 'exact-exit.json'):
        copy(control/'launch'/name, 'lifecycle/'+name)
    session_path = Path(load(control/'launch/start-summary.json')['session_file'])
    session = load(session_path)
    if session['state'] != 'stopped':
        raise ValueError('The owned runtime has not been finalized')
    session.pop('token', None)
    write(output/'lifecycle/session-stopped-redacted.json', session)
    write(output/'lifecycle/session-provenance.json', {'original_path': str(session_path),
        'original_sha256': digest(session_path), 'redacted_top_level_keys': ['token'],
        'scope': 'Stopped-session snapshot; local authentication token omitted.'})
    copy(facts, 'lifecycle/facts.json')
    write(output/'index.json', {'schema_version': 1, 'kind': kind,
        'scope': 'Slim immutable diagnostic evidence; no full BP/RP or source tar; not appearance acceptance.',
        'replay': 'python -B -X utf8 host/tools/pack_shelf_input_evidence_r21.py verify --package .',
        'sha256': {path.relative_to(output).as_posix(): digest(path) for path in sorted(output.rglob('*')) if path.is_file()}})
    return verify_package(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    archive = actions.add_parser('pack')
    archive.add_argument('--kind', choices=('skeleton-v1', 'terrain-inputs-v4'), required=True)
    archive.add_argument('--control', type=Path, required=True)
    archive.add_argument('--output', type=Path, required=True)
    archive.add_argument('--facts', type=Path, required=True)
    verify = actions.add_parser('verify')
    verify.add_argument('--package', type=Path, required=True)
    refresh = actions.add_parser('refresh-verifier')
    refresh.add_argument('--package', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'refresh-verifier':
        index_path = args.package/'index.json'
        index = load(index_path)
        for name, expected in index['sha256'].items():
            if digest(args.package/name) != expected:
                raise ValueError('Refusing to refresh changed evidence: '+name)
        target = args.package/'host/tools'/Path(__file__).name
        shutil.copyfile(Path(__file__), target)
        index['sha256'][target.relative_to(args.package).as_posix()] = digest(target)
        write(index_path, index)
        result = verify_package(args.package)
    elif args.action == 'verify':
        result = verify_package(args.package)
    else:
        result = pack(args.kind, args.control, args.output, args.facts)
    print(json.dumps(result))


if __name__ == '__main__':
    main()

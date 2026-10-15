"""Prepare one overlay atlas and replay an incomplete native holdout offline."""
import argparse
import copy
import difflib
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FROZEN = Path(__file__).resolve().parent / 'sources/analysis/tools'
if FROZEN.is_dir():
    sys.path.insert(0, str(FROZEN))
from archive_frame_block_evidence_r21 import (
    compare, contained, digest, import_closure, sanitize, write_json)


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert digest(source) == digest(destination)


def candidate(project, control, install, output):
    import generate_frame_block_items as generator
    from item_sprite_capture_contract import snapshot_digest, snapshot_sources

    plan = json.loads((control / 'plan.json').read_bytes())
    before = snapshot_sources(project)
    assert snapshot_digest(before) == plan['source_sha256']
    catalog_path = project / 'tools/data/frame_block_item_catalog_nemc_3.10.0.420447.json'
    catalog = json.loads(catalog_path.read_bytes())
    affected = {key: value for key, value in catalog['resources'].items()
        if any('overlay_color' in generator.texture_entry(face['entry'])
               for face in value['faces'].values())}
    rows = [row for row in catalog['items'] if row['resource'] in affected]
    assert [(row['name'], row['aux']) for row in rows] == [('minecraft:grass_block', 0)]
    packs, blocks, terrain, unused_sources = generator.source_records(install)
    output.mkdir(parents=True, exist_ok=False)
    key, resource = next(iter(affected.items()))
    assert blocks[resource['definition_key']] == resource['definition']
    images, native = {}, {}
    for face, saved in resource['faces'].items():
        images[face], current = generator.resolve_face(packs, terrain, saved['atlas_key'])
        assert current == saved, face
        source = packs / saved['path']
        copy_file(source, output / 'native' / saved['path'])
        native[saved['path']] = digest(source)
    for relative in ('vanilla/blocks.json', 'vanilla/textures/terrain_texture.json'):
        copy_file(packs / relative, output / 'native' / relative)
        native[relative] = digest(packs / relative)
    bitmap, rectangles = generator.atlas_image(images)
    assert rectangles == resource['rectangles']
    relative = 'resource_pack/textures/models/' + generator.ASSET + '/' + key + '.png'
    assert digest(project / relative) == resource['bitmap_sha256']
    copy_file(project / relative, output / 'original' / relative)
    target = output / 'override' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(bitmap)
    old = np.array(Image.open(project / relative).convert('RGBA'))
    new = np.array(Image.open(BytesIO(bitmap)).convert('RGBA'))
    assert old.shape == new.shape and not np.array_equal(old, new)
    unchanged = np.ones(old.shape[:2], dtype=bool)
    diagnostics = {}
    for face, saved in resource['faces'].items():
        u0, v0, u1, v1 = rectangles[face]
        x0, y0, x1, y1 = (round(u0 * old.shape[1]), round(v0 * old.shape[0]),
                          round(u1 * old.shape[1]), round(v1 * old.shape[0]))
        entry = generator.texture_entry(saved['entry'])
        if 'overlay_color' not in entry:
            assert np.array_equal(old[y0-1:y1+1, x0-1:x1+1], new[y0-1:y1+1, x0-1:x1+1])
            continue
        unchanged[y0-1:y1+1, x0-1:x1+1] = False
        source = np.array(Image.open(packs / saved['path']).convert('RGBA'))
        alpha = source[:, :, 3]
        assert set(np.unique(alpha)) == {0, 255}
        original = source.astype(float)
        mask = original[:, :, 3:4] / 255.
        original[:, :, :3] *= mask + (1. - mask) * generator.color(entry['overlay_color'])
        original[:, :, 3] = 255
        assert np.array_equal(np.rint(original).astype(np.uint8), old[y0:y1, x0:x1])
        corrected = new[y0:y1, x0:x1]
        assert np.array_equal(corrected[alpha == 0, :3], source[alpha == 0, :3])
        tinted = np.rint(source[alpha == 255, :3] * generator.color(entry['overlay_color'])).astype(np.uint8)
        assert np.array_equal(corrected[alpha == 255, :3], tinted)
        assert np.all(corrected[:, :, 3] == 255)
        diagnostics[face] = {'alpha_zero_untinted_pixels': int((alpha == 0).sum()),
            'alpha_255_tinted_pixels': int((alpha == 255).sum()),
            'old_atlas_wrong_polarity_reproduced': True,
            'hidden_base_rgb_preserved': True, 'result_opaque': True}
    assert np.array_equal(old[unchanged], new[unchanged])
    side = resource['faces']['north']
    raw = Image.open(packs / side['path']).convert('RGBA')
    alpha = raw.getchannel('A').convert('RGB')
    u0, v0, u1, v1 = rectangles['north']
    box = (round(u0 * old.shape[1]), round(v0 * old.shape[0]),
           round(u1 * old.shape[1]), round(v1 * old.shape[0]))
    panels = [raw.convert('RGB'), alpha, Image.fromarray(old).crop(box).convert('RGB'), images['north'].convert('RGB')]
    preview = Image.new('RGB', (1024, 300), 'white')
    draw = ImageDraw.Draw(preview)
    for index, (label, panel) in enumerate(zip(('Source RGB', 'Source alpha', 'Captured wrong recipe', 'Candidate, not accepted'), panels)):
        draw.text((index * 256 + 4, 8), label, fill='black')
        preview.paste(panel.resize((256, 256), Image.Resampling.NEAREST), (index * 256, 40))
    preview.save(output / 'overlay-source-comparison.png')
    original_generator = project / 'tools/generate_frame_block_items.py'
    corrected_generator = Path(generator.__file__)
    for name, path in (('original-generator.py', original_generator), ('corrected-generator.py', corrected_generator)):
        copy_file(path, output / name)
    patch = ''.join(difflib.unified_diff(original_generator.read_text(encoding='utf-8').splitlines(True),
        corrected_generator.read_text(encoding='utf-8').splitlines(True),
        fromfile='original/generate_frame_block_items.py', tofile='corrected/generate_frame_block_items.py'))
    (output / 'generator.diff').write_text(patch, encoding='ascii')
    metadata = {'schema': 1, 'production_qualified': False, 'appearance_accepted': False,
        'native_pixels_accepted': False, 'base_light_general_acceptance': False,
        'source_sha256': plan['source_sha256'], 'source_unchanged': True,
        'catalog_sha256': digest(catalog_path), 'affected_resources': len(affected),
        'affected_items': [[row['name'], row['aux']] for row in rows],
        'affected_profiles': 1, 'resource_key': key, 'resource': resource,
        'changed_resource_paths': [relative], 'original_bitmap_sha256': resource['bitmap_sha256'],
        'candidate_bitmap_sha256': hashlib.sha256(bitmap).hexdigest(),
        'generator_sha256': digest(corrected_generator), 'native_source_sha256': native,
        'endpoint_checks': diagnostics,
        'unmodified': ['top and bottom tiles and padding', 'UV rectangles', 'all meshes',
            'all shaders including empirical 0.93', 'glint', 'production catalog and profile'],
        'semantics': 'overlay alpha=0 preserves hidden RGB; alpha=255 multiplies RGB by overlay_color; output alpha=255',
        'limits': ['Only installed binary-alpha endpoints are established; intermediate alpha is unverified',
            'Wiki prose describes alpha-controlled tint, but its formula omits an alpha multiplier on the tint term',
            'No candidate screenshot exists; the old native pixels failed and are not corrected',
            'One successful top ROI does not establish a universal 0.93 lighting factor']}
    assert snapshot_sources(project) == before
    write_json(output / 'candidate.json', metadata)
    return {key: metadata[key] for key in ('affected_items', 'changed_resource_paths', 'candidate_bitmap_sha256', 'production_qualified')}


def review(report, pose, output):
    import analyze_frame_block_multiview_r21 as geometry
    import analyze_frame_block_appearance_r21 as appearance
    from camera_projection import project_points
    from analyze_liquid_workspace import capture_failures
    captures = {row['label']: row for row in report['captures']}
    cases = [row for row in report['cases'] if row.get('measurement_completed')]
    assert len(cases) == 1 and cases[0]['source']['item'] == ['minecraft:grass_block', 0]
    assert cases[0]['native_reference']['restored']
    output.mkdir(parents=True, exist_ok=False)
    result = {'cases': [], 'geometry_thresholds': geometry.LIMITS}
    for case in cases:
        identity, routes = case['id'], ('native', 'full', 'missing')
        subset = {label: row['capture'] for label, row in captures.items()
            if any(label == identity + '_' + route + '_' + control
                   for route in routes for control in ('hidden_before', 'shown', 'hidden_after'))}
        assert len(subset) == 9 and not capture_failures(subset, report['session'])
        fov = report['camera_calibration']['vertical_fov']
        views = {route: geometry.observe(case, route, captures, fov) for route in routes}
        common = np.logical_and.reduce([views[route]['mask'] for route in routes])
        native = views['native']
        regions = appearance.face_regions(native['position'], pose, native['camera'], native['size'], fov, common, project_points)
        images = {route: Image.fromarray(views[route]['shown'].astype(np.uint8)) for route in routes}
        row = {'angle': case['source']['view_angle_degrees'], 'images': images, 'mask': common, 'regions': regions}
        item = case['source']['item'][0].split(':')[-1]
        appearance.draw_montage([row], output / (item + '-native-full-missing.png'))
        appearance.draw_montage([row], output / (item + '-face-rois.png'), annotated=True)
        measured = {'id': identity, 'item': case['source']['item'], 'angle': row['angle'],
            'native_reference_restored': True,
            'paired_filled_silhouettes': {route: geometry.paired(native, views[route]) for route in ('full', 'missing')},
            'unfilled_differences': {}, 'faces': {}}
        raw_masks = {}
        for route, view in views.items():
            before = geometry.rgb(captures[identity + '_' + route + '_hidden_before']['capture']['path'])
            after = geometry.rgb(captures[identity + '_' + route + '_hidden_after']['capture']['path'])
            envelope = np.zeros(common.shape, dtype=bool)
            envelope[view['lo'][1]:view['hi'][1], view['lo'][0]:view['hi'][0]] = True
            stable = np.max(np.abs(before - after), axis=2) <= 3
            raw = geometry.difference_mask(view['shown'], (before.astype(float) + after)/2., envelope, 8) & stable
            raw_masks[route] = raw
            measured['unfilled_differences'][route] = {'pixels': int(raw.sum()),
                'filled_pixels': int(view['mask'].sum()), 'filled_extra_pixels': int((view['mask'] & ~raw).sum())}
            Image.fromarray(raw).save(output / (item + '-' + route + '-unfilled-mask.png'))
            Image.fromarray(view['mask']).save(output / (item + '-' + route + '-filled-mask.png'))
        measured['paired_unfilled_iou'] = {route: float((raw_masks['native'] & raw_masks[route]).sum()
            / max(1, int((raw_masks['native'] | raw_masks[route]).sum()))) for route in ('full', 'missing')}
        for face, region in regions.items():
            mask = region['mask']
            pixels = {route: views[route]['shown'][mask].astype(np.uint8) for route in routes}
            measured['faces'][face] = {'roi_pixels': int(mask.sum()), 'large_roi': int(mask.sum()) >= 64,
                'routes': {route: appearance.color_summary(values) for route, values in pixels.items()},
                'native_product': {route: appearance.color_pair(pixels['native'], pixels[route]) for route in ('full', 'missing')}}
            Image.fromarray(mask).save(output / (item + '-' + face + '-roi.png'))
        result['cases'].append(measured)
    write_json(output / 'review.json', result)
    return result


def build(source, control, project, analysis, overlay, readme, output):
    from item_sprite_capture_contract import snapshot_sources, snapshot_digest
    raw = json.loads(source.read_bytes())
    assert not raw['completed'] and raw['source_unchanged'] and not raw['cleanup_errors']
    assert raw['launch_sources'] == raw['sources_after'] == snapshot_sources(project)
    assert snapshot_digest(raw['launch_sources']) == raw['launch_sources_sha256']
    expected = json.loads((analysis / 'review.json').read_bytes())
    assert expected['source_report_sha256'] == digest(source)
    session = {key: raw['session'][key] for key in
        ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
    session['session_file'] = 'session:' + session['id']
    output.mkdir(parents=True, exist_ok=False)
    receipts = [row['capture'] for row in raw['captures']]
    receipts += [row[mode] for row in raw['camera_calibration']['views'] for mode in ('shown', 'hidden')]
    assert len(raw['captures']) == 18 and len(receipts) == 24
    paths = {}
    for receipt in receipts:
        original = Path(receipt['path'])
        assert digest(original) == receipt['sha256']
        relative = 'captures/' + original.name
        assert relative not in paths.values()
        copy_file(original, output / relative)
        paths[str(original)] = relative
    report = copy.deepcopy(raw)
    report['session'] = session
    report = sanitize(report, session, paths)
    write_json(output / 'report.json', report)
    copy_file(readme, output / 'README.md')
    copy_file(Path(__file__), output / 'replay.py')
    for path in analysis.iterdir():
        if path.suffix == '.png' or path.name == 'review.json':
            copy_file(path, output / 'analysis' / path.name)
    shutil.copytree(overlay, output / 'overlay-candidate')
    prior = ROOT / 'docs/evidence/frame-block-appearance-r21-v1'
    prior_manifest = json.loads((prior / 'manifest.json').read_bytes())
    for relative, expected_hash in prior_manifest['files'].items():
        if relative.startswith('sources/'):
            assert digest(prior / relative) == expected_hash
            copy_file(prior / relative, output / 'sources/analysis' / relative.removeprefix('sources/'))
    capture_entries = ['tools/frame_block_light_r21_host.py', 'tools/run_visible_items_r16.py']
    for relative in sorted(import_closure(project, capture_entries)):
        assert digest(project / relative) == raw['launch_sources'][relative]
        copy_file(project / relative, output / 'sources/capture' / relative)
    for relative in sorted(import_closure(ROOT, ['tools/generate_frame_block_items.py'])):
        copy_file(ROOT / relative, output / 'sources/generator' / relative)
    selected = ('plan.json', 'candidate.json', 'source-textures.json', 'launch-preflight.json',
        'launch-attempt.json', 'ready-summary.json', 'external-observer-amendment.json',
        'exact-exit.json', 'normal-stop-journal.json', 'noon-grass-log.json',
        'noon-grass-log-attempt.json', 'noon-grass-log-environment.json', 'noon-grass-log-outcome.json')
    for name in selected:
        copy_file(control / name, output / 'control' / name)
    for name in ('start.stderr.txt', 'exit-watch.stderr.txt'):
        copy_file(control / name, output / 'control' / name)
    for name in ('frame_block_light_r21_run.py', 'frame_block_light_r21_review.py'):
        copy_file(ROOT / '.runtime' / name, output / 'hosts' / name)
    observer = ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'
    amendment = json.loads((control / 'external-observer-amendment.json').read_bytes())
    assert digest(observer) == amendment['observer_sha256']
    copy_file(observer, output / 'hosts/watch_intrinsic_glint_exit_r21.py')
    for relative in raw['candidate_geometry']['data']['files']:
        assert digest(project / relative) == raw['launch_sources'][relative]
        copy_file(project / relative, output / 'captured-resources' / relative)
    for row in json.loads((control / 'source-textures.json').read_bytes()).values():
        copy_file(project / row['atlas'], output / 'captured-resources' / row['atlas'])
    (output / '.gitattributes').write_text('* -text -whitespace\n', encoding='ascii')
    files = {path.relative_to(output).as_posix(): digest(path)
        for path in sorted(output.rglob('*')) if path.is_file()}
    write_json(output / 'manifest.json', {'schema': 1, 'production_qualified': False,
        'appearance_accepted': False, 'phase_completed': False,
        'original_report_sha256': digest(source), 'launch_sources_sha256': raw['launch_sources_sha256'],
        'raw_png_count': len(receipts), 'capture_receipt_count': len(raw['captures']),
        'completed_cases': 1, 'requested_cases': 2,
        'original_helper_manifest_sha256': digest(prior / 'manifest.json'),
        'files': files, 'archive_tool_sha256': digest(Path(__file__))})
    return {'files': len(files), 'raw_png_count': len(receipts), 'phase_completed': False,
        'production_qualified': False, 'staged': False}


def replay(bundle, output):
    from analyze_liquid_workspace import capture_failures
    from item_sprite_capture_contract import snapshot_digest
    from verify_camera_projection import analyze_calibration

    bundle = bundle.resolve()
    manifest = json.loads((bundle / 'manifest.json').read_bytes())
    actual_files = {path.relative_to(bundle).as_posix() for path in bundle.rglob('*')
        if path.is_file() and path != bundle / 'manifest.json' and '__pycache__' not in path.parts}
    assert actual_files == set(manifest['files'])
    for relative, expected_hash in manifest['files'].items():
        assert digest(contained(bundle, relative)) == expected_hash, relative
    assert digest(bundle / 'replay.py') == manifest['archive_tool_sha256']
    report = json.loads((bundle / 'report.json').read_bytes())
    assert not report['completed'] and not report['cleanup_errors'] and report['source_unchanged']
    assert report['launch_sources'] == report['sources_after']
    assert snapshot_digest(report['launch_sources']) == manifest['launch_sources_sha256']
    receipts = [row['capture'] for row in report['captures']]
    receipts += [row[mode] for row in report['camera_calibration']['views'] for mode in ('shown', 'hidden')]
    assert len(receipts) == manifest['raw_png_count'] == 24
    for receipt in receipts:
        receipt['path'] = str(contained(bundle, receipt['path']))
    assert not capture_failures({str(index): receipt for index, receipt in enumerate(receipts)}, report['session'])
    output.mkdir(parents=True, exist_ok=False)
    calibration = copy.deepcopy(report['camera_calibration'])
    for row in calibration['views']:
        row['signal'] = str(output / ('camera-' + row['view'] + '-signal.png'))
        row['outline_comparison'] = str(output / ('camera-' + row['view'] + '-outline.png'))
    analyze_calibration(calibration)
    for key in ('passed', 'vertical_fov', 'individual_fitted_vertical_fov'):
        compare(report['camera_calibration'][key], calibration[key], 'calibration/' + key)
    for expected, actual in zip(report['camera_calibration']['views'], calibration['views']):
        compare(expected['fit'], actual['fit'], 'calibration/' + actual['view'])
    pose = report['candidate_geometry']['data']['pose']
    actual = review(report, pose, output / 'analysis')
    original = json.loads((bundle / 'analysis/review.json').read_bytes())
    for key in ('cases', 'geometry_thresholds'):
        compare(original[key], actual[key], key)
    images = list((bundle / 'analysis').glob('*.png'))
    for path in images:
        assert np.array_equal(np.asarray(Image.open(path)),
            np.asarray(Image.open(output / 'analysis' / path.name))), path.name
    sys.path.insert(0, str(bundle / 'sources/generator/tools'))
    import generate_frame_block_items as generator
    overlay = bundle / 'overlay-candidate'
    metadata = json.loads((overlay / 'candidate.json').read_bytes())
    assert digest(Path(generator.__file__)) == metadata['generator_sha256']
    faces = {}
    for face in generator.FACE_VERTICES:
        saved = metadata['resource']['faces'][face]
        path = overlay / 'native' / saved['path']
        assert digest(path) == saved['sha256']
        faces[face], unused_operations = generator.bake_texture(Image.open(path), generator.texture_entry(saved['entry']))
    bitmap, rectangles = generator.atlas_image(faces)
    assert rectangles == metadata['resource']['rectangles']
    assert hashlib.sha256(bitmap).hexdigest() == metadata['candidate_bitmap_sha256']
    exit_report = json.loads((bundle / 'control/exact-exit.json').read_bytes())
    stop = json.loads((bundle / 'control/normal-stop-journal.json').read_bytes())
    assert exit_report['completed'] and stop['session_state_after_finalize'] == 'stopped' and not stop['force_used']
    for kind in ('game', 'mcdk'):
        assert exit_report['processes'][kind]['pid'] == report['session'][kind + '_pid']
        assert exit_report['processes'][kind]['identity'] == report['session'][kind + '_identity']
    result = {'schema': 1, 'replay_completed': True, 'production_qualified': False,
        'appearance_accepted': False, 'phase_completed': False, 'raw_png_count': len(receipts),
        'completed_cases': 1, 'requested_cases': 2, 'analysis_images_reproduced': len(images),
        'camera_calibration_reproduced': True, 'original_failed_pixels_reproduced': True,
        'corrected_overlay_atlas_reproduced': True,
        'exit_codes': {kind: row['exit_code_hex'] for kind, row in exit_report['processes'].items()}}
    write_json(output / 'replay.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparer = commands.add_parser('candidate')
    for name in ('project', 'control', 'install', 'output'):
        preparer.add_argument('--' + name, type=Path, required=True)
    builder = commands.add_parser('build')
    for name in ('source', 'control', 'project', 'analysis', 'overlay', 'readme', 'output'):
        builder.add_argument('--' + name, type=Path, required=True)
    replayer = commands.add_parser('replay')
    replayer.add_argument('bundle', type=Path)
    replayer.add_argument('output', type=Path)
    args = vars(parser.parse_args())
    command = args.pop('command')
    print(json.dumps({'candidate': candidate, 'build': build, 'replay': replay}[command](**args)))


if __name__ == '__main__':
    main()

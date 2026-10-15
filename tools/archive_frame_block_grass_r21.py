"""Archive and replay the three restored grass overlay holdouts without a game."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
FROZEN = Path(__file__).resolve().parent / 'sources/analysis/tools'
if FROZEN.is_dir():
    sys.path.insert(0, str(FROZEN))
from archive_frame_block_evidence_r21 import (
    compare, contained, digest, import_closure, sanitize, write_json)

PHASES = ('front', 'left75', 'right75')
SESSION_FIELDS = ('id', 'owner', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert digest(source) == digest(destination)


def receipts(report):
    return ([row['capture'] for row in report['captures']] +
            [row[mode] for row in report['camera_calibration']['views'] for mode in ('shown', 'hidden')])


def build(control, output, readme):
    from item_sprite_capture_contract import snapshot_digest, snapshot_sources
    prior = ROOT / 'docs/evidence/frame-block-light-holdout-r21-v1'
    plan = json.loads((control / 'plan.json').read_bytes())
    project = Path(plan['project'])
    assert snapshot_sources(project) == plan['sources']
    assert snapshot_digest(plan['sources']) == plan['source_sha256']
    assert digest(prior / 'manifest.json') == plan['analysis_manifest_sha256']
    output.mkdir(parents=True, exist_ok=False)
    originals = {}
    for phase in plan['phases']:
        name = phase['id']
        assert name in PHASES
        source = Path(phase['capture_output']) / 'report.json'
        raw = json.loads(source.read_bytes())
        outcome = json.loads((control / (name + '-outcome.json')).read_bytes())
        review = ROOT / ('.runtime/frame-block-grass-overlay-r21-' + name + '-review-v1')
        expected = json.loads((review / 'review.json').read_bytes())
        assert expected['source_report_sha256'] == outcome['report_sha256'] == digest(source)
        assert expected['ready'] and expected['calibration_reproduced']
        assert raw['completed'] and raw['matrix_completed'] and raw['environment_restored']
        assert raw['source_unchanged'] and not raw['cleanup_errors']
        assert raw['launch_sources'] == raw['sources_after'] == plan['sources']
        assert outcome['phase_ready_for_review'] and outcome['native_references_restored']
        session = {key: raw['session'][key] for key in SESSION_FIELDS}
        session['session_file'] = 'session:' + session['id']
        paths = {}
        assert len(receipts(raw)) == 20
        for receipt in receipts(raw):
            source_png = Path(receipt['path'])
            assert digest(source_png) == receipt['sha256']
            relative = 'captures/' + name + '/' + source_png.name
            assert relative not in paths.values()
            copy_file(source_png, output / relative)
            paths[str(source_png)] = relative
        write_json(output / 'phases' / name / 'report.json', sanitize(raw, session, paths))
        copy_file(review / 'review.json', output / 'phases' / name / 'review.json')
        for image in review.rglob('*.png'):
            copy_file(image, output / 'phases' / name / image.relative_to(review))
        originals[name] = {'report_sha256': digest(source), 'raw_png_count': 20,
                           'review_sha256': digest(review / 'review.json')}
    analysis = prior / 'sources/analysis'
    entries = ['tools/analyze_frame_block_appearance_r21.py',
               'tools/analyze_frame_block_multiview_r21.py',
               'tools/verify_camera_projection.py', 'tools/item_sprite_capture_contract.py']
    old_manifest = json.loads((prior / 'manifest.json').read_bytes())
    for relative in sorted(import_closure(analysis, entries)):
        assert digest(analysis / relative) == old_manifest['files']['sources/analysis/' + relative]
        copy_file(analysis / relative, output / 'sources/analysis' / relative)
    copy_file(prior / 'replay.py', output / 'sources/analysis/tools/archive_frame_block_light_holdout_r21.py')
    for source in (prior / 'sources/generator').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts:
            copy_file(source, output / 'sources/generator' / source.relative_to(prior / 'sources/generator'))
    candidate = json.loads((control / 'candidate.json').read_bytes())
    for relative, expected_hash in candidate['files'].items():
        assert digest(project / relative) == expected_hash == plan['sources'][relative]
        copy_file(project / relative, output / 'captured-resources' / relative)
    textures = json.loads((control / 'source-textures.json').read_bytes())
    for row in textures.values():
        for face in row['faces'].values():
            native = prior / 'overlay-candidate/native' / face['path']
            assert digest(native) == face['sha256']
            destination = output / 'native' / face['path']
            if not destination.exists():
                copy_file(native, destination)
    selected = ['plan.json', 'candidate.json', 'source-textures.json', 'ready-summary.json',
                'launch-preflight.json', 'launch-attempt.json', 'runtime-amendment-v2.json',
                'offline-amendment-checks-v2.json', 'exact-exit.json', 'normal-stop-journal.json']
    selected += [name + suffix for name in PHASES
                 for suffix in ('.json', '-attempt.json', '-environment.json', '-outcome.json',
                                '-runtime-amendment-v2.json')]
    for name in selected:
        copy_file(control / name, output / 'control' / name)
    for name in ('start.stderr.txt', 'exit-watch.stderr.txt', 'AMENDMENT_V2.md'):
        copy_file(control / name, output / 'control' / name)
    for name in ('frame_block_grass_r21_prepare.py', 'frame_block_grass_r21_run.py',
                 'frame_block_grass_r21_run_v2.py', 'frame_block_grass_r21_review.py'):
        copy_file(ROOT / '.runtime' / name, output / 'hosts' / name)
    for relative in sorted(import_closure(control / 'external-host', ['tools/watch_intrinsic_glint_exit_r21.py'])):
        copy_file(control / 'external-host' / relative, output / 'sources/observer' / relative)
    copy_file(project / 'tools/frame_block_light_r21_host.py', output / 'hosts/frame_block_light_r21_host.py')
    copy_file(Path(__file__), output / 'replay.py')
    copy_file(readme, output / 'README.md')
    (output / '.gitattributes').write_text('* -text -whitespace\n', encoding='ascii')
    files = {path.relative_to(output).as_posix(): digest(path)
             for path in sorted(output.rglob('*')) if path.is_file()}
    manifest = {'schema': 1, 'production_qualified': False, 'appearance_accepted': False,
        'phase_completed': True, 'phases': originals, 'raw_png_count': 60,
        'source_sha256': plan['source_sha256'], 'frozen_source_files': len(plan['sources']),
        'prior_failed_evidence_manifest_sha256': digest(prior / 'manifest.json'),
        'archive_tool_sha256': digest(Path(__file__)), 'files': files}
    write_json(output / 'manifest.json', manifest)
    return {'files': len(files), 'phases': len(originals), 'raw_png_count': 60,
            'production_qualified': False, 'manifest_sha256': digest(output / 'manifest.json')}


def replay(bundle, output):
    import numpy as np
    from PIL import Image
    from analyze_liquid_workspace import capture_failures
    from item_sprite_capture_contract import snapshot_digest
    from verify_camera_projection import analyze_calibration
    from archive_frame_block_light_holdout_r21 import review

    bundle = bundle.resolve()
    manifest = json.loads((bundle / 'manifest.json').read_bytes())
    actual = {path.relative_to(bundle).as_posix() for path in bundle.rglob('*')
              if path.is_file() and path != bundle / 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files'])
    for relative, expected_hash in manifest['files'].items():
        assert digest(contained(bundle, relative)) == expected_hash, relative
    assert digest(bundle / 'replay.py') == manifest['archive_tool_sha256']
    plan = json.loads((bundle / 'control/plan.json').read_bytes())
    assert snapshot_digest(plan['sources']) == manifest['source_sha256']
    assert len(plan['sources']) == manifest['frozen_source_files'] == 3828
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for name in PHASES:
        report = json.loads((bundle / 'phases' / name / 'report.json').read_bytes())
        expected = json.loads((bundle / 'phases' / name / 'review.json').read_bytes())
        outcome = json.loads((bundle / 'control' / (name + '-outcome.json')).read_bytes())
        phase = next(row for row in plan['phases'] if row['id'] == name)
        assert report['completed'] and report['matrix_completed'] and report['environment_restored']
        assert report['source_unchanged'] and not report['cleanup_errors']
        assert report['launch_sources'] == report['sources_after'] == plan['sources']
        assert expected['source_report_sha256'] == outcome['report_sha256'] == manifest['phases'][name]['report_sha256']
        assert report['frame_block_batch']['sha256'] == phase['matrix_sha256']
        assert report['cases'][0]['source']['view_angle_degrees'] == phase['angle']
        first = datetime.fromisoformat(json.loads((bundle / 'control' / (name + '-attempt.json')).read_bytes())['at'])
        assert len(receipts(report)) == 20
        for receipt in receipts(report):
            assert datetime.fromisoformat(receipt['started_at']) >= first
            receipt['path'] = str(contained(bundle, receipt['path']))
            assert digest(Path(receipt['path'])) == receipt['sha256']
        assert not capture_failures({str(i): row for i, row in enumerate(receipts(report))}, report['session'])
        destination = output / name
        destination.mkdir()
        calibration = deepcopy(report['camera_calibration'])
        for row in calibration['views']:
            row['signal'] = str(destination / ('camera-' + row['view'] + '-signal.png'))
            row['outline_comparison'] = str(destination / ('camera-' + row['view'] + '-outline.png'))
        analyze_calibration(calibration)
        for key in ('passed', 'vertical_fov', 'individual_fitted_vertical_fov'):
            compare(report['camera_calibration'][key], calibration[key], name + '/calibration/' + key)
        for saved, measured in zip(report['camera_calibration']['views'], calibration['views']):
            compare(saved['fit'], measured['fit'], name + '/calibration/' + measured['view'])
        measured = review(report, report['candidate_geometry']['data']['pose'], destination / 'analysis')
        for key in ('cases', 'geometry_thresholds'):
            compare(expected[key], measured[key], name + '/' + key)
        images = list((bundle / 'phases' / name).rglob('*.png'))
        for image in images:
            assert np.array_equal(np.asarray(Image.open(image)),
                                  np.asarray(Image.open(destination / image.relative_to(bundle / 'phases' / name))))
        results[name] = {'raw_png_count': 20, 'calibration_reproduced': True,
                         'analysis_images_reproduced': len(images)}
    generator_path = bundle / 'sources/generator/tools/generate_frame_block_items.py'
    spec = importlib.util.spec_from_file_location('frozen_grass_generator', generator_path)
    generator = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(generator_path.parent))
    spec.loader.exec_module(generator)
    textures = json.loads((bundle / 'control/source-textures.json').read_bytes())
    for row in textures.values():
        faces = {face: generator.bake_texture(Image.open(bundle / 'native' / row['faces'][face]['path']),
                          generator.texture_entry(row['faces'][face]['entry']))[0]
                 for face in generator.FACE_VERTICES}
        bitmap, rectangles = generator.atlas_image(faces)
        assert rectangles == row['rectangles']
        assert hashlib.sha256(bitmap).hexdigest() == row['atlas_sha256']
        assert (bundle / 'captured-resources' / row['atlas']).read_bytes() == bitmap
    exits = json.loads((bundle / 'control/exact-exit.json').read_bytes())
    stop = json.loads((bundle / 'control/normal-stop-journal.json').read_bytes())
    assert exits['completed'] and stop['normal_close_requests'] == 1 and not stop['force_stop']
    assert stop['finalization']['session_state'] == 'stopped'
    for kind in ('game', 'mcdk'):
        assert exits['processes'][kind]['pid'] == report['session'][kind + '_pid']
        assert exits['processes'][kind]['identity'] == report['session'][kind + '_identity']
    result = {'schema': 1, 'replay_completed': True, 'production_qualified': False,
        'appearance_accepted': False, 'phases': results, 'raw_png_count': 60,
        'corrected_atlas_reproduced': True, 'frozen_source_files': 3828,
        'exit_codes': {kind: row['exit_code_hex'] for kind, row in exits['processes'].items()}}
    write_json(output / 'replay.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    builder = commands.add_parser('build')
    for name in ('control', 'output', 'readme'):
        builder.add_argument('--' + name, type=Path, required=True)
    replayer = commands.add_parser('replay')
    replayer.add_argument('bundle', type=Path)
    replayer.add_argument('output', type=Path)
    args = vars(parser.parse_args())
    command = args.pop('command')
    print(json.dumps({'build': build, 'replay': replay}[command](**args)))


if __name__ == '__main__':
    main()

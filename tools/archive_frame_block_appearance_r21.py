"""Freeze and replay raw frame-block appearance failures and a light experiment."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

FROZEN_TOOLS = Path(__file__).resolve().parent / 'sources/tools'
if FROZEN_TOOLS.is_dir():
    sys.path.insert(0, str(FROZEN_TOOLS))

from archive_frame_block_evidence_r21 import (compare, contained, digest,
    import_closure, verify_files, write_json)
from prepare_frame_block_light_r21 import FRAGMENT, correct_base_light

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ('data/resource_packs/vanilla_netease/shaders/glsl/entityVertexUtil.h',
    'data/resource_packs/vanilla_netease/shaders/glsl/entityFragmentUtil.h',
    'data/resource_packs/vanilla_netease/shaders/glsl/entity.fragment',
    'data/resource_packs/vanilla/materials/entity.material')


def copy_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    assert digest(source) == digest(destination)


def candidate_differences(candidate, holdouts):
    metadata = json.loads((candidate / 'candidate.json').read_bytes())
    assert metadata['production_qualified'] is False
    assert metadata['native_pixels_accepted'] is False
    assert metadata['native_cause_established'] is False
    assert metadata['base_light'] == .93
    changed = []
    for relative, expected in metadata['files'].items():
        source = contained(holdouts / 'sources', relative)
        actual = contained(candidate, relative)
        assert digest(source) == metadata['source_file_sha256'][relative], relative
        assert digest(actual) == expected, relative
        if source.read_bytes() != actual.read_bytes():
            changed.append(relative)
    assert changed == metadata['changed_paths'] == [FRAGMENT], changed
    original = (holdouts / 'sources' / FRAGMENT).read_bytes().decode('ascii')
    assert (candidate / FRAGMENT).read_bytes() == correct_base_light(original).encode('ascii')
    return metadata


def copy_headers(project, header_root, output):
    pending = list((project / 'resource_pack/shaders/glsl').iterdir())
    selected = {}
    while pending:
        path = pending.pop()
        for name in re.findall(r'^\s*#include\s+"([^"]+)"',
                               path.read_text(encoding='utf-8'), flags=re.M):
            if name in selected:
                continue
            source = contained(header_root, name)
            selected[name] = digest(source)
            copy_file(source, contained(output, name))
            pending.append(source)
    return selected


def shader_check(bundle, report, browser):
    subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(bundle / 'sources/tools/verify_frame_block_item_shaders.py'),
        '--headers', str(bundle / 'headers'), '--browser', browser,
        '--project', str(bundle / 'candidate'), '--report', str(report)], check=True)


def verify(bundle, holdouts):
    manifest = json.loads((bundle / 'manifest.json').read_bytes())
    files = {path.relative_to(bundle).as_posix() for path in bundle.rglob('*')
             if path.is_file() and path != bundle / 'manifest.json'
             and '__pycache__' not in path.parts}
    assert files == set(manifest['files'])
    for relative, expected in manifest['files'].items():
        assert digest(contained(bundle, relative)) == expected, relative
    assert digest(bundle / 'replay.py') == manifest['archive_tool_sha256']
    verify_files(holdouts)
    assert digest(holdouts / 'manifest.json') == manifest['source_bundle_manifest_sha256']
    candidate = candidate_differences(bundle / 'candidate', holdouts)
    assert digest(bundle / 'sources/tools/prepare_frame_block_light_r21.py') == candidate['generator_sha256']
    appearance = json.loads((bundle / 'analysis/appearance.json').read_bytes())
    assert appearance['source_bundle_manifest_sha256'] == manifest['source_bundle_manifest_sha256']
    assert digest(bundle / 'sources/tools/analyze_frame_block_appearance_r21.py') == appearance['analyzer_sha256']
    assert appearance['appearance_accepted'] is False and appearance['production_qualified'] is False
    faces = [face for case in appearance['cases'] for face in case['faces'].values()]
    assert len(faces) == 8 and all(face['large_roi'] for face in faces)
    assert all(face['native_product']['full']['mean_luma_ratio'] > 1.07 for face in faces)
    assert all(face['native_product']['full']['fitted_alignment_or_color_correction'] is False for face in faces)
    compile_report = json.loads((bundle / 'shader-verification.json').read_bytes())
    assert compile_report['passed'] and compile_report['production_qualified'] is False
    for name, expected in compile_report['shader_sha256'].items():
        assert digest(bundle / 'candidate/resource_pack/shaders/glsl' / name) == expected
    return manifest, appearance


def build(holdouts, appearance, candidate, shader_report, install, headers, readme, output, browser):
    verify_files(holdouts)
    candidate_differences(candidate, holdouts)
    original = json.loads((appearance / 'appearance.json').read_bytes())
    assert digest(ROOT / 'tools/analyze_frame_block_appearance_r21.py') == original['analyzer_sha256']
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(appearance, output / 'analysis')
    shutil.copytree(candidate, output / 'candidate')
    copy_file(readme, output / 'README.md')
    copy_file(Path(__file__), output / 'replay.py')
    entries = ['tools/analyze_frame_block_appearance_r21.py',
        'tools/prepare_frame_block_light_r21.py', 'tools/verify_frame_block_item_shaders.py']
    for relative in sorted(import_closure(ROOT, entries)):
        copy_file(contained(ROOT, relative), contained(output / 'sources', relative))
    native = {}
    for relative in NATIVE:
        source = contained(install, relative)
        copy_file(source, contained(output / 'native', relative))
        native[relative] = digest(source)
    header_hashes = copy_headers(candidate, headers, output / 'headers')
    shader_check(output, output / 'shader-verification.json', browser)
    compare(json.loads(shader_report.read_bytes()),
            json.loads((output / 'shader-verification.json').read_bytes()))
    write_json(output / 'lighting-diagnosis.json', {
        'schema': 1, 'production_qualified': False, 'native_cause_established': False,
        'native_install': str(install), 'native_source_sha256': native,
        'native_source_binding': 'Installed 3.10.0.420447 source snapshots read after the original capture; actual frame material route and flags were not logged',
        'directional_match': 'Candidate frameIntensity equals entityVertexUtil.h FANCY, non-RNGL_LIGHT and non-RNGL_UNLIT branch: (1+Ny*TILE_LIGHT_COLOR.w)*0.275 - Nx*Nx*0.1 + Nz*Nz*0.1 + 0.45',
        'branch_limits': ['Native !FANCY or RNGL_UNLIT branch returns 1',
            'Native RNGL_LIGHT branch uses HIDE_COLOR directional lighting',
            'FLIP_BACKFACES and USE_OVERLAY affect native lighting when enabled',
            'Actual ordinary stone item-frame route, flags, vertex colors, TILE_LIGHT_COLOR and fog were not observed'],
        'other_native_factors': ['getLightColor multiplies TILE_LIGHT_COLOR.xyz',
            'COLOR_BASED fragment route multiplies vertColor; item_in_hand declares COLOR_BASED, NO_TEXTURE and ITEM_IN_HAND',
            'ITEM_IN_HAND may apply CHANGE_COLOR tint; entity.fragment applies fog before glint'],
        'candidate_difference': 'Specialized frame-block fragment multiplies texture by itemLight, has no native vertex COLOR term or explicit fog, and independently adds squared glint',
        'empirical_base_light': .93,
        'factor_provenance': 'Rounded inverse of observed approximately 1.0763 old flat-item brightness and current eight stone ROI gains 1.0704-1.0776; not a discovered native constant',
        'training_rois': 8, 'holdouts_accepted': 0,
        'static_glint_limits': 'Sequential enchanted quartz stills show volumetric glint but do not identify phase, brightness, motion direction or UV agreement',
        'compile_binding': 'Shader verification rerun against the packaged candidate, frozen verifier/imports and exact frozen transitive engine headers; full report equals original candidate-v2 report'})
    (output / '.gitattributes').write_text(
        '* -text -whitespace\n', encoding='ascii')
    files = {path.relative_to(output).as_posix(): digest(path)
             for path in sorted(output.rglob('*')) if path.is_file()}
    write_json(output / 'manifest.json', {'schema': 1, 'production_qualified': False,
        'appearance_accepted': False, 'native_cause_established': False,
        'source_bundle_manifest_sha256': digest(holdouts / 'manifest.json'),
        'source_bundle_default': '../frame-block-holdouts-r21-v1',
        'files': files, 'native_source_sha256': native, 'header_sha256': header_hashes,
        'archive_tool_sha256': digest(Path(__file__)),
        'limitations': ['Requires the unchanged sibling native-holdout bundle for original PNGs',
            'Appearance pixels remain unchanged and failed; no corrected screenshot is accepted',
            'The eight existing ROIs are training diagnostics, not native acceptance holdouts',
            'Candidate subset is not a prepared runnable project and changes no production file']})
    verify(output, holdouts)
    return {'files': len(files), 'headers': len(header_hashes), 'production_qualified': False}


def replay(bundle, holdouts, output, browser=None):
    manifest, expected = verify(bundle, holdouts)
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, '-B', '-X', 'utf8',
        str(bundle / 'sources/tools/analyze_frame_block_appearance_r21.py'),
        str(holdouts), str(output / 'analysis')], check=True)
    actual = json.loads((output / 'analysis/appearance.json').read_bytes())
    compare(expected, actual)
    for path in (bundle / 'analysis').iterdir():
        if path.suffix == '.png':
            from PIL import Image
            import numpy as np
            assert np.array_equal(np.asarray(Image.open(path)),
                np.asarray(Image.open(output / 'analysis' / path.name))), path.name
    if browser:
        shader_check(bundle, output / 'shader-verification.json', browser)
        compare(json.loads((bundle / 'shader-verification.json').read_bytes()),
                json.loads((output / 'shader-verification.json').read_bytes()))
    result = {'schema': 1, 'completed': True, 'files_verified': len(manifest['files']),
        'appearance_reproduced': True, 'roi_and_montage_pixels_reproduced': 11,
        'candidate_changed_paths_verified': [FRAGMENT], 'shader_check_repeated': bool(browser),
        'production_qualified': False, 'appearance_accepted': False}
    write_json(output / 'replay.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    builder = commands.add_parser('build')
    for name in ('holdouts', 'appearance', 'candidate', 'shader-report',
                 'install', 'headers', 'readme', 'output'):
        builder.add_argument('--' + name, type=Path, required=True)
    builder.add_argument('--browser', required=True)
    replayer = commands.add_parser('replay')
    replayer.add_argument('bundle', type=Path)
    replayer.add_argument('output', type=Path)
    replayer.add_argument('--holdouts', type=Path)
    replayer.add_argument('--browser')
    args = vars(parser.parse_args())
    command = args.pop('command')
    if command == 'replay' and args['holdouts'] is None:
        args['holdouts'] = args['bundle'].parent / 'frame-block-holdouts-r21-v1'
    print(json.dumps({'build': build, 'replay': replay}[command](**args)))


if __name__ == '__main__':
    main()

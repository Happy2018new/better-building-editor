"""Exercise physical motion gates against real product shaders at four phases.

Host GLES regression only; this does not establish game or native-water parity.
The actual mesh, shaders, artwork and original alpha are retained. The supplied
clock advances independently at 20 Hz, including phases between atlas updates.
"""
import argparse
import base64
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from analyze_product_water_flow import GRID, controlled_motion, physical_points
from verify_biome_shader import shader_source
from verify_liquid_product_triangles import (RENDER, camera_matrix, digest,
    header_fingerprints, selected_mesh, uniforms)

ROOT = Path(__file__).resolve().parents[1]
SIZE = 128


def renderer():
    source = RENDER.replace("const failures=[];let checks=0;", "const failures=[];let checks=0;const frames=[];")
    source = source.replace("gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,fixture.matrix);",
        "gl.uniform1f(gl.getUniformLocation(program,'TOTAL_REAL_WORLD_TIME'),fixture.time);\n"
        "gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,fixture.matrix);")
    source = source.replace("for(const sample of fixture.samples)",
        "frames.push(btoa(String.fromCharCode(...pixels)));\nfor(const sample of fixture.samples)")
    source = source.replace("checks,failures:failures.slice(0,24)", "checks,frames,failures:failures.slice(0,24)")
    return source


def make_cases(root, headers):
    contract_path = root / 'tools/data/liquid_product_resource_contract_v1.json'
    contract = json.loads(contract_path.read_bytes())
    inputs, includes, cases = {contract_path.relative_to(root).as_posix(): digest(contract_path)}, {}, []
    texture_path = root / 'resource_pack/textures/models/modern_projection/liquid/flowing_water_grey.png'
    inputs[texture_path.relative_to(root).as_posix()] = digest(texture_path)
    with Image.open(texture_path) as image:
        rgba = image.convert('RGBA')
        texture_size = rgba.size
        texture = base64.b64encode(rgba.tobytes()).decode('ascii')
    cell = (0, 1, 1)
    for owner in ('editor', 'world'):
        for name, face, rotation, axis, sign in (
                ('flow_east', 0, 192, 1, 1), ('flow_south', 0, 0, 0, 1),
                ('flow_west', 0, 64, 1, -1), ('flow_north', 0, 128, 0, -1),
                ('falling', 2, 0, 0, -1)):
            model = ('modern_projection_liquid_product_flowing_water_grey'
                     + ('_top' if face == 0 else '') + ('_world' if owner == 'world' else ''))
            option = contract['model_options'][model]
            mesh_path = root / 'resource_pack/models' / contract['models'][model]['mesh']
            mesh = json.loads(mesh_path.read_bytes())['mesh'][0]
            vertices, indices = selected_mesh(mesh, 0, face)
            inputs[mesh_path.relative_to(root).as_posix()] = digest(mesh_path)
            sources = []
            for filename in (option['vertex_shader'], option['fragment_shader']):
                path = root / 'resource_pack/shaders/glsl' / filename
                inputs[path.relative_to(root).as_posix()] = digest(path)
                header_fingerprints(path.read_text(encoding='ascii'), headers, includes)
                sources.append(shader_source(path, headers, 300, ()))
            for phase in (0., .0125, .025, .0375):
                fixtures = [{'time': phase + index * .05, 'samples': [],
                    'matrix': camera_matrix(face, cell, option['preview_depth']),
                    'uniforms': uniforms(0, cell, face, (255,) * 4, rotation),
                    'background': (.125, .375, .75, 1.)} for index in range(32)]
                cases.append({'name': '%s/%s/phase%s' % (owner, name, phase),
                    'version': 300, 'size': SIZE, 'vertex': sources[0], 'fragment': sources[1],
                    'vertices': vertices, 'indices': indices, 'rgba': texture,
                    'texture_size': texture_size, 'fixtures': fixtures,
                    'face': face, 'axis': axis, 'sign': sign})
    return cases, inputs, includes


def sample_frames(frames, face):
    points, spacing = physical_points({'position': (0, 0, 0), 'heights': (1,) * 4}, face)
    points = np.asarray(points)
    # gl.readPixels rows start at the bottom. Orthographic face axes are
    # independently fixed to +X/-Z (top) and +X/+Y (south side).
    x = (.1 + .8 * points[:, 0]) * SIZE - .5
    y = (.1 + .8 * (1 - points[:, 2] if face == 0 else points[:, 1])) * SIZE - .5
    values = []
    for payload in frames:
        pixels = np.frombuffer(base64.b64decode(payload), dtype=np.uint8).reshape(SIZE, SIZE, 4)
        grey = pixels[:, :, :3].astype(float).mean(axis=2)
        values.append(map_coordinates(grey, (y, x), order=1).reshape(GRID, GRID))
    return np.asarray(values), spacing


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh evidence; prior results are immutable')
    cases, inputs, includes = make_cases(args.root, args.headers)
    report = {'scope': __doc__, 'inputs_sha256': inputs, 'headers_sha256': includes,
        'verifier_sha256': digest(Path(__file__)),
        'analyzer_sha256': digest(ROOT / 'tools/analyze_product_water_flow.py'),
        'game_acceptance_claimed': False, 'results': [], 'passed': False}
    signals = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page()
            for index, case in enumerate(cases):
                rendered = page.evaluate(renderer(), [case])[0]
                if not rendered['passed']:
                    raise RuntimeError(str(rendered))
                signal, spacing = sample_frames(rendered['frames'], case['face'])
                signals['case_%s' % index] = signal
                result = controlled_motion(signal, np.arange(32) * 500000,
                    case['axis'], case['sign'], spacing, 16 if case['face'] == 0 else 15)
                report['results'].append({'name': case['name'], 'signal_key': 'case_%s' % index,
                                          'result': result})
        finally:
            browser.close()
    signals_path = args.output.with_suffix('.npz')
    np.savez_compressed(signals_path, **signals)
    report['signals'] = {'path': str(signals_path), 'sha256': digest(signals_path)}
    report['passed'] = all(row['result']['passed'] for row in report['results'])
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': report['passed'], 'cases': len(cases), 'failures': [
        row['name'] for row in report['results'] if not row['result']['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

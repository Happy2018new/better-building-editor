"""Host GLES water-style checks; this does not claim native game acceptance."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from PIL import Image

from verify_biome_shader import shader_source
from verify_liquid_skeleton_resources import RENDER, fixtures, top_fixtures
from generate_liquid_product_resources import text_digest, verify_contract

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_RENDER = RENDER.replace(
    "gl.uniform1f(gl.getUniformLocation(p,'TIME'),fixture.time);",
    "gl.uniform1f(gl.getUniformLocation(p,'TIME'),fixture.time%210);\n"
    "    gl.uniform1f(gl.getUniformLocation(p,'TOTAL_REAL_WORLD_TIME'),fixture.time);").replace(
    "gl.vertexAttrib4fv(position,fixture.position);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);",
    "gl.vertexAttrib4fv(position,fixture.position);\n"
    "    const bg=fixture.background??[0,0,0,0];gl.clearColor(...bg);gl.clear(gl.COLOR_BUFFER_BIT);\n"
    "    if(fixture.background){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);}\n"
    "    else gl.disable(gl.BLEND);")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker_image(size):
    image = Image.new('RGBA', size)
    width, height = size
    image.putdata([(x * 7 % 256, y % width * 5 % 256, y // width * 8 % 256, 240)
                   for y in range(height) for x in range(width)])
    return image


def hour_fixtures(image, ticks):
    """Known-frame colors select time independently of the engine TIME210 clock."""
    width = image.width
    frames = image.height // width
    rows = []
    for time in (209.975, 210., 210.025, 3599.95, 3599.975, 3600., 0., .025, .05):
        clock = time * 20. / ticks
        frame = int(clock) % frames
        fraction = clock % 1.
        first = image.getpixel((0, frame * width))
        second = image.getpixel((0, ((frame + 1) % frames) * width))
        expected = [round(a * (1. - fraction) + b * fraction) for a, b in zip(first[:3], second[:3])]
        expected.append(round(.45 * 255.))
        rows.append({'name': 'hour/%s' % time, 'time': time, 'position': [0., 0., 0., 1.],
            'uniforms': [[64., 0., 0., 0.], [65535.] * 4, [65535.] * 4,
                         [39686., -1., float(0xFFFFFF), 1.]], 'expected': expected})
    return rows


def transparency_fixtures(image, ticks, top=False, frozen=False):
    source = top_fixtures(image, ticks, frozen, .45) if top else fixtures(image, ticks, frozen, .45)
    first = source[0]
    rows = []
    for background in ((1., 0., 0., 1.), (0., 1., 0., 1.), (0., 0., 1., 1.)):
        alpha = .45 * .5
        expected = [round(first['expected'][i] * alpha + background[i] * 255. * (1. - alpha))
                    for i in range(3)]
        expected.append(round(255. * (alpha * alpha + 1. - alpha)))
        rows.append(dict(first, name='rear/' + str(background), background=background, expected=expected))
    return rows


def make_cases(overlay, headers):
    contract = json.loads((overlay / 'contract.json').read_bytes())
    verify_contract(contract, overlay, ROOT)
    shaders = overlay / 'resource_pack/shaders/glsl'
    cases = []
    for name, options in contract['model_options'].items():
        key = options['texture']
        texture = contract['textures'][key]
        ticks = texture['animation']['ticks_per_frame']
        path = overlay / ('resource_pack/textures/models/modern_projection/liquid/' + key + '.png')
        with Image.open(path).convert('RGBA') as image:
            for marker in (False, True):
                artwork = marker_image(image.size) if marker else image
                parameters = {} if options['top_only'] else {'sampling': {
                    'region': 'nw' if key.startswith('flowing_') else 'full', 'pixel_mapping': 'centers'}}
                factory = top_fixtures if options['top_only'] else fixtures
                inputs = factory(artwork, ticks, options['frozen'], .45, **parameters)
                inputs.extend(transparency_fixtures(artwork, ticks, options['top_only'], options['frozen']))
                if marker and not options['top_only'] and key == 'still_water_grey' and not options['frozen']:
                    inputs.extend(hour_fixtures(artwork, ticks))
                for version in (100, 300):
                    cases.append({'name': '%s/%s/%s' % (name, version, 'marker' if marker else 'artwork'),
                        'version': version,
                        'vertex': shader_source(shaders / options['vertex_shader'], headers, version, ('BLEND',)),
                        'fragment': shader_source(shaders / options['fragment_shader'], headers, version, ('BLEND',)),
                        'size': artwork.size, 'rgba': base64.b64encode(artwork.tobytes()).decode('ascii'),
                        'fixtures': inputs})
            # Installed skeletal headers use non-square matrices and gl_InstanceID (GLES3).
            for version in (300,):
                cases.append({'name': '%s/%s/skinning' % (name, version), 'version': version,
                    'vertex': shader_source(shaders / options['vertex_shader'], headers, version,
                                           ('USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE')),
                    'fragment': shader_source(shaders / options['fragment_shader'], headers, version, ()),
                    'compile_only': True})
    # Frame color is spatially constant so still and flow cadence can share an independent oracle.
    image = Image.new('RGBA', (16, 512))
    image.putdata([(0, 0, (y // 16) * 8, 255) for y in range(512) for _ in range(16)])
    for key in ('still_water_grey', 'flowing_water_grey'):
        options = contract['model_options']['modern_projection_liquid_product_' + key]
        ticks = contract['textures'][key]['animation']['ticks_per_frame']
        for version in (100, 300):
            cases.append({'name': 'clock/%s/%s' % (key, version), 'version': version,
                'vertex': shader_source(shaders / options['vertex_shader'], headers, version, ()),
                'fragment': shader_source(shaders / options['fragment_shader'], headers, version, ()),
                'size': image.size, 'rgba': base64.b64encode(image.tobytes()).decode('ascii'),
                'fixtures': hour_fixtures(image, ticks)})
    return cases


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cases = make_cases(args.overlay, args.headers)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(PRODUCT_RENDER, cases)
        finally:
            browser.close()
    report = {'schema_version': 1, 'passed': all(row['passed'] for row in results),
        'checks': sum(row.get('checks', 0) for row in results), 'results': results,
        'contract_sha256': digest(args.overlay / 'contract.json'),
        'verifier_sha256': digest(Path(__file__)),
        'helper_sha256': {p: text_digest(ROOT / 'tools' / p) for p in (
            'verify_biome_shader.py', 'verify_liquid_skeleton_resources.py')},
        'helper_fingerprint': 'sha256_utf8_text_with_lf',
        'scope': 'Host GLES2/3 texels, four side crops, 256 top angles, alpha composition and hour reset',
        'skinning_scope': 'GLES3 only: installed native header uses mat3x4 and gl_InstanceID',
        'game_acceptance_claimed': False, 'native_parity_claimed': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'],
                      'failed_cases': [row for row in results if not row['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

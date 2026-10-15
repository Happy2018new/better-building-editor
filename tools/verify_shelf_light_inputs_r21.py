"""Check the private shelf GPU input shader against explicit synthetic inputs."""
import argparse
import json
from pathlib import Path

from verify_biome_shader import shader_source
from verify_native_actor_shaders import RENDER, actor_fixtures


VARIANTS = (
    ('plain', ()), ('fancy', ('FANCY',)), ('color', ('COLOR_BASED',)),
    ('fancy_color', ('FANCY', 'COLOR_BASED')),
    ('unlit_color', ('FANCY', 'COLOR_BASED', 'RNGL_UNLIT')),
    ('local', ('FANCY', 'COLOR_BASED', 'RNGL_LOCAL_LIGHT')),
    ('skinning', ('FANCY', 'COLOR_BASED', 'USE_SKINNING')),
)


def fixtures(flags, mesh=False):
    rows = [] if mesh else actor_fixtures(flags)
    color = [.8, .6, .4] if mesh or 'COLOR_BASED' in flags else [1., 0., 1.]
    flag_rgb = [float('FANCY' in flags),
                (int('RNGL_UNLIT' in flags)+2*int('RNGL_LOCAL_LIGHT' in flags))/7.,
                (int('COLOR_BASED' in flags)+2*int('USE_SKINNING' in flags))/7.]
    expected = [[.5, 1., .5]]*3+[[.25, .5, .75]]*2+[color, flag_rgb, [0., 0., 1.]]
    if 'USE_SKINNING' in flags:
        return []
    # Native lighting baseline fixtures assume FANCY is absent or an upward normal.
    if 'RNGL_LOCAL_LIGHT' in flags:
        rows = []
    for mode, rgb in enumerate(expected, 1):
        rows.append({'name': 'input_'+str(mode), 'packet': [19491., float(mode), 0., 0.],
                     'local': [0.]*4, 'common': 1., 'vertex_color': [.8, .6, .4, 1.],
                     'shadow_color': [0.]*4, 'pixel': [180, 120, 60, 255],
                     'expected': [value*255. for value in rgb]+[255.],
                     'blank': False, 'tolerance': 2})
    if mesh:
        row = dict(rows[0], name='unmarked_material_selector', packet=[0.]*4,
                   expected=[255., 0., 255., 255.])
        return rows+[row]
    # COLOR_BASED changes the native baseline color; those old fixtures do not model it.
    return [row for row in rows if row['name'].startswith('input_')] if 'COLOR_BASED' in flags else rows


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--route', choices=('actor', 'mesh'), default='actor')
    args = parser.parse_args()
    vertex = args.project/'resource_pack/shaders/glsl/modern_projection_shelf_inputs.vertex'
    fragment = vertex.with_suffix('.fragment')
    mesh = args.route == 'mesh'
    variants = (('plain', ()), ('fancy', ('FANCY',)), ('blend', ('BLEND',)),
                ('seasons', ('SEASONS',)), ('alpha', ('ALPHA_TEST',)),
                ('bypass', ('BYPASS_PIXEL_SHADER',))) if mesh else VARIANTS
    cases = [{'name': name+'/'+str(version), 'kind': 'terrain' if mesh else 'entity', 'version': version,
              'flags': flags, 'v': shader_source(vertex, args.headers, version, flags),
              'f': shader_source(fragment, args.headers, version, flags), 'fixtures': fixtures(flags, mesh)}
             for version in (100, 300) for name, flags in variants]
    skin_flags = VARIANTS[-1][1]
    cases.extend({'name': 'native_skinning/'+str(version), 'kind': 'native_baseline',
                  'version': version, 'flags': skin_flags,
                  'v': shader_source(args.headers/'entity.vertex', args.headers, version, skin_flags),
                  'f': shader_source(args.project/'resource_pack/shaders/glsl/modern_projection_native_actor.fragment',
                                     args.headers, version, skin_flags), 'fixtures': []}
                 for version in (() if mesh else (100, 300)))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    baselines = {row['version']: row for row in results if row['kind'] == 'native_baseline'}
    inherited = [row for row in results if not row['linked'] and
                 row['name'].startswith(('skinning/', 'native_skinning/')) and
                 not baselines[row['version']]['linked']]
    passed = all(row['passed'] or row in inherited for row in results)
    report = {'passed': passed, 'production_qualified': False,
              'synthetic_pixels_only': True, 'results': results,
              'inherited_gles100_skinning_failures': len(inherited),
              'inheritance_check': 'Compare actual native entity.vertex with identical flags in the same browser'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'passed': passed, 'programs': len(results),
                      'linked': sum(row['linked'] for row in results),
                      'pixel_checks': sum(len(row['pixel_checks']) for row in results),
                      'failures': [row for row in results if not row['passed'] and row not in inherited]}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

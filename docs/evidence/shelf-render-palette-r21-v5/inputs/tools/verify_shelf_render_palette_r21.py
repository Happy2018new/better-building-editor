"""Verify the marked COLOR branch and unchanged unmarked full-palette shader."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_shelf_render_palette_r21 import FRAGMENT, verify
from verify_biome_shader import RENDER, shader_source


def renderer():
    old = "f.mode === 'world' ? 19487 : 0"
    if RENDER.count(old) != 1:
        raise ValueError('The synthetic common-block renderer changed')
    result = RENDER.replace(old, 'f.marker')
    old = "gl.uniform1f(uniform('COMMON_BLOCK_GEO_FLOAT1_1'),1);"
    if result.count(old) != 1:
        raise ValueError('The common-block uniform setup changed')
    return result.replace(old, old+"\n    gl.uniform1f(uniform('RENDER_DISTANCE'),1000000);"
        "\n    gl.uniform2f(uniform('FOG_CONTROL'),0,1);")


def fixtures(diagnostic):
    rows = []
    for marker in (0., 19487., 19491.):
        for rgb in ((.8, .8, .8), (.2, .5, .8), (1., 1., 1.)):
            rows.append({'name': str(marker)+'/'+str(rgb), 'mode': 'native', 'marker': marker,
                         'target': 6, 'vertex': list(rgb)+[1.], 'pixel': [128, 128, 128, 255],
                         'expected': [value*(255 if diagnostic and marker == 19491. else 128)
                                      for value in rgb], 'tolerance': 1})
    return rows


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh compiler report')
    frozen = verify(args.freeze)
    source = json.loads(Path(frozen['source_freeze']).read_bytes())
    cases = []
    vertex = Path(frozen['project'])/'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex'
    for diagnostic in (False, True):
        project = Path(frozen['project'] if diagnostic else source['project'])
        for version in (100, 300):
            for flags in ((), ('BLEND',), ('BLEND', 'ALPHA_TEST'), ('FANCY', 'FOG')):
                cases.append({'name': ('candidate' if diagnostic else 'source')+'/'+str(version)+'/'+','.join(flags),
                    'version': version, 'v': shader_source(vertex, args.headers, version, flags),
                    'f': shader_source(project/FRAGMENT, args.headers, version, flags),
                    'fixtures': fixtures(diagnostic), 'palette': [], 'targets': {}})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(renderer(), cases)
        finally:
            browser.close()
    report = {'schema_version': 1, 'passed': not any(row['failures'] for row in results),
        'production_qualified': False, 'native_neighbor_ao_qualified': False,
        'frozen_manifest_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'programs': len(results), 'pixel_checks': sum(row['checks'] for row in results), 'results': results,
        'expanded_source_sha256': {row['name']: {stage: hashlib.sha256(row[stage].encode('utf8')).hexdigest()
                                    for stage in ('v', 'f')} for row in cases},
        'scope': 'Actual common block pair with target headers. Unmarked and 19487 retain source output; '
                 'candidate 19491 returns varying color. Synthetic inputs do not establish native AO.'}
    verify(args.freeze)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({key: report[key] for key in ('passed', 'programs', 'pixel_checks')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Pair original terrain programs with eight-slot input readback diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_shelf_terrain_inputs_r21 import FLAG_CHANNELS, FRAGMENT, verify
from verify_biome_shader import shader_source
from verify_shelf_native_routes_r21 import RENDER as ROUTE_RENDER, variants


def renderer():
    source = ROUTE_RENDER
    changes = (
        ('canvas.width=64;', 'canvas.width=128;', 1),
        ('gl.viewport(0,0,64,4);', 'gl.viewport(0,0,128,4);', 1),
        ('strip<4;', 'strip<8;', 2),
        ("constant('COLOR',[1,1,1,fixture.vertexAlpha]);",
         "constant('COLOR',[.25,.5,.75,fixture.vertexAlpha]);", 1),
        ("unit===1&&c.family==='entity'?[0,0,0,0]:[255,255,255,255]",
         'unit===1?[80,160,240,255]:[255,255,255,255]', 1),
        ('const expected=strip%2||bypass||discard?baseline:[...c.marker.map(v=>v*255),baseline[3]];',
         '''const slots=[[255,255,0],[63.75,127.5,191.25],[255,0,255],
     c.flags.includes('ALWAYS_LIT')?[255,255,255]:[80,160,240],
     [0,255,255],c.flag_bytes,[255,255,255],baseline.slice(0,3)];
    const expected=bypass||discard?baseline:[...slots[strip],baseline[3]];''', 1),
    )
    for old, new, count in changes:
        if source.count(old) != count:
            raise RuntimeError('The frozen native route renderer changed: '+old)
        source = source.replace(old, new)
    return source


RENDER = renderer()


def flag_bytes(flags):
    return [sum(1 << bit for bit, name in enumerate(channel) if name in flags)*17
            for channel in FLAG_CHANNELS]


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
    pairs = []
    for version in (100, 300):
        for flags in variants('renderchunk'):
            native = shader_source(args.headers/'renderchunk.fragment', args.headers, version, flags)
            boundary = native.index('\n')+1
            native = native[:boundary]+'precision highp float;\nprecision highp int;\n'+native[boundary:]
            pairs.append({'name': str(version)+'/'+','.join(flags), 'family': 'renderchunk',
                'version': version, 'flags': flags, 'flag_bytes': flag_bytes(flags),
                'vertex': shader_source(args.headers/'renderchunk.vertex', args.headers, version, flags),
                'native': native,
                'selector': shader_source(Path(frozen['project'])/FRAGMENT, args.headers, version, flags),
                'compile_only': False, 'allow_native_skinning_failure': False})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, pairs)
        finally:
            browser.close()
    report = {'schema_version': 1, 'passed': all(row['passed'] for row in results),
        'native_input_readback_qualified': False, 'production_qualified': False,
        'frozen_manifest_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'expanded_source_sha256': {row['name']: {stage: hashlib.sha256(row[stage].encode('utf8')).hexdigest()
                                    for stage in ('vertex', 'native', 'selector')} for row in pairs},
        'pairs': len(results), 'programs': sum(len(row['programs']) for row in results),
        'pixel_checks': sum(len(row['checks']) for row in results), 'results': results,
        'scope': 'Synthetic native terrain/input pairs. COLOR, lightmap, flags, final RGB and native alpha; no runtime shelf input qualification.'}
    verify(args.freeze)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({key: report[key] for key in ('passed', 'pairs', 'programs', 'pixel_checks')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

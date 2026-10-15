"""Compile frame-block material pairs with actual target-engine GLES headers."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_biome_shader import shader_source
from verify_item_icon_shaders import COMPILE

ROOT = Path(__file__).resolve().parents[1]


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh frame-block shader report')
    shaders = ROOT / 'resource_pack/shaders/glsl'
    cases, hashes = [], {}
    for material in ('opaque', 'cutout', 'translucent'):
        for route in ('', '_world'):
            vertex = shaders / ('modern_projection_frame_block' + route + '.vertex')
            fragment = shaders / ('modern_projection_frame_block_' + material + '.fragment')
            for path in (vertex, fragment):
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            for version in (100, 300):
                for flags in (('BLEND',), ('BLEND', 'USE_OVERLAY')):
                    cases.append({'name': '%s%s/%s/%d' % (material, route, ','.join(flags), version),
                        'version': version, 'vertex': shader_source(vertex, args.headers, version, flags),
                        'fragment': shader_source(fragment, args.headers, version, flags)})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(COMPILE, cases)
        finally:
            browser.close()
    report = {'schema': 1, 'shader_sha256': hashes, 'results': results,
              'passed': all(row['compiled'] and row['linked'] for row in results),
              'production_qualified': False, 'scope': 'Offline compilation only; native pixels remain unaccepted'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': report['passed'], 'cases': len(results),
                      'failures': [row for row in results if not row['compiled'] or not row['linked']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

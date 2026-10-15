"""Compile actual item shader pairs with target-game headers in GLES 2/3."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
COMPILE = r'''cases => cases.map(row => {
 const canvas=document.createElement('canvas');
 const gl=canvas.getContext(row.version===300?'webgl2':'webgl');
 const result={name:row.name,compiled:false,linked:false,errors:[]};
 if(!gl){result.errors.push('WebGL context unavailable');return result;}
 const program=gl.createProgram();
 for(const [name,type] of [['vertex',gl.VERTEX_SHADER],['fragment',gl.FRAGMENT_SHADER]]) {
  const shader=gl.createShader(type);gl.shaderSource(shader,row[name]);gl.compileShader(shader);
  if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))result.errors.push({stage:name,log:gl.getShaderInfoLog(shader)});
  gl.attachShader(program,shader);
 }
 result.compiled=result.errors.length===0;
 gl.linkProgram(program);result.linked=gl.getProgramParameter(program,gl.LINK_STATUS);
 if(!result.linked)result.errors.push({stage:'link',log:gl.getProgramInfoLog(program)});
 return result;
})'''


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert not args.report.exists(), 'Choose a fresh compiler report'
    directory = ROOT / 'resource_pack/shaders/glsl'
    cases, hashes = [], {}
    for family in ('item_sprite', 'item_icon'):
        for route in ('', '_world'):
            vertex = directory / ('modern_projection_' + family + route + '.vertex')
            fragment = directory / ('modern_projection_' + family + '.fragment')
            for path in (vertex, fragment):
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                assert 'precision highp float;' in path.read_text(encoding='ascii'), path
            for version in (100, 300):
                for flags in (('BLEND',), ('BLEND', 'USE_OVERLAY')):
                    cases.append({'name': '%s%s/%d/%s' % (family,route,version,','.join(flags)),
                                  'family': family, 'version': version,
                                  'vertex': shader_source(vertex,args.headers,version,flags),
                                  'fragment': shader_source(fragment,args.headers,version,flags)})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(COMPILE, cases)
        finally:
            browser.close()
    baseline = dict((row['name'].replace('item_sprite','item_icon',1), row)
                    for row in results if row['name'].startswith('item_sprite'))
    for row in results:
        if row['name'].startswith('item_icon'):
            reference = baseline[row['name']]
            row['baseline_passed'] = reference['compiled'] and reference['linked']
            row['regression'] = row['baseline_passed'] and not (row['compiled'] and row['linked'])
    report = {'schema':1,'results':results,'shader_sha256':hashes,
              'passed':all(row['compiled'] and row['linked'] for row in results),
              'no_regressions':not any(row.get('regression') for row in results),
              'scope':'Offline target-header GLES compilation; native pixels remain separate'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(report))
    return 0 if report['no_regressions'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

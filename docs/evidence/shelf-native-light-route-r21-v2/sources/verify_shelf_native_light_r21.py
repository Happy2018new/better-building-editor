"""Compile the native light diagnostic and sample each stripe on actual GLES."""
import argparse
import json
from pathlib import Path

from prepare_shelf_native_light_r21 import FRAGMENT
from verify_biome_shader import shader_source


RENDER = r'''cases => {
  const results=[];
  for (const c of cases) {
    const canvas=document.createElement('canvas'); canvas.width=64; canvas.height=4;
    const gl=canvas.getContext(c.version===300?'webgl2':'webgl',
      {antialias:false,preserveDrawingBuffer:true});
    if(!gl) throw new Error('GLES unavailable');
    const program=gl.createProgram(), errors=[];
    for(const [type,source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,c.f]]) {
      const shader=gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) errors.push(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    if(!errors.length) {
      gl.linkProgram(program);
      if(!gl.getProgramParameter(program,gl.LINK_STATUS)) errors.push(gl.getProgramInfoLog(program));
    }
    const checks=[];
    if(!errors.length && !c.compile_only) {
      gl.useProgram(program); gl.viewport(0,0,64,4);
      const uniform=name=>gl.getUniformLocation(program,name);
      const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
      for(const name of ['WORLD','WORLDVIEWPROJ','WORLDVIEW','PROJ','BONE'])
        gl.uniformMatrix4fv(uniform(name),false,identity);
      gl.uniform4f(uniform('TILE_LIGHT_COLOR'),.25,.5,.75,1);
      gl.uniform4f(uniform('OVERLAY_COLOR'),0,0,0,0);
      gl.uniform4f(uniform('FOG_COLOR'),0,0,0,0);
      gl.uniform2f(uniform('FOG_CONTROL'),10,20);
      gl.uniform1f(uniform('RENDER_DISTANCE'),1);
      const position=gl.getAttribLocation(program,'POSITION');
      gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,1,3,-1,0,1,-1,3,0,1]),gl.STATIC_DRAW);
      gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,4,gl.FLOAT,false,0,0);
      const normal=gl.getAttribLocation(program,'NORMAL');
      if(normal>=0) gl.vertexAttrib4f(normal,0,1,0,0);
      const uv=gl.getAttribLocation(program,'TEXCOORD_0');
      if(uv>=0) gl.vertexAttrib2f(uv,.5,.5);
      for(let unit=0;unit<3;++unit) {
        gl.activeTexture(gl.TEXTURE0+unit); gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
        gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,
          new Uint8Array(unit===0?[180,120,60,255]:[0,0,0,0]));
        gl.uniform1i(uniform('TEXTURE_'+unit),unit);
      }
      gl.drawArrays(gl.TRIANGLES,0,3);
      for(let stripe=0;stripe<4;++stripe) {
        const pixel=new Uint8Array(4);
        gl.readPixels(stripe*16+8,1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
        const expected=c.expected[stripe],actual=Array.from(pixel),error=gl.getError();
        checks.push({stripe,actual,expected,error,
          passed:!error && expected.every((value,i)=>Math.abs(value-actual[i])<=2)});
      }
    }
    results.push({name:c.name,errors,checks,passed:!errors.length&&checks.every(c=>c.passed)});
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
  return results;
}'''


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    variants = [('plain', ()), ('fancy', ('FANCY',)),
                ('alpha', ('FANCY', 'ALPHA_TEST')),
                ('unlit', ('FANCY', 'RNGL_UNLIT')),
                ('always_lit', ('FANCY', 'ALWAYS_LIT')),
                ('skinning', ('FANCY', 'USE_SKINNING'))]
    cases = []
    for version in (100, 300):
        for name, flags in variants:
            expected = [[255., 0., 255., 255.], [63.75, 127.5, 191.25, 255.],
                        [63.75, 127.5, 191.25, 255.],
                        [255. if 'FANCY' in flags else 0.,
                         255./7. if 'RNGL_UNLIT' in flags else 0.,
                         255. if 'ALWAYS_LIT' in flags else 0., 255.]]
            cases.append({'name': name+'/'+str(version), 'version': version,
                'v': shader_source(args.headers/'entity.vertex', args.headers, version, flags),
                'f': shader_source(args.project/FRAGMENT, args.headers, version, flags),
                'expected': expected, 'compile_only': 'USE_SKINNING' in flags})
            if 'USE_SKINNING' in flags:
                baseline = shader_source(args.headers/'entity.fragment', args.headers, version, flags)
                boundary = baseline.index('\n')+1
                baseline = baseline[:boundary]+'precision highp float;\nprecision highp int;\n'+baseline[boundary:]
                cases.append(dict(cases[-1], name='native_skinning/'+str(version),
                                  f=baseline))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    native_failures = {row['name'].split('/')[-1]: row['errors'] for row in results
                       if row['name'].startswith('native_skinning/') and not row['passed']}
    inherited = [row['name'] for row in results if not row['passed'] and
                 row['name'].split('/')[0] in ('skinning', 'native_skinning') and
                 row['errors'] == native_failures.get(row['name'].split('/')[-1])]
    passed = all(row['passed'] or row['name'] in inherited for row in results)
    report = {'passed': passed, 'programs': len(results),
              'pixel_checks': sum(len(row['checks']) for row in results),
              'inherited_native_failures': inherited, 'results': results,
              'native_appearance_qualified': False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({key: report[key] for key in ('passed', 'programs', 'pixel_checks',
                                                'inherited_native_failures')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

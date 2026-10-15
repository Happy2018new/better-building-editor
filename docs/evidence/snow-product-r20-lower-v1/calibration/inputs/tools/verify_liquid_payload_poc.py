"""Compile generated shaders and check synthetic carrier vertices in GLES 2/3."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from liquid_payload_poc import decode_vertex
from verify_biome_shader import shader_source

RENDER = '''cases => {
  const results = [];
  for (const item of cases) {
    const canvas = document.createElement('canvas');
    canvas.width = 1; canvas.height = 1;
    const gl = canvas.getContext(item.version === 100 ? 'webgl' : 'webgl2', {antialias:false});
    if (!gl) { results.push({name:item.name,linked:false,error:'missing GL context'}); continue; }
    function compile(type, source) {
      const shader=gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
      return shader;
    }
    try {
      const program=gl.createProgram();
      gl.attachShader(program,compile(gl.VERTEX_SHADER,item.vertex));
      gl.attachShader(program,compile(gl.FRAGMENT_SHADER,item.fragment)); gl.linkProgram(program);
      if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
      gl.useProgram(program); gl.viewport(0,0,1,1);
      const position=gl.getAttribLocation(program,'POSITION');
      const uv=gl.getAttribLocation(program,'TEXCOORD_0');
      const matrix=new Float32Array(16); matrix[15]=1;
      gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,matrix);
      gl.uniform4fv(gl.getUniformLocation(program,'EXTRA_ACTOR_UNIFORM1'),[1,1,1,1]);
      gl.uniform4fv(gl.getUniformLocation(program,'EXTRA_ACTOR_UNIFORM2'),[0,0,1,1]);
      gl.uniform4fv(gl.getUniformLocation(program,'EXTRA_ACTOR_UNIFORM3'),[.25,.5,.125,.125]);
      gl.uniform4fv(gl.getUniformLocation(program,'EXTRA_ACTOR_UNIFORM4'),[39683,item.denominator,1,1]);
      gl.disableVertexAttribArray(position); gl.disableVertexAttribArray(uv);
      const failures=[];
      for (const fixture of item.fixtures) {
        gl.vertexAttrib4fv(position,fixture.position); gl.vertexAttrib2fv(uv,fixture.uv);
        gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.POINTS,0,1);
        const actual=new Uint8Array(4); gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,actual);
        if (actual.some((value,index)=>Math.abs(value-fixture.expected[index])>1)) {
          failures.push({name:fixture.name,actual:[...actual],expected:fixture.expected});
        }
      }
      results.push({name:item.name,linked:true,checks:item.fixtures.length,failures,passed:failures.length===0});
    } catch(error) {
      results.push({name:item.name,linked:false,error:String(error),passed:false});
    }
    gl.getExtension('WEBGL_lose_context').loseContext();
  }
  return results;
}'''


def fixtures(bits):
    count = 1 << bits
    rows = []
    for index in (0, 1, 21, 63):
        for kind in range(7):
            for corner in ((0, 0), (1, 0), (1, 1), (0, 1)):
                for half in (False, True):
                    codes = (count - 1, index + kind * 64, count // 3)
                    third = (index * 17) % count
                    position = [codes[0] + corner[0] * 0.5 - 0.25,
                                float(codes[1]), codes[2] + corner[1] * 0.5 - 0.25, 1.0]
                    if half:
                        position = [struct.unpack('e', struct.pack('e', value))[0] for value in position]
                    point = decode_vertex(codes, third, corner, bits)
                    uv = [.25 + (third % 64) / 64 * .125,
                          .5 + (third // 64) / 64 * .125]
                    rows.append({'name': '%s/%s/%s/half=%s' % (index, kind, corner, half),
                                 'position': position, 'uv': uv,
                                 'expected': [axis / 4 * 255 for axis in point] + [255]})
    return rows


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    shaders = args.overlay / 'resource_pack/shaders/glsl'
    cases = []
    identities = {name: hashlib.sha256((shaders / ('liquid_payload_poc.' + name)).read_bytes()).hexdigest()
                  for name in ('vertex', 'fragment')}
    for version in (100, 300):
        for bits in (6, 8):
            for flags in (('BLEND',), ('BLEND', 'FOG')):
                cases.append({'name': '%d/%dbit/%s' % (version, bits, ','.join(flags)),
                              'version': version, 'denominator': (1 << bits) - 1,
                              'vertex': shader_source(shaders / 'liquid_payload_poc.vertex', args.headers, version, flags),
                              'fragment': shader_source(shaders / 'liquid_payload_poc.fragment', args.headers, version, flags),
                              'fixtures': fixtures(bits)})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    report = {'schema_version': 1, 'shader_sha256': identities, 'results': results,
              'checks': sum(row.get('checks', 0) for row in results),
              'passed': all(row.get('passed', False) for row in results),
              'native_geometry_accepted': False, 'accuracy_accepted': False,
              'native_input_format_verified': False, 'animated_sampling_accepted': False,
              'scope': 'Expanded installed game headers, GLES 2/3 and synthetic float/half-float carriers only'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

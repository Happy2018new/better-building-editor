"""Exercise unchanged shared shaders with overhanging synthetic native quads."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_biome_shader import shader_source

RENDER = r'''cases => {
 const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
 const results=[];
 for(const c of cases) {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=64;
  const gl=canvas.getContext(c.version===300?'webgl2':'webgl',
    {antialias:false,alpha:true,premultipliedAlpha:false,preserveDrawingBuffer:true});
  if(!gl) throw Error('No WebGL context');
  gl.disable(gl.DITHER);gl.disable(gl.BLEND);gl.disable(gl.CULL_FACE);
  const debug=gl.getExtension('WEBGL_debug_renderer_info');
  const result={name:c.name,renderer:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),checks:[]};
  const program=gl.createProgram();
  for(const [type,source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,c.f]]) {
   const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
   if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
   gl.attachShader(program,shader);
  }
  gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  const uniform=name=>gl.getUniformLocation(program,name);
  const projection=identity.slice();projection[15]=0;
  gl.uniformMatrix4fv(uniform('PROJ'),false,projection);
  gl.uniformMatrix4fv(uniform('WORLD'),false,identity);
  gl.uniformMatrix4fv(uniform('WORLDVIEW'),false,identity);
  gl.uniform4f(uniform('TILE_LIGHT_COLOR'),1,1,1,1);
  gl.uniform4f(uniform('CURRENT_COLOR'),1,1,1,1);
  const color=gl.getAttribLocation(program,'COLOR');if(color>=0) gl.vertexAttrib4f(color,1,1,1,1);
  for(const name of ['TEXCOORD_0','TEXCOORD_1']) {
   const location=gl.getAttribLocation(program,name);if(location>=0) gl.vertexAttrib2f(location,.5,.5);
  }
  for(let unit=0;unit<2;++unit) {
   gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([180,120,60,255]));
   gl.uniform1i(uniform('TEXTURE_'+unit),unit);
  }
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
  const location=gl.getAttribLocation(program,'POSITION');
  gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,4,gl.FLOAT,false,0,0);
  for(const test of c.fixtures) {
   const matrix=new Array(16).fill(0);matrix[test.axes[0]*4]=4;
   matrix[test.axes[1]*4+1]=4;matrix[15]=1;
   gl.uniformMatrix4fv(uniform('WORLDVIEWPROJ'),false,matrix);
   const vertices=[];
   for(const corner of [[-.2,-.2],[.2,-.2],[-.2,.2],[.2,-.2],[.2,.2],[-.2,.2]]) {
    const point=[0,0,0];point[test.axis]=test.distance;
    point[test.axes[0]]=corner[0];point[test.axes[1]]=corner[1];
    for(let axis=0;axis<3;++axis) point[axis]+=test.packed?1:0;
    vertices.push(...point,1);
   }
   gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
   gl.uniform4f(uniform('EXTRA_ACTOR_UNIFORM4'),19487,1,test.active_bank,test.opacity);
   gl.uniform4f(uniform('EXTRA_ACTOR_UNIFORM1'),0,0,0,19490);
   gl.uniform1f(uniform('COMMON_BLOCK_GEO_FLOAT1_1'),test.common);
   gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,6);
   const pixels=new Uint8Array(64*64*4);gl.readPixels(0,0,64,64,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   let visible=0;for(let i=3;i<pixels.length;i+=4) if(pixels[i]>0) ++visible;
   const actual=Array.from(pixels.slice((32*64+32)*4,(32*64+32)*4+4));
   const error=gl.getError();
   const passed=error===0 && (test.expect_visible ? visible>2500 && actual[3]===255 : visible===0);
   result.checks.push({...test,visible_pixels:visible,center_rgba:actual,gl_error:error,passed});
  }
  result.passed=result.checks.every(test=>test.passed);results.push(result);
  gl.getExtension('WEBGL_lose_context').loseContext();
 }
 return results;
}'''


def fixtures():
    rows = []
    for axis, axes, distances in ((1, (0, 2), (.49, .581528254, .653281482, -.58)),
                                  (2, (0, 1), (.49, .653281482, -.58))):
        for distance in distances:
            for bank in (0, 1):
                for packed in (False, True):
                    for stale in (False, True):
                        rows.append(dict(name='axis%d/%s/bank%d/%s/%s' % (
                            axis, distance, bank + 1, 'context' if packed else 'overlay',
                            'stale' if stale else 'active'), axis=axis, axes=axes,
                            distance=distance, packed=packed,
                            common=(.25 if packed else .125) + .5 * bank,
                            active_bank=2-bank if stale else bank+1,
                            opacity=1., expect_visible=not stale and (not packed or abs(distance) < .5)))
    return rows


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT / '.runtime/projects/book-r20')
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', default='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    vertex = args.project / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex'
    fragment = args.project / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
    cases = []
    for version in (100, 300):
        for flags in ((), ('BLEND', 'ALPHA_TEST', 'ENABLE_SET_TRANSPARENCY')):
            cases.append(dict(name='%s/%s' % (version, ','.join(flags)), version=version,
                v=shader_source(vertex, args.headers, version, flags),
                f=shader_source(fragment, args.headers, version, flags), fixtures=fixtures()))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        results = browser.new_page().evaluate(RENDER, cases)
        browser.close()
    report = dict(schema=1, stage='synthetic_shared_shader_raster',
        created_at=datetime.now(timezone.utc).isoformat(), product_qualified=False,
        native_lectern_pixels_qualified=False, successful=all(row['passed'] for row in results),
        programs=len(results), checks=sum(len(row['checks']) for row in results), results=results,
        sources={str(path): sha(path) for path in (vertex, fragment, Path(__file__),
            args.project/'resource_pack/materials/terrain.material',
            args.project/'behavior_pack/modern_projection/projection/occupancy_shader.py')},
        limits=['Real unchanged shaders, synthetic axis-aligned quads and SwiftShader only.',
                'Distances include both experimental lectern rotation-sign overhang references.',
                'No native geometry extraction, native lectern texture or real game pixel acceptance.',
                'No change to global clip or native/rendered book ownership.'])
    args.output.write_text(json.dumps(report, indent=2), encoding='ascii')
    print(json.dumps({key: report[key] for key in ('successful', 'programs', 'checks')}))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

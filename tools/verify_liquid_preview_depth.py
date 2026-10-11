"""Replay the shared liquid depth header with installed headers on host GLES.

This verifies affine depth consistency, not the native skeleton's UI bindings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.preview_depth import depth_color
from verify_biome_shader import shader_source

HEADER = ROOT / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'
VERTEX = '''precision highp float;
#include "vertexVersionCentroid.h"
#include "uniformWorldConstants.h"
#include "modern_projection_liquid_preview_depth.h"
attribute vec4 POSITION;
varying highp vec4 sampleColor;
void main() {
    vec4 projected = vec4(0.2,0.3,0.4,0.8);
    float clip;
    liquidPreviewDepth(POSITION.xyz, projected, clip);
    sampleColor=vec4((clip+256.0)/512.0, (projected.z+1.0)*0.5, projected.x, projected.y);
    gl_Position=vec4(0.0,0.0,0.0,1.0);
    gl_PointSize=1.0;
}
'''
FRAGMENT = '''precision highp float;
#include "fragmentVersionCentroid.h"
varying highp vec4 sampleColor;
void main() { gl_FragColor=sampleColor; }
'''
RENDER = '''cases => cases.map(item => {
 const canvas=document.createElement('canvas');canvas.width=1;canvas.height=1;
 const gl=canvas.getContext(item.version===100?'webgl':'webgl2',{antialias:false});
 if(!gl)return {name:item.name,passed:false,error:'GL unavailable'};
 try {
  function compile(type,source){const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
   if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));return shader;}
  const program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,item.vertex));
  gl.attachShader(program,compile(gl.FRAGMENT_SHADER,item.fragment));gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
  const position=gl.getAttribLocation(program,'POSITION');gl.disableVertexAttribArray(position);
  const failures=[];
  for(const fixture of item.fixtures){
   gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEW'),false,fixture.worldview);
   gl.uniformMatrix4fv(gl.getUniformLocation(program,'PROJ'),false,fixture.projection);
   gl.uniform4fv(gl.getUniformLocation(program,'CURRENT_COLOR'),fixture.color);
   gl.vertexAttrib4fv(position,[...fixture.point,1]);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
   gl.drawArrays(gl.POINTS,0,1);const actual=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,actual);
   if(actual.some((v,i)=>Math.abs(v-fixture.expected[i])>1))failures.push({name:fixture.name,actual:[...actual],expected:fixture.expected});
  }
  return {name:item.name,passed:failures.length===0,checks:item.fixtures.length,failures};
 }catch(error){return {name:item.name,passed:false,error:String(error)};}
 finally{gl.getExtension('WEBGL_lose_context').loseContext();}
})'''


def fixtures():
    rows = []
    # One world point represented relative to different batch centers must
    # have the same depth. Include zoom-dependent native transform scales.
    for center in ((0., 0., 0.), (4., 2., -8.), (-64., 100., 64.)):
        for scale in (.01, .1, 1., 20.):
            for tagged, perspective in ((True, False), (False, False), (True, True)):
                viewpoint = (2., 1., 2.)
                toward = (2. / 3., 1. / 3., 2. / 3.)
                point = tuple(viewpoint[i] - center[i] for i in range(3))
                distance = sum(center[i] * toward[i] for i in range(3)) - 8.
                color = depth_color(distance, 'plains', (4, 4)) if tagged else (.1, .2, .3)
                color += (1.,)
                world = [0.] * 16
                world[2], world[6], world[10], world[15] = tuple(v * scale for v in toward) + (1.,)
                projection = [0.] * 16
                projection[0], projection[5], projection[10], projection[14], projection[15] = (
                    1., 1., -.002, .2, 0. if perspective else 1.)
                clip, depth = -1., .4
                if tagged and not perspective:
                    decoded_distance = (round(color[2] * 65536.) - 32768.) / 64.
                    clip = sum(point[i] * toward[i] for i in range(3)) + decoded_distance
                    depth = (.9 + clip * -.002 * .04) / 1.9
                expected = [round((clip + 256.) / 512. * 255.),
                            round((depth + 1.) * .5 * 255.), 51, 76]
                rows.append({'name': '%s/%s/%s/%s' % (center, scale, tagged, perspective),
                             'point': point, 'color': color, 'worldview': world,
                             'projection': projection, 'expected': expected})
    return rows


def main():
    from playwright.sync_api import sync_playwright
    import tempfile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report path')
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        vertex, fragment = temp / 'check.vertex', temp / 'check.fragment'
        vertex.write_text(VERTEX.replace('#include "' + HEADER.name + '"',
                                        HEADER.read_text(encoding='ascii')), encoding='ascii')
        fragment.write_text(FRAGMENT, encoding='ascii')
        cases = [{'name': 'GLES%d' % version, 'version': version,
                  'vertex': shader_source(vertex, args.headers, version, ()),
                  'fragment': shader_source(fragment, args.headers, version, ()), 'fixtures': fixtures()}
                 for version in (100, 300)]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    report = {'schema': 1, 'passed': all(row['passed'] for row in results), 'results': results,
              'header_sha256': hashlib.sha256(HEADER.read_bytes()).hexdigest(),
              'scope': 'Host shared-depth math; native UI binding and geometry remain separate',
              'native_binding_accepted': False, 'production_editor_accepted': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

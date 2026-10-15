"""Read actual candidate UI ray/plane outputs on host WebGL2 affine fixtures."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'

from verify_portal_native_adapter_r20 import expanded_shader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.runtime/browser_packages'))

JS = r'''item => {
 const canvas=document.createElement('canvas');canvas.width=1;canvas.height=1;
 const gl=canvas.getContext('webgl2',{antialias:false});
 if(!gl)throw Error('WebGL2 unavailable');
 const program=gl.createProgram();
 const fragment='#version 300 es\nprecision highp float;\nin lowp vec4 checkPlane;\nout vec4 color;\nvoid main(){color=checkPlane;}';
 for(const [type,source] of [[gl.VERTEX_SHADER,item.vertex],[gl.FRAGMENT_SHADER,fragment]]){
  const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
  if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));
  gl.attachShader(program,shader);
 }
 gl.transformFeedbackVaryings(program,['checkUV','checkPlane'],gl.INTERLEAVED_ATTRIBS);
 gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
 gl.useProgram(program);
 for(const name of ['WORLDVIEWPROJ','PROJ'])gl.uniformMatrix4fv(gl.getUniformLocation(program,name),false,item.identity);
 for(const [name,value] of Object.entries({EXTRA_VECTOR1:[4095,0,0,0],EXTRA_VECTOR2:[65535,65535,0,0],EXTRA_VECTOR4:[39686,0,0,0]}))
  gl.uniform4fv(gl.getUniformLocation(program,name),value);
 gl.uniform1f(gl.getUniformLocation(program,'TIME'),64);
 const position=gl.getAttribLocation(program,'POSITION'),normal=gl.getAttribLocation(program,'NORMAL');
 const feedback=gl.createTransformFeedback();gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,feedback);
 const buffer=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,buffer);
 gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,32,gl.STATIC_READ);gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,buffer);
 const failures=[];let maxError=0,pixelMaxError=0;
 for(const fixture of item.fixtures){
  gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEW'),false,fixture.worldview);
  gl.vertexAttrib4fv(position,fixture.position);gl.vertexAttrib4fv(normal,[...fixture.normal,0]);
  gl.clear(gl.COLOR_BUFFER_BIT);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,1);gl.endTransformFeedback();
  const actual=new Float32Array(8);gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,actual);
  const pixel=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
  const error=Math.max(...actual.map((v,i)=>Math.abs(v-fixture.expected[i])));
  const pe=Math.max(...pixel.map((v,i)=>Math.abs(v-Math.round(fixture.expected[i+4]*255))));
  maxError=Math.max(maxError,error);pixelMaxError=Math.max(pixelMaxError,pe);
  if((!Number.isFinite(error)||error>.00015||pe>1)&&failures.length<12)
   failures.push({name:fixture.name,actual:[...actual],expected:fixture.expected,pixel:[...pixel],error,pixelError:pe});
 }
 const glError=gl.getError();gl.getExtension('WEBGL_lose_context').loseContext();
 return {passed:!failures.length&&!glError,fixtures:item.fixtures.length,maxError,pixelMaxError,glError,failures};
}'''


def fixtures():
    import numpy as np
    angle = .71
    rotate = np.array(((math.cos(angle), 0., math.sin(angle)), (0., 1., 0.),
                       (-math.sin(angle), 0., math.cos(angle))))
    matrices = (('identity', np.eye(3), (0., 0., 0.)),
                ('translated', np.eye(3), (2.7, -4.3, 6.1)),
                ('rotated', rotate, (2.7, -4.3, 6.1)),
                ('scaled_rotated', rotate @ np.diag((.13, 2.7, 1.3)), (2.7, -4.3, 6.1)),
                ('sheared', np.array(((1.7, .2, .1), (.3, .7, .4), (.1, .2, 1.2))), (2.7, -4.3, 6.1)),
                ('reflected', rotate @ np.diag((-1.2, .6, 2.1)), (-1.7, 3.3, -5.1)),
                ('zero_scale', np.zeros((3, 3)), (2.7, -4.3, 6.1)),
                ('near_zero_scale', np.diag((.000001, .000001, .000001)), (2.7, -4.3, 6.1)))
    normals = ((0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0), (0, -1, 0))
    points = ((.3, 1., .6), (.3, .6, 0.), (.7, .6, 1.),
              (0., .6, .7), (1., .6, .3), (.7, 0., .6))
    rows = []
    for label, linear, translation in matrices:
        matrix = np.eye(4)
        matrix[:3, :3], matrix[:3, 3] = linear, translation
        for face, (normal, point) in enumerate(zip(normals, points)):
            local = np.array(point) + 1.
            entity = np.array((-local[0], -local[2] + 1.5, -local[1]))
            valid = abs(np.linalg.det(linear)) > .000000000001
            ray = entity + np.linalg.solve(linear, np.array(translation)) if valid else np.zeros(3)
            n = np.array((-normal[0], -normal[2], -normal[1]))
            for layer in tuple(range(16)) + (32,):
                distance = 32. if layer > 31 else math.floor(layer * 255. / 16.) * 32. / 255.
                encoded = list((n + 1.) * .5) + [distance / 32.]
                rows.append({'name': label + '/face%d/layer%d' % (face, layer),
                             'worldview': matrix.T.flatten().tolist(),
                             'position': [.3, face * 2. + .6, layer, 1.], 'normal': normal,
                             'expected': list(ray) + [float(valid)] + encoded})
    return rows


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--native-shaders', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    local = args.project / 'resource_pack/shaders/glsl'
    shader = local / 'modern_projection_portal_native_ui.vertex'
    source = expanded_shader(shader, local, args.native_shaders, 300, ())
    source = source.replace('void main() {', 'out highp vec3 checkRay;\nvoid portalMain() {', 1)
    source = source.replace('    float denominator=dot(viewRay,planeNormal);',
                            '    checkRay=viewRay;\n    float denominator=dot(viewRay,planeNormal);', 1)
    source += '''
out highp vec4 checkUV;
out lowp vec4 checkPlane;
void main(){portalMain();checkUV=vec4(checkRay,portalVisible);
checkPlane=encodedPlane;gl_Position=vec4(0.,0.,0.,1.);gl_PointSize=1.;}
'''
    item = {'vertex': source, 'identity': [1., 0., 0., 0., 0., 1., 0., 0.,
                                         0., 0., 1., 0., 0., 0., 0., 1.], 'fixtures': fixtures()}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            result = browser.new_page().evaluate(JS, item)
        finally:
            browser.close()
    report = {'schema': 1, 'result': result, 'shader_sha256': hashlib.sha256(shader.read_bytes()).hexdigest(),
              'scope': 'Host GPU affine UI ray/normal algebra and encoded-plane pixels',
              'native_ui_matrix_bindings_observed': False, 'qualification': False,
              'cpu_reference': 'entity + numpy.linalg.solve(WORLDVIEW.linear, WORLDVIEW.translation)'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps(report))
    assert result['passed']


if __name__ == '__main__':
    main()

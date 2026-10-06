"""Check the actual native glow decoder with WebGL2 transform feedback.

Requires Playwright, Chromium and the installed game's GLSL headers. Run:
    python tools/verify_native_transport.py --headers <game/data/shaders/glsl>
        --browser <chromium.exe> --report <result.json>

Exercises quantization, atlas inset, all visible IDs, sentinel rejection and
interpolated motion/formation channels. Does not verify Minecraft draw order.
"""
import argparse
from functools import lru_cache
import itertools
import json
import math
import re
import struct
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from playwright.sync_api import sync_playwright
from test_native_glow import aura_packet, survey_packet, aura_attributes, survey_attributes

SHADERS = ROOT / 'resource_pack/shaders/glsl'
VISIBLE = {'aura': 176, 'survey': 971, 'strike': 328}
MATH = types.SimpleNamespace(mod=lambda a, b: a % b, floor=math.floor)
F32 = lambda x: struct.unpack('f', struct.pack('f', x))[0]


def shader(kind, game_headers):
    headers = (SHADERS, game_headers)
    seen = set()
    def expand(text):
        def include(m):
            name = m.group(1)
            if name in seen:
                return ''
            seen.add(name)
            path = next(p / name for p in headers if (p / name).exists())
            return expand(path.read_text(encoding='utf8'))
        return re.sub(r'^\s*#include\s+"([^"]+)".*$', include, text, flags=re.M)
    name = 'modern_projection_aura.vertex' if kind == 'aura' else 'modern_projection_survey_stars.vertex'
    text = expand((SHADERS / name).read_text(encoding='utf8'))
    text = text.replace('void main(){', 'void effectMain(){')
    defines = ['NATIVE_GLOW', 'AURA_GLOW' if kind == 'aura' else 'SURVEY_GLOW']
    if kind == 'strike':
        defines.append('SURVEY_STRIKE')
    prefix = '#version 300 es\nprecision highp int;\n#define MCPE_NETEASE\n#define MAT4 highp mat4\n#define POS4 highp vec4\n'
    prefix += ''.join('#define ' + d + '\n' for d in defines)
    wrapper = '\n' + '\n'.join('out highp vec4 probe%d;' % i for i in range(6))
    wrapper += '\nvoid main(){gl_Position=vec4(0.,0.,0.,1.);probe0=vec4(-1.);'
    wrapper += ''.join('probe%d=vec4(0.);' % i for i in range(1, 6))
    wrapper += 'if(!%s())return;' % ('nativeAura' if kind == 'aura' else 'nativeSurvey')
    wrapper += 'probe0=vec4(1.,nativeId,nativeCorner);'
    wrapper += ''.join('probe%d=EXTRA_ACTOR_UNIFORM%d;' % (i, i) for i in range(1, 4 if kind == 'aura' else 5))
    wrapper += 'probe5=vec4(nativeOrigin,1.);}\n'
    return prefix + text + wrapper


@lru_cache(maxsize=3)
def components(kind):
    path = ROOT / ('resource_pack/particles/modern_projection_' + kind + '_glow.json')
    return json.loads(path.read_text(encoding='utf8'))['particle_effect']['components']


def attributes(kind, packet, index, corner, quantize=round, inset=0):
    scope = {'v': types.SimpleNamespace(particle_lifetime=1048576 + index, **packet), 'math': MATH}
    parts = components(kind)
    uv_def = parts['minecraft:particle_appearance_billboard']['uv']
    base = [eval(s, {'__builtins__': {}}, scope) for s in uv_def['uv']]
    texels = [base[i] + (uv_def['uv_size'][i] if corner[i] > 0 else 0) - corner[i] * inset for i in range(2)]
    uv = [quantize(F32(F32(v / uv_def['texture_width']) * 65535)) / 65535 for v in texels]
    color = [eval(s, {'__builtins__': {}}, scope) * 255 for s in parts['minecraft:particle_appearance_tinting']['color'][:3]] + [packet['alpha']]
    data = [int(base[i] // 4) for i in range(2)]
    return uv, color, data


def record(kind, packet, index, corner, other=None, fraction=0, hidden=False, quantize=round, inset=0):
    uv, color, data = attributes(kind, packet, index, corner, quantize, inset)
    if other:
        next_uv, next_color, next_data = attributes(kind, other, index, corner, quantize, inset)
        assert data == next_data and uv == next_uv
        color = [a + (b - a) * fraction for a, b in zip(color, next_color)]
    if hidden:
        color[3] = 0
    row = [1, 2, 3, 1] + [v / 255 for v in color] + uv
    expected = [-1] * 4 + [0] * 20
    if not hidden and index < VISIBLE[kind]:
        origin = [1 - corner[0] * 1e-6, 2 + corner[1] * 1e-6, 3]
        if kind == 'aura':
            d = aura_attributes(data, color)
            uniforms = [d['entered'], d['tool'], d['motion'], d['third_person']]
            uniforms += list(d['velocity']) + [math.sqrt(sum(v * v for v in d['velocity']))]
            uniforms += list(d['seeds']) + [d['switching'], 1] + [0] * 4
        else:
            d = survey_attributes(data, color, kind == 'strike')
            uniforms = list(d['size']) + [0] + [0] * 4
            uniforms += [d['entered'], d['brightness'], d['theme'] + .1, d['orbit']]
            uniforms += [-v for v in origin] + [d['face'] if kind == 'strike' else d['density']]
        expected = [1, d['id']] + list(corner) + uniforms + origin + [1]
    return row, expected


def cases(headers):
    output = []
    corners = list(itertools.product((-1, 1), repeat=2))
    for kind in VISIBLE:
        rows, wanted = [], []
        def add(*args, **kwargs):
            row, expected = record(kind, *args, **kwargs)
            rows.extend(row)
            wanted.extend(expected)
        packet = (aura_packet((1, 1, 1), (-7, 7, -7), (255, 255, .5, 1), 1)[0] if kind == 'aura'
                  else survey_packet((64, 128, 64), 5 if kind == 'strike' else None, (1, 1.5, 1.1, 3), 1.8)[0])
        for quantize in (round, math.floor):
            for inset in (0, .25, .5):
                for index in range(VISIBLE[kind] + 1):
                    for corner in corners:
                        add(packet, index, corner, quantize=quantize, inset=inset)
            for index in (0, VISIBLE[kind]):
                for corner in corners:
                    add(packet, index, corner, hidden=True, quantize=quantize)
        if kind == 'aura':
            for flags, birth, axis, code in itertools.product(((0, 0, 0), (1, 1, 1), (1, 1, 0)), (0, .4, 1), range(3), (0, 15, 27, 31, 47, 59, 61)):
                a, b = [0] * 3, [0] * 3
                a[axis], b[axis] = (code - 31) * 7 / 31, (code - 30) * 7 / 31
                before = aura_packet(flags, a, (77, 255, .3, 1), birth)[0]
                after = aura_packet(flags, b, (77, 255, .6, 1), birth)[0]
                for fraction, corner in itertools.product((0, .1, .25, .5, .75, .9, 1), corners):
                    add(before, 112, corner, other=after, fraction=fraction)
        else:
            for theme, entered in itertools.product((0, 1), (0, 10/254, .5, 253/254)):
                face = 5 if kind == 'strike' else None
                before = survey_packet((64, 128, 64), face, (entered, .3, theme + .1, 0), .3)[0]
                after = survey_packet((64, 128, 64), face, (min(1, entered + 1/254), 1.5, theme + .1, 3), 1.8)[0]
                for index, fraction, corner in itertools.product((0, 127, 255, VISIBLE[kind]-1, VISIBLE[kind]), (0, .1, .25, .5, .75, .9, 1), corners):
                    add(before, index, corner, other=after, fraction=fraction)
        output.append({'name': kind, 'v': shader(kind, headers), 'rows': rows, 'expected': wanted})
    return output


JS = r'''(cases)=>{
 const gl=document.createElement('canvas').getContext('webgl2');
 if(!gl)throw Error('WebGL2 unavailable');
 const result=[];
 for(const c of cases){
  const program=gl.createProgram();
  for(const [type,source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,'#version 300 es\nprecision highp float;\nout vec4 color;\nvoid main(){color=vec4(0.);}\n']]){
   const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(c.name+' compile: '+gl.getShaderInfoLog(s));
   gl.attachShader(program,s);
  }
  gl.transformFeedbackVaryings(program,[0,1,2,3,4,5].map(i=>'probe'+i),gl.INTERLEAVED_ATTRIBS);
  gl.linkProgram(program);
  if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(c.name+' link: '+gl.getProgramInfoLog(program));
  gl.useProgram(program);
  const vao=gl.createVertexArray();gl.bindVertexArray(vao);
  const input=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,input);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(c.rows),gl.STATIC_DRAW);
  for(const [name,size,offset] of [['POSITION',4,0],['COLOR',4,16],['TEXCOORD_0',2,32]]){
   const loc=gl.getAttribLocation(program,name);if(loc<0)throw Error(name+' absent');
   gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,40,offset);
  }
  gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]));
  const feedback=gl.createTransformFeedback();gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,feedback);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,buffer);gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,c.expected.length*4,gl.STATIC_READ);gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,buffer);
  gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,c.rows.length/10);gl.endTransformFeedback();gl.disable(gl.RASTERIZER_DISCARD);
  const actual=new Float32Array(c.expected.length);gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,actual);
  const errors=[];let mismatches=0,maxError=0;
  for(let i=0;i<actual.length;i++){const delta=Math.abs(actual[i]-c.expected[i]);maxError=Math.max(maxError,delta);if(!Number.isFinite(actual[i])||delta>.0005){mismatches++;if(errors.length<8)errors.push({row:Math.floor(i/24),field:i%24,expected:c.expected[i],actual:actual[i]});}}
  const err=gl.getError();result.push({name:c.name,vertices:c.rows.length/10,mismatches,maxError,glError:err,errors});
  gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,null);gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,null);gl.deleteTransformFeedback(feedback);gl.deleteBuffer(buffer);gl.deleteBuffer(input);gl.deleteVertexArray(vao);gl.deleteProgram(program);
 }
 return result;
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page()
        result = page.evaluate(JS, cases(args.headers))
        browser.close()
    print(json.dumps(result, indent=2))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding='utf8')
    assert not any(r['mismatches'] or r['glError'] for r in result)


if __name__ == '__main__':
    main()

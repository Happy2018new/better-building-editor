"""Verify frozen diagnostic shaders offline; no Minecraft connection or writes."""
import argparse
import itertools
import json
import math
from pathlib import Path
import struct

from prepare_frame_item_translation import generated_shader, sha256
from verify_biome_shader import shader_source

F32 = lambda value: struct.unpack('f', struct.pack('f', value))[0]


def check_bundle(bundle):
    plan = json.loads((bundle / 'plan.json').read_bytes())
    if plan.get('production_rendering_accepted') is not False or plan.get('sdk_dispatch_authorized') is not False:
        raise ValueError('The bundle must remain unaccepted preparation')
    for row in plan['sources'] + plan['generated']:
        path = (bundle / row['path']).resolve()
        if not path.is_relative_to(bundle.resolve()):
            raise ValueError('Bundle source escapes its directory')
        payload = path.read_bytes()
        if len(payload) != row['bytes'] or sha256(payload) != row['sha256']:
            raise ValueError('Frozen source changed: ' + row['path'])
    original = (bundle / 'original.vertex').read_bytes()
    for name, shift in (('nooffset.vertex', 0), ('translated.vertex', 2)):
        if (bundle / name).read_bytes() != generated_shader(original, shift):
            raise ValueError('Diagnostic shader differs from its declared change')
    return plan


def packet(height=8, offset=9, tag=209.25):
    return [F32(tag / 255.), F32((height + offset * 256) / 131072.), F32(32768 / 65536.), 1.]


def oracle(position, color, projection, shift):
    tag = math.floor(F32(color[0] * 255.) + .5)
    fraction = F32(color[0] * 255.) % 1.
    layout = projection == 'editor' and 209 <= tag <= 222 and fraction > .125
    height = offset = 0
    value = list(position)
    if layout:
        packed = math.floor(F32(color[1] * 131072.) + .5)
        height, offset = packed % 256, packed // 256
        value[1] += (height + offset) / 2.
    selected = layout and height == 8 and offset == 9 and 8.5 <= value[1] <= 16.5
    if layout and offset > .5 and value[1] >= offset - .5:
        value[1] -= offset
    if layout:
        value[1] -= height / 2.
    if selected:
        value[0] += shift
    return value + [float(selected)]


def fixtures():
    rows = []
    # Native cell centers and every texel-grid corner cover the entire item slab.
    for x, y, z in itertools.product((2.75, 3., 3.25),
                                     (11.75, 12., 12.25), (3.4375, 3.46875)):
        rows.append({'name': 'item_slab', 'position': [x, y - 8.5, z],
                     'color': packet(), 'projection': 'editor'})
    for virtual_y in (-.5, 0., 3., 7.5, 8.499, 8.5, 16.5, 16.501):
        rows.append({'name': 'band_boundary', 'position': [3., virtual_y - 8.5, 3.],
                     'color': packet(), 'projection': 'editor'})
    for height, offset in ((8, 0), (7, 8), (16, 17), (8, 256)):
        rows.append({'name': 'wrong_layout', 'position': [3., 3.5, 3.],
                     'color': packet(height, offset), 'projection': 'editor'})
    for tag in (208.25, 209., 209.125, 223.25):
        rows.append({'name': 'wrong_tag', 'position': [3., 3.5, 3.],
                     'color': packet(tag=tag), 'projection': 'editor'})
    rows.append({'name': 'untagged_world', 'position': [3., 3.5, 3.],
                 'color': packet(), 'projection': 'world'})
    return rows


GPU = r'''cases => {
 const results=[];
 for(const c of cases){
  const gl=document.createElement('canvas').getContext(c.version===300?'webgl2':'webgl');
  if(!gl)throw Error('No GLES '+c.version);
  const p=gl.createProgram();
  for(const [type,source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,c.f]]){
   const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(c.name+' compile: '+gl.getShaderInfoLog(s));
   gl.attachShader(p,s);
  }
  if(c.version===300)gl.transformFeedbackVaryings(p,['diagCoordinates','diagClip'],gl.INTERLEAVED_ATTRIBS);
  gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(c.name+' link: '+gl.getProgramInfoLog(p));
  gl.useProgram(p);
  if(c.version===100){results.push({name:c.name,compiled:true,checks:0});continue;}
  const matrix=(rows)=>[0,1,2,3].flatMap(col=>[0,1,2,3].map(row=>rows[row][col]));
  const yaw=35*Math.PI/180,pitch=25*Math.PI/180;
  const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const view=matrix([[cy,0,-sy,0],[-sy*sp,cp,-cy*sp,0],[sy*cp,sp,cy*cp,0],[0,0,0,1]]);
  const checks=[];
  for(const f of c.fixtures){
   const projection=matrix([[1,0,0,0],[0,1,0,0],[0,0,-.002,0],[0,0,0,f.projection==='editor'?1:0]]);
   for(const [name,value] of [['WORLDVIEW',view],['WORLDVIEWPROJ',view],['PROJ',projection]]){
    const u=gl.getUniformLocation(p,name);if(u!==null)gl.uniformMatrix4fv(u,false,value);
   }
   for(const [name,value] of [['CURRENT_COLOR',f.color],['EXTRA_ACTOR_UNIFORM4',[0,0,0,1]],
                            ['EXTRA_ACTOR_UNIFORM1',[0,0,0,0]],['TILE_LIGHT_COLOR',[1,1,1,1]]]){
    const u=gl.getUniformLocation(p,name);if(u!==null)gl.uniform4fv(u,value);
   }
   const scalar=gl.getUniformLocation(p,'COMMON_BLOCK_GEO_FLOAT1_1');if(scalar!==null)gl.uniform1f(scalar,0);
   const a=gl.getAttribLocation(p,'POSITION');gl.disableVertexAttribArray(a);gl.vertexAttrib4fv(a,[...f.position,1]);
   for(const [name,value] of [['COLOR',[1,1,1,1]],['TEXCOORD_0',[0,0,0,1]],['TEXCOORD_1',[0,0,0,1]]]){
    const n=gl.getAttribLocation(p,name);if(n>=0){gl.disableVertexAttribArray(n);gl.vertexAttrib4fv(n,value);}
   }
   const buffer=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,buffer);
   gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,32,gl.STREAM_READ);gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,buffer);
   gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,1);
   gl.endTransformFeedback();gl.disable(gl.RASTERIZER_DISCARD);
   const output=new Float32Array(8);gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,output);
   const error=gl.getError();if(error!==gl.NO_ERROR)throw Error(c.name+' GL '+error);
   checks.push({name:f.name,coordinates:[...output.slice(0,4)],clip:[...output.slice(4)]});gl.deleteBuffer(buffer);
  }
  results.push({name:c.name,compiled:true,checks});gl.getExtension('WEBGL_lose_context').loseContext();
 }
 return results;
}'''


def verify(bundle, headers, browser):
    plan = check_bundle(bundle)
    samples = fixtures()
    fragment = bundle / 'sources/resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
    cases = []
    for version, flags, shift in itertools.product((100, 300), ((), ('BLEND', 'ALPHA_TEST')), (0, 2)):
        path = bundle / ('nooffset.vertex' if shift == 0 else 'translated.vertex')
        vertex = shader_source(path, headers, version, flags)
        if version == 300:
            vertex = vertex.replace('void main()', 'out highp vec4 diagCoordinates;\nout highp vec4 diagClip;\nvoid main()', 1)
            vertex = vertex.replace('    POS4 worldPos;',
                                    '    diagCoordinates=vec4(logicalPosition.xyz,diagnosticFrameItem?1.0:0.0);\n    diagClip=vec4(0.0);\n    POS4 worldPos;', 1)
            vertex = vertex.replace('    gl_Position = pos;', '    gl_Position = pos;\n    diagClip=pos;', 1)
        cases.append({'name': '%d/%s/shift%d' % (version, ','.join(flags), shift),
                      'version': version, 'shift': shift, 'v': vertex,
                      'f': shader_source(fragment, headers, version, flags), 'fixtures': samples})
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        process = playwright.chromium.launch(executable_path=browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = process.new_page().evaluate(GPU, cases)
        finally:
            process.close()
    failures = []
    coordinates_checked = clip_pairs_checked = 0
    for case, result in zip(cases, results):
        if case['version'] != 300:
            continue
        for fixture, observed in zip(samples, result['checks']):
            wanted = oracle(fixture['position'], fixture['color'], fixture['projection'], case['shift'])
            if any(abs(a - b) > .00002 for a, b in zip(wanted, observed['coordinates'])):
                failures.append({'program': case['name'], 'fixture': fixture, 'expected': wanted, 'actual': observed})
            coordinates_checked += 1
    for flags in ((), ('BLEND', 'ALPHA_TEST')):
        pair = [next(row for row in results if row['name'] == '300/%s/shift%d' % (','.join(flags), shift))
                for shift in (0, 2)]
        for fixture, zero, moved in zip(samples, pair[0]['checks'], pair[1]['checks']):
            selected = oracle(fixture['position'], fixture['color'], fixture['projection'], 0)[3]
            dx = 2. * selected
            yaw, pitch = math.radians(35), math.radians(25)
            dz = dx * math.sin(yaw) * math.cos(pitch)
            expected = [dx * math.cos(yaw), -dx * math.sin(yaw) * math.sin(pitch),
                        dz * -.002 * .04 / 1.7 if fixture['projection'] == 'editor' else dz, 0.]
            actual = [b - a for a, b in zip(zero['clip'], moved['clip'])]
            if any(abs(a - b) > .00002 for a, b in zip(expected, actual)):
                failures.append({'fixture': fixture, 'expected_clip_delta': expected, 'actual_clip_delta': actual})
            clip_pairs_checked += 1
    return {'schema': 1, 'scope': 'Offline actual generated GLSL and layout packet contract',
            'plan_sha256': sha256((bundle / 'plan.json').read_bytes()),
            'production_rendering_accepted': False, 'sdk_dispatch_attempted': False,
            'programs': len(results), 'fixtures': len(samples),
            'coordinate_checks': coordinates_checked, 'clip_pair_checks': clip_pairs_checked,
            'passed': not failures, 'failures': failures,
            'source_root': plan['source_root'], 'headers': str(headers.resolve()),
            'limits': 'Software GPU coordinates do not prove native triangle generation, material routing or drawing'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Preserve existing verification report')
    result = verify(args.bundle.resolve(), args.headers, args.browser)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: result[key] for key in ('programs', 'coordinate_checks', 'clip_pair_checks', 'passed')}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

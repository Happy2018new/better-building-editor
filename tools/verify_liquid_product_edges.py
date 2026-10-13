"""Check shared water edges with actual meshes and installed skinning headers.

The native matrix buffers are explicit host fixtures, not game observations.
Top and side artwork need not agree; positions and each face's UV must agree
with independent physical corners and the declared side mapping.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from verify_biome_shader import shader_source
from verify_liquid_product_triangles import face_vertices, header_fingerprints, selected_mesh, uniforms

ROOT = Path(__file__).resolve().parents[1]
SIZE = 96
FRAGMENT = '#version 300 es\nprecision highp float;out vec4 result;void main(){result=vec4(1.);}'
RUN = r'''cases => {
 const results=[];
 for(const item of cases){
  const canvas=document.createElement('canvas');canvas.width=item.size;canvas.height=item.size;
  const gl=canvas.getContext('webgl2',{antialias:false,premultipliedAlpha:false});
  if(!gl){results.push({name:item.name,error:'WebGL2 unavailable',passed:false});continue;}
  try{
   const compile=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
   const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,item.vertex));
   gl.attachShader(p,compile(gl.FRAGMENT_SHADER,item.fragment));
   gl.transformFeedbackVaryings(p,['edgePosition','liquidUv'],gl.INTERLEAVED_ATTRIBS);gl.linkProgram(p);
   if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
   const location=name=>gl.getUniformLocation(p,name);
   gl.uniformMatrix4fv(location('PROJ'),false,new Float32Array(16));
   gl.uniformMatrix3x4fv(location('BONES_70[0]'),false,item.bone);
   gl.uniformMatrix4x3fv(location('INSTANCE_WORLDMAT_50[0]'),false,item.instance);
   const boneId=gl.getAttribLocation(p,'BONEID_0');if(boneId>=0)gl.vertexAttrib1f(boneId,0);
   gl.disable(gl.DEPTH_TEST);gl.disable(gl.DITHER);gl.viewport(0,0,item.size,item.size);
   gl.frontFace(gl.CW);gl.enable(gl.CULL_FACE);gl.cullFace(item.invert_culling?gl.FRONT:gl.BACK);
   gl.depthMask(!item.disable_depth_write);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
   const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);
   const position=gl.getAttribLocation(p,'POSITION');gl.enableVertexAttribArray(position);
   gl.vertexAttribPointer(position,3,gl.FLOAT,false,0,0);
   const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);
   const tf=gl.createTransformFeedback();gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,tf);
   const feedback=gl.createBuffer();gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,feedback);
   gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,8*6*4,gl.DYNAMIC_READ);
   gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,feedback);
   const failures=[];let checks=0,seamChecks=0,maxEdgeError=0;
   for(const row of item.fixtures){
    gl.bindBuffer(gl.ARRAY_BUFFER,vb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(row.vertices.flat()),gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(row.indices.flat()),gl.STATIC_DRAW);
    gl.uniformMatrix4fv(location('WORLDVIEWPROJ'),false,row.matrix);
    for(let n=1;n<=4;n++)gl.uniform4fv(location('EXTRA_VECTOR'+n),row.uniforms[n-1]);
    gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);gl.drawArrays(gl.POINTS,0,8);
    gl.endTransformFeedback();gl.disable(gl.RASTERIZER_DISCARD);
    gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,feedback);const values=new Float32Array(48);
    gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,values);
    for(let n=0;n<48;n++){checks++;const error=Math.abs(values[n]-row.expected[n]);
     if(error>2e-6)failures.push({fixture:row.name,component:n,actual:values[n],expected:row.expected[n]});}
    for(const [a,b] of row.shared){for(let axis=0;axis<4;axis++){
     const error=Math.abs(values[a*6+axis]-values[b*6+axis]);maxEdgeError=Math.max(maxEdgeError,error);
     checks++;if(error>2e-6)failures.push({fixture:row.name,shared:[a,b],axis,error});}}
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawElements(gl.TRIANGLES,row.indices.flat().length,gl.UNSIGNED_SHORT,0);
    const pixels=new Uint8Array(item.size*item.size*4);gl.readPixels(0,0,item.size,item.size,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    for(const [x,y] of row.seam_pixels){checks++;seamChecks++;if(pixels[(y*item.size+x)*4+3]!==255)
     failures.push({fixture:row.name,seam_pixel:[x,y],alpha:pixels[(y*item.size+x)*4+3]});}
   }
   results.push({name:item.name,passed:failures.length===0,checks,seam_checks:seamChecks,
    maximum_shared_clip_error:maxEdgeError,failure_count:failures.length,failures:failures.slice(0,12)});
  }catch(error){results.push({name:item.name,passed:false,error:String(error)});}
  finally{gl.getExtension('WEBGL_lose_context').loseContext();}
 }
 return results;
}'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chain(ui, bone, instance):
    if ui:
        return np.array(((-1, 0, 0, 0), (0, 0, -1, 1.5), (0, -1, 0, 0), (0, 0, 0, 1.)))
    return instance @ bone @ np.diag((1., 1., -1., 1.))


def shared_corners(face):
    return {1: ((0, 7), (1, 6)), 2: ((2, 7), (3, 6)),
            3: ((3, 7), (0, 6)), 4: ((1, 7), (2, 6))}[face]


def seam_pixels(first, second):
    a = (np.asarray(first[:2]) / first[3] * .5 + .5) * SIZE
    b = (np.asarray(second[:2]) / second[3] * .5 + .5) * SIZE
    delta = b - a
    length2 = float(delta @ delta)
    result = []
    for y in range(SIZE):
        for x in range(SIZE):
            relative = np.array((x + .5, y + .5)) - a
            t = float(relative @ delta / length2)
            if .08 < t < .92 and np.linalg.norm(relative - t * delta) <= .5:
                result.append((x, y))
    if len(result) < 8:
        raise ValueError('Shared-edge fixture has insufficient independent seam pixels')
    return result


def fixture(mesh, slot, face, heights, ui, bone, instance):
    top, top_indices = selected_mesh(mesh, slot, 0)
    side, side_indices = selected_mesh(mesh, slot, face)
    cell = (slot % 4, (slot + 1) % 4, (slot + 2) % 4)
    normalized = tuple(value / 255. for value in heights)
    top_points, top_uv = face_vertices(0, normalized)
    side_points, side_uv = face_vertices(face, normalized)
    normal = {1: (0, 0, -1), 2: (0, 0, 1), 3: (-1, 0, 0), 4: (1, 0, 0)}[face]
    # Keep both top triangles front-facing even at the maximum saved slope.
    toward = np.array(normal) * .6 + np.array((0, .8, 0))
    up = np.array(normal) * -.8 + np.array((0, .6, 0))
    right = np.cross(up, toward)
    physical = np.eye(4)
    physical[:3, :3] = np.array((right * 1.2, up * 1.2, toward * .4))
    physical[:3, 3] = -physical[:3, :3] @ (np.array(cell) - 1.5)
    coordinates = chain(ui, bone, instance)
    matrix = physical @ np.linalg.inv(coordinates)
    expected = []
    projected = []
    for point, uv in zip(top_points + side_points, top_uv + side_uv):
        local = np.array(tuple(cell[i] + point[i] - 2. for i in range(3)) + (1.,))
        clip = physical @ local
        projected.append(clip.tolist())
        expected.extend(clip.tolist() + list(uv))
    corners = shared_corners(face)
    visible_areas = []
    indices = top_indices + [tuple(index + 4 for index in row) for row in side_indices]
    for triangle in indices:
        first, second, third = (np.array(projected[index][:2]) for index in triangle)
        ab, ac = second - first, third - first
        visible_areas.append(float(ab[0] * ac[1] - ab[1] * ac[0]))
    if min(visible_areas[:len(top_indices)]) <= 0 or min(visible_areas) < 0:
        raise ValueError('Shared-edge fixture has a legitimately hidden triangle')
    return {'name': 'slot%s/face%s/%s' % (slot, face, heights), 'vertices': top + side,
            'indices': indices, 'visible_triangle_areas': visible_areas,
            'matrix': matrix.T.flatten().tolist(),
            'uniforms': uniforms(slot, cell, 0, heights), 'expected': expected,
            'shared': corners, 'seam_pixels': seam_pixels(projected[corners[0][0]], projected[corners[1][0]])}


def instrument(source):
    if source.count('void main() {') != 1 or source.count('gl_PointSize=1.0;') != 1:
        raise ValueError('Review instrumentation after vertex layout changes')
    return source.replace('void main() {', 'out highp vec4 edgePosition;\nvoid main() {').replace(
        'gl_PointSize=1.0;', 'edgePosition=gl_Position;\ngl_PointSize=1.0;')


def cases(root, headers):
    contract_path = root / 'tools/data/liquid_product_resource_contract_v1.json'
    contract = json.loads(contract_path.read_bytes())
    inputs = {contract_path.relative_to(root).as_posix(): sha(contract_path)}
    for helper in ('verify_liquid_product_triangles.py', 'verify_biome_shader.py'):
        relative = 'tools/' + helper
        inputs[relative] = sha(root / relative)
    includes, result = {}, []
    heights = ((189, 189, 189, 189), (47, 47, 47, 47), (17, 61, 199, 239), (255, 0, 127, 64))
    bone = np.array(((1.2, 0, 0, .1), (0, .8, 0, -.2), (0, 0, 1.5, .3), (0, 0, 0, 1.)))
    instance = np.array(((0, 0, 1, .4), (0, 1, 0, .2), (-1, 0, 0, -.3), (0, 0, 0, 1.)))
    for name, option in contract['model_options'].items():
        if option['top_only'] or option['frozen']:
            continue
        material = contract['materials'][name + ':entity_for_skeleton_alpha']
        if (material['+states'] != ['Blending', 'DisableDepthWrite', 'InvertCulling']
                or material['blendSrc'] != 'SourceAlpha' or material['blendDst'] != 'OneMinusSrcAlpha'):
            raise ValueError('Actual material states changed; review host convention fixtures')
        mesh_path = root / 'resource_pack/models' / contract['models'][name]['mesh']
        vertex_path = root / 'resource_pack/shaders/glsl' / option['vertex_shader']
        inputs.update({p.relative_to(root).as_posix(): sha(p) for p in (mesh_path, vertex_path)})
        header_fingerprints(vertex_path.read_text('ascii'), headers, includes)
        mesh = json.loads(mesh_path.read_bytes())['mesh'][0]
        ui = option['preview_depth']
        flags = ('USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE')
        source = instrument(shader_source(vertex_path, headers, 300, flags))
        rows = []
        for slot in range(4):
            for face in range(1, 5):
                for height in heights:
                    row = fixture(mesh, slot, face, height, ui, bone, instance)
                    row['uniforms'][0][slot] += (1 << face) * 64
                    rows.append(row)
        result.append({'name': name, 'vertex': source, 'fragment': FRAGMENT, 'size': SIZE,
                       'bone': bone[:3].flatten().tolist(), 'instance': instance[:3].T.flatten().tolist(),
                       'invert_culling': True, 'disable_depth_write': True, 'fixtures': rows})
    return result, inputs, includes


def sensitivity(original):
    controls = []
    for fault, source, replacement in (
            ('top_south_lower_one_byte', 'liquidUv=vec2(u,v);',
             'if(v>0.5) point.y-=1.0/255.0;\nliquidUv=vec2(u,v);'),
            ('south_u_flip', 'liquidUv=vec2(u,1.0-height);',
             'liquidUv=vec2(face>1.5 && face<2.5?1.0-u:u,1.0-height);')):
        altered = dict(original, name='sensitivity/' + fault)
        altered['vertex'] = original['vertex'].replace(source, replacement, 1)
        altered['fixtures'] = [row for row in original['fixtures'] if '/face2/' in row['name']]
        controls.append(altered)
    return controls


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh evidence output')
    items, inputs, includes = cases(args.root, args.headers)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page()
            results = page.evaluate(RUN, items)
            faults = page.evaluate(RUN, sensitivity(items[0]))
        finally:
            browser.close()
    changed = [name for name, value in inputs.items() if sha(args.root / name) != value]
    changed += [name for name, value in includes.items() if sha(args.headers / name) != value]
    sensitive = all(row.get('failure_count', 0) > 0 and not row.get('error') for row in faults)
    report = {'schema': 1, 'passed': not changed and sensitive and all(row['passed'] for row in results),
              'checks': sum(row.get('checks', 0) for row in results), 'results': results,
              'sensitivity_passed': sensitive, 'sensitivity': faults, 'inputs_sha256': inputs,
              'headers_sha256': includes, 'changed_inputs': changed, 'verifier_sha256': sha(Path(__file__)),
              'scope': 'Host GLES3 actual indexed shared edges, positions, UVs and installed bone/instance helpers',
              'matrix_scope': 'Explicit affine host bone/instance fixtures; no observed game matrices',
              'culling_scope': 'Host CW convention with actual InvertCulling material; native convention not qualified',
              'fixture_scope': 'Both top triangles face the camera; zero-height side triangles may be degenerate',
              'seam_scope': 'Pixel centers within half a pixel of the independently projected shared edge',
              'game_acceptance_claimed': False, 'native_parity_claimed': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'], 'results': results,
                      'sensitivity_passed': sensitive}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

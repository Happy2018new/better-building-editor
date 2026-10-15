"""Rasterize actual product-water triangles against an independent face oracle.

This checks host GLES and never qualifies native game rendering. The oracle
uses physical cube corners and barycentric interpolation, not generator mesh
helpers or arbitrary interior calls to the vertex shader.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import re

from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
SIZE = 64
FACE_NORMALS = ((0, 1, 0), (0, 0, -1), (0, 0, 1),
                (-1, 0, 0), (1, 0, 0), (0, -1, 0))
TRIANGLES = ((0, 2, 1), (0, 3, 2))

RENDER = r'''async cases => {
 const results=[];
 for (const item of cases) {
  const canvas=document.createElement('canvas');canvas.width=item.size;canvas.height=item.size;
  const gl=canvas.getContext(item.version===100?'webgl':'webgl2',{antialias:false,premultipliedAlpha:false});
  if(!gl){results.push({name:item.name,passed:false,error:'GL unavailable'});continue;}
  try {
   const compile=(kind,source)=>{const shader=gl.createShader(kind);gl.shaderSource(shader,source);gl.compileShader(shader);
    if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));return shader;};
   const program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,item.vertex));
   gl.attachShader(program,compile(gl.FRAGMENT_SHADER,item.fragment));gl.linkProgram(program);
   if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
   gl.useProgram(program);gl.viewport(0,0,item.size,item.size);
   gl.enable(gl.CULL_FACE);gl.cullFace(gl.BACK);gl.frontFace(gl.CCW);
   gl.disable(gl.DEPTH_TEST);gl.disable(gl.DITHER);
   gl.uniform4fv(gl.getUniformLocation(program,'CURRENT_COLOR'),[1,1,1,1]);
   gl.uniform4fv(gl.getUniformLocation(program,'HIDE_COLOR_FRAGMENT'),[1,1,1,1]);
   gl.uniformMatrix4fv(gl.getUniformLocation(program,'PROJ'),false,new Float32Array(16));
   if(item.rgba){const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,item.texture_size[0],item.texture_size[1],0,gl.RGBA,gl.UNSIGNED_BYTE,
     Uint8Array.from(atob(item.rgba),c=>c.charCodeAt(0)));gl.uniform1i(gl.getUniformLocation(program,'TEXTURE_0'),0);
    gl.uniform1f(gl.getUniformLocation(program,'TOTAL_REAL_WORLD_TIME'),0);
    gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
   }else gl.disable(gl.BLEND);
   const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
   gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(item.vertices.flat()),gl.STATIC_DRAW);
   const location=gl.getAttribLocation(program,'POSITION');gl.enableVertexAttribArray(location);
   gl.vertexAttribPointer(location,3,gl.FLOAT,false,0,0);
   const index=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,index);
   gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(item.indices.flat()),gl.STATIC_DRAW);
   const failures=[];let checks=0;
   for(const fixture of item.fixtures){
    gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,fixture.matrix);
    for(let n=1;n<=4;n++)gl.uniform4fv(gl.getUniformLocation(program,'EXTRA_VECTOR'+n),fixture.uniforms[n-1]);
    gl.clearColor(...fixture.background);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawElements(gl.TRIANGLES,item.indices.flat().length,gl.UNSIGNED_SHORT,0);
    const pixels=new Uint8Array(item.size*item.size*4);gl.readPixels(0,0,item.size,item.size,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    for(const sample of fixture.samples){checks++;const offset=(sample.y*item.size+sample.x)*4;
     const actual=[...pixels.slice(offset,offset+4)];
     if(actual.some((value,n)=>Math.abs(value-sample.expected[n])>2))failures.push({fixture:fixture.name,
      x:sample.x,y:sample.y,actual,expected:sample.expected,covered:sample.covered});
    }
   }
   results.push({name:item.name,passed:failures.length===0,checks,failures:failures.slice(0,24),failure_count:failures.length});
  }catch(error){results.push({name:item.name,passed:false,error:String(error)});}
  finally{gl.getExtension('WEBGL_lose_context').loseContext();}
 }
 return results;
}'''


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def face_vertices(face, heights):
    """Physical positions and UVs in the four encoded input-corner roles."""
    nw, ne, se, sw = heights
    if face == 0:
        points = ((0, nw, 0), (1, ne, 0), (1, se, 1), (0, sw, 1))
        uv = ((0, 0), (1, 0), (1, 1), (0, 1))
    elif face == 5:
        points = ((1, 0, 0), (0, 0, 0), (0, 0, 1), (1, 0, 1))
        uv = ((0, 0), (1, 0), (1, 1), (0, 1))
    else:
        endpoints = {
            1: ((0, 0), (1, 0), nw, ne),
            2: ((1, 1), (0, 1), se, sw),
            3: ((0, 1), (0, 0), sw, nw),
            4: ((1, 0), (1, 1), ne, se),
        }
        left, right, left_height, right_height = endpoints[face]
        points = ((left[0], 0, left[1]), (right[0], 0, right[1]),
                  (right[0], right_height, right[1]), (left[0], left_height, left[1]))
        uv = ((0, 1), (1, 1), (1, 1 - right_height), (0, 1 - left_height))
    return points, uv


def face_axes(face):
    normal = FACE_NORMALS[face]
    if face == 0:
        return (1, 0, 0), (0, 0, -1), normal
    if face == 5:
        return (-1, 0, 0), (0, 0, -1), normal
    up = (0, 1, 0)
    return cross(up, normal), up, normal


def camera_matrix(face, cell, ui):
    """Map a physical unit cube to the central 80% of an orthographic image."""
    right, up, toward = face_axes(face)
    center = tuple(axis - 1.5 for axis in cell)
    rows = []
    for basis, scale in ((right, 1.6), (up, 1.6), (toward, .6)):
        physical = tuple(scale * axis for axis in basis)
        translation = -dot(physical, center)
        if ui:
            # Inverse of UI entity axes: physical=(-entity.x,-entity.z,1.5-entity.y).
            rows.append((-physical[0], -physical[2], -physical[1],
                         translation + 1.5 * physical[2]))
        else:
            rows.append(physical + (translation,))
    rows.append((0, 0, 0, 1))
    return [rows[row][column] for column in range(4) for row in range(4)]


def project_vertices(face, heights):
    points, uv = face_vertices(face, heights)
    right, up, toward = face_axes(face)
    vertices = []
    for point, texcoord in zip(points, uv):
        centered = subtract(point, (.5, .5, .5))
        vertices.append((.5 + .8 * dot(right, centered),
                         .5 + .8 * dot(up, centered),
                         .5 + .3 * dot(toward, centered), texcoord))
    return vertices


def barycentric(point, triangle):
    a, b, c = triangle
    denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(denominator) < 1.e-12:
        return None
    first = ((b[1] - c[1]) * (point[0] - c[0]) +
             (c[0] - b[0]) * (point[1] - c[1])) / denominator
    second = ((c[1] - a[1]) * (point[0] - c[0]) +
              (a[0] - c[0]) * (point[1] - c[1])) / denominator
    weights = first, second, 1 - first - second
    return weights if min(weights) >= -1.e-9 else None


def sample_triangle(vertices, point):
    for indices in TRIANGLES:
        triangle = tuple(vertices[index] for index in indices)
        weights = barycentric(point, triangle)
        if weights is not None:
            depth = sum(weight * vertex[2] for weight, vertex in zip(weights, triangle))
            uv = tuple(sum(weight * vertex[3][axis] for weight, vertex in zip(weights, triangle))
                       for axis in (0, 1))
            return depth, uv
    return None


def marker_pixel(x, y):
    return x * 7 % 256, y * 5 % 256, (x * 3 + y * 2) % 256, 240


def marker_bytes(width, frames):
    return bytes(channel for y in range(width * frames) for x in range(width)
                 for channel in marker_pixel(x, y % width))


def ideal_top_uv(uv, code):
    # Independent Java-style template as a centered square with half-unit span.
    angle = code * math.tau / 256
    x, z = uv[0] - .5, uv[1] - .5
    return (.5 + .5 * (math.cos(angle) * x + math.sin(angle) * z),
            .5 + .5 * (-math.sin(angle) * x + math.cos(angle) * z))


def expected_pixel(sample, mode, width, top, flowing, rotation, background, visible=True):
    if sample is None or not visible:
        return tuple(round(value * 255) for value in background)
    depth, uv = sample
    if top:
        uv = ideal_top_uv(uv, rotation)
    if mode == 'geometry':
        return tuple(round(value * 255) for value in uv + (depth, 1))
    if top:
        px, py = (int(value * width) for value in uv)
    else:
        span = width // 2 if flowing else width
        px, py = (int(value * (span - 1) + .5) for value in uv)
    texel = marker_pixel(px, py)
    alpha = .45
    rgb = tuple(round(texel[axis] * alpha + background[axis] * 255 * (1 - alpha))
                for axis in range(3))
    return rgb + (round(255 * (alpha * alpha + background[3] * (1 - alpha))),)


def uniforms(slot, cell, face, heights, rotation=0, visible=True):
    codes, pairs = [0.] * 4, [0.] * 8
    address = cell[0] + 4 * cell[2] + 16 * cell[1]
    codes[slot] = float(address + ((1 << face) * 64 if visible else 0) + rotation * 4096)
    pairs[slot * 2] = float(heights[0] + heights[1] * 256)
    pairs[slot * 2 + 1] = float(heights[2] + heights[3] * 256)
    return [codes, pairs[:4], pairs[4:], [39686., -1., float(0xFFFFFF), 1.]]


def geometry_fragment(version):
    prefix = '#version 300 es\n' if version == 300 else '#version 100\n'
    varying = 'in' if version == 300 else 'varying'
    output = 'out vec4 result;\n' if version == 300 else ''
    target = 'result' if version == 300 else 'gl_FragColor'
    return prefix + 'precision highp float;\n' + output + ''.join(
        '%s highp %s %s;\n' % (varying, kind, name)
        for kind, name in (('vec2', 'liquidUv'), ('float', 'liquidVisible'), ('float', 'liquidClip'))) + (
            'void main(){if(liquidVisible<.5||liquidClip>0.)discard;'
            '%s=vec4(liquidUv,gl_FragCoord.z,1.);}\n' % target)


def selected_mesh(mesh, slot, face):
    indices = [i for i, vertex in enumerate(mesh['vertices'])
               if int(vertex['pos'][0] // 2) == slot and int(vertex['pos'][1] // 2) == face]
    if len(indices) != 4:
        raise ValueError('Actual water mesh must retain four vertices per slot and face')
    mapping = {value: index for index, value in enumerate(indices)}
    triangles = [tuple(mapping[index] for index in triangle) for triangle in mesh['indices']
                 if set(triangle).issubset(mapping)]
    if tuple(triangles) != TRIANGLES:
        raise ValueError('Actual water mesh triangulation changed; review the independent oracle')
    expected = ((0, 0), (1, 0), (1, 1), (0, 1))
    vertices = [mesh['vertices'][index] for index in indices]
    for vertex, (u, v) in zip(vertices, expected):
        if vertex['pos'] != [slot * 2. + u, face * 2. + v, 0.] or tuple(vertex['normal']) != FACE_NORMALS[face]:
            raise ValueError('Actual water mesh input roles or outward normals changed')
    return [vertex['pos'] for vertex in vertices], triangles


def fixture(face, heights, slot, ui, mode, width, top, flowing, rotation=0, visible=True):
    cell = ((slot * 3) % 4, (slot + 1) % 4, (slot * 2 + 1) % 4)
    vertices = project_vertices(face, tuple(value / 255 for value in heights))
    background = (0., 0., 0., 0.) if mode == 'geometry' else (.125, .375, .75, 1.)
    samples = []
    for x, y in ((8, 8), (8, 55), (55, 8), (55, 55), (19, 13), (27, 17),
                 (43, 23), (14, 37), (21, 45), (38, 49), (51, 35), (33, 30)):
        sample = sample_triangle(vertices, ((x + .5) / SIZE, (y + .5) / SIZE))
        # Avoid edges, where an independent oracle must not guess raster fill conventions.
        samples.append({'x': x, 'y': y, 'covered': sample is not None,
                        'expected': expected_pixel(sample, mode, width, top, flowing,
                                                   rotation, background, visible)})
    return {'name': '%s/slot%s/%s/r%s/%s' % (face, slot, heights, rotation, visible),
            'matrix': camera_matrix(face, cell, ui), 'background': background,
            'uniforms': uniforms(slot, cell, face, heights, rotation, visible), 'samples': samples}


def make_cases(root, headers):
    path = root / 'tools/data/liquid_product_resource_contract_v1.json'
    contract = json.loads(path.read_bytes())
    if contract.get('schema_version') != 1 or contract.get('native_parity_claimed') is not False:
        raise ValueError('Unknown product-water resource contract')
    cases, inputs, includes = [], {path.relative_to(root).as_posix(): digest(path)}, {}
    heights_set = ((255, 255, 255, 255), (64, 64, 64, 64), (55, 129, 218, 177))
    for name, option in contract['model_options'].items():
        mesh_path = root / 'resource_pack/models' / contract['models'][name]['mesh']
        mesh = json.loads(mesh_path.read_bytes())['mesh'][0]
        inputs[mesh_path.relative_to(root).as_posix()] = digest(mesh_path)
        vertex_path = root / 'resource_pack/shaders/glsl' / option['vertex_shader']
        fragment_path = root / 'resource_pack/shaders/glsl' / option['fragment_shader']
        for source in (vertex_path, fragment_path):
            inputs[source.relative_to(root).as_posix()] = digest(source)
            header_fingerprints(source.read_text(encoding='ascii'), headers, includes)
        top, flowing = option['top_only'], option['texture'].startswith('flowing_')
        width, height = contract['textures'][option['texture']]['size']
        faces = (0,) if top else range(6)
        for version in (100, 300):
            vertex = shader_source(vertex_path, headers, version, ())
            for mode in ('geometry', 'marker'):
                fragment = (geometry_fragment(version) if mode == 'geometry'
                            else shader_source(fragment_path, headers, version, ()))
                for face in faces:
                    for slot in range(4):
                        vertices, indices = selected_mesh(mesh, slot, face)
                        fixtures = [fixture(face, heights, slot, option['preview_depth'], mode,
                                            width, top, flowing, rotation)
                                    for heights in heights_set
                                    for rotation in ((0, 37, 128, 223) if top else (0,))]
                        fixtures.append(fixture(face, heights_set[0], slot, option['preview_depth'],
                                                mode, width, top, flowing, visible=False))
                        case = {'name': '%s/%s/%s/face%s/slot%s' % (name, version, mode, face, slot),
                                'version': version, 'size': SIZE, 'vertex': vertex,
                                'fragment': fragment, 'vertices': vertices, 'indices': indices,
                                'fixtures': fixtures}
                        if mode == 'marker':
                            case.update(texture_size=(width, height),
                                        rgba=base64.b64encode(marker_bytes(width, height // width)).decode('ascii'))
                        cases.append(case)
    return cases, inputs, includes


def header_fingerprints(source, headers, checked):
    for name in re.findall(r'^\s*#include\s+"([^"]+)"', source, flags=re.M):
        if name in checked:
            continue
        path = headers / name
        payload = path.read_bytes()
        checked[name] = hashlib.sha256(payload).hexdigest()
        header_fingerprints(payload.decode('utf8'), headers, checked)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sensitivity_cases(cases):
    """Require the raster oracle to detect concrete plausible implementation faults."""
    original = next(case for case in cases if '/100/marker/face1/slot0' in case['name']
                    and '_frozen' not in case['name'])
    fixtures = [row for row in original['fixtures'] if '/(255, 255, 255, 255)/' not in row['name']]
    controls = []
    for fault in ('reverse_winding', 'stretch_low_side', 'flip_side_u'):
        candidate = dict(original, name='sensitivity/' + fault, fixtures=fixtures)
        if fault == 'reverse_winding':
            candidate['indices'] = [tuple(reversed(triangle)) for triangle in original['indices']]
        else:
            source = 'liquidUv=vec2(u,1.0-height);'
            replacement = ('liquidUv=vec2(u,1.0-v);' if fault == 'stretch_low_side'
                           else 'liquidUv=vec2(1.0-u,1.0-height);')
            if original['vertex'].count(source) != 1:
                raise ValueError('Review sensitivity controls after changing side UV shader syntax')
            candidate['vertex'] = original['vertex'].replace(source, replacement)
        controls.append(candidate)
    return controls


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Project containing the installed product resource contract')
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh result path; existing evidence must be preserved')
    cases, inputs, includes = make_cases(args.root, args.headers)
    controls = sensitivity_cases(cases)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
            sensitivity = browser.new_page().evaluate(RENDER, controls)
        finally:
            browser.close()
    changed = [name for name, fingerprint in inputs.items() if digest(args.root / name) != fingerprint]
    changed_headers = [name for name, fingerprint in includes.items() if digest(args.headers / name) != fingerprint]
    sensitive = all(result.get('failure_count', 0) > 0 and not result.get('error') for result in sensitivity)
    report = {'schema_version': 1, 'passed': not changed and not changed_headers and sensitive and all(result['passed'] for result in results),
              'checks': sum(result.get('checks', 0) for result in results), 'results': results,
              'sensitivity_passed': sensitive, 'sensitivity_controls': sensitivity,
              'inputs_sha256': inputs, 'headers_sha256': includes,
              'inputs_changed_during_check': changed, 'headers_changed_during_check': changed_headers,
              'verifier_sha256': digest(Path(__file__)),
              'shader_expander_sha256': digest(ROOT / 'tools/verify_biome_shader.py'),
              'scope': 'Actual indexed triangles: six outward faces, four payload slots, quantized slopes, UV crops and culling',
              'world_skinning_included': False, 'game_acceptance_claimed': False, 'native_parity_claimed': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': report['passed'], 'checks': report['checks'],
                      'sensitivity_passed': sensitive,
                      'failed': [{'name': result['name'], 'failure_count': result.get('failure_count'),
                                  'error': result.get('error')} for result in results if not result['passed']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

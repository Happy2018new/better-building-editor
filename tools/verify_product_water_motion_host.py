"""Dense actual-shader water motion checks, independent of native acceptance."""
import argparse
import base64
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from analyze_product_water_flow import GRID, PHYSICAL_FLOW, motion, sha
from verify_biome_shader import shader_source
from verify_liquid_product_triangles import camera_matrix, selected_mesh, uniforms

ROOT = Path(__file__).resolve().parents[1]
SIZE = 120
RUN = r'''items=>items.map(item=>{
 const canvas=document.createElement('canvas');canvas.width=canvas.height=item.size;
 const gl=canvas.getContext('webgl2',{antialias:false,premultipliedAlpha:false});
 if(!gl)throw Error('WebGL2 unavailable');
 try{
  const compile=(kind,source)=>{const s=gl.createShader(kind);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;};
  const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,item.vertex));
  gl.attachShader(p,compile(gl.FRAGMENT_SHADER,item.fragment));gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
  const loc=name=>gl.getUniformLocation(p,name);
  gl.uniformMatrix4fv(loc('WORLDVIEWPROJ'),false,item.matrix);
  gl.uniformMatrix4fv(loc('PROJ'),false,new Float32Array(16));
  gl.uniform4fv(loc('CURRENT_COLOR'),[1,1,1,1]);
  for(let n=1;n<=4;n++)gl.uniform4fv(loc('EXTRA_VECTOR'+n),item.uniforms[n-1]);
  gl.disable(gl.DEPTH_TEST);gl.disable(gl.DITHER);gl.disable(gl.BLEND);
  gl.frontFace(gl.CW);gl.enable(gl.CULL_FACE);gl.cullFace(gl.FRONT);
  const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,item.width,item.height,0,gl.RGBA,gl.UNSIGNED_BYTE,
   Uint8Array.from(atob(item.rgba),c=>c.charCodeAt(0)));
  gl.uniform1i(loc('TEXTURE_0'),0);
  const vb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,vb);
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(item.vertices.flat()),gl.STATIC_DRAW);
  const pos=gl.getAttribLocation(p,'POSITION');gl.enableVertexAttribArray(pos);
  gl.vertexAttribPointer(pos,3,gl.FLOAT,false,0,0);
  const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(item.indices.flat()),gl.STATIC_DRAW);
  gl.viewport(0,0,item.size,item.size);const frames=[];
  for(const time of item.times){gl.uniform1f(loc('TOTAL_REAL_WORLD_TIME'),time);
   gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
   gl.drawElements(gl.TRIANGLES,item.indices.flat().length,gl.UNSIGNED_SHORT,0);
   const pixels=new Uint8Array(item.size*item.size*4);gl.readPixels(0,0,item.size,item.size,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   frames.push([...pixels]);}
  return {name:item.name,frames};
 }finally{gl.getExtension('WEBGL_lose_context').loseContext();}
})'''


def cases(headers):
    from projection.debug_product_water_blueprints import source_document
    from projection.liquid_native_shapes import product_shape_provider
    contract_path = ROOT / 'tools/data/liquid_product_resource_contract_v1.json'
    contract = json.loads(contract_path.read_bytes())
    inputs = {str(contract_path.relative_to(ROOT)): sha(contract_path)}
    image_path = ROOT / 'resource_pack/textures/models/modern_projection/liquid/flowing_water_grey.png'
    with Image.open(image_path) as image:
        image = image.convert('RGBA')
        texture = {'rgba': base64.b64encode(image.tobytes()).decode('ascii'),
                   'width': image.width, 'height': image.height}
    inputs[str(image_path.relative_to(ROOT))] = sha(image_path)
    times = [.025 + index * .05 for index in range(32)]
    rows = []
    for ui in (True, False):
        for identity, vector in PHYSICAL_FLOW.items():
            document = source_document(identity)
            shape = product_shape_provider(document).surface(document, (3, 3, 3), 0,
                                                                document.get_layer((3, 3, 3), 0))
            rows.append((ui, identity, 0, shape.flow_uv[1], vector))
        rows.append((ui, 'falling_side', 2, 0, (0, -1)))
    result = []
    for ui, identity, face, rotation, direction in rows:
        name = 'modern_projection_liquid_product_flowing_water_grey' + ('_top' if face == 0 else '') + ('' if ui else '_world')
        option = contract['model_options'][name]
        paths = [ROOT / 'resource_pack/shaders/glsl' / option[key] for key in ('vertex_shader', 'fragment_shader')]
        mesh_path = ROOT / 'resource_pack/models' / contract['models'][name]['mesh']
        for path in paths + [mesh_path]:
            inputs[str(path.relative_to(ROOT))] = sha(path)
        mesh = json.loads(mesh_path.read_bytes())['mesh'][0]
        vertices, indices = selected_mesh(mesh, 0, face)
        cell = (0, 0, 0)
        result.append(dict(texture, name=identity + ('/ui' if ui else '/world'), size=SIZE,
            vertex=shader_source(paths[0], headers, 300, ()),
            fragment=shader_source(paths[1], headers, 300, ()), times=times,
            uniforms=uniforms(0, cell, face, (255, 255, 255, 255), rotation),
            vertices=vertices, indices=indices, matrix=camera_matrix(face, cell, ui),
            face=face, direction=direction))
    return result, inputs


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh motion evidence')
    items, inputs = cases(args.headers)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            renders = browser.new_page().evaluate(RUN, items)
        finally:
            browser.close()
    u, v = np.meshgrid(np.linspace(.08, .92, GRID), np.linspace(.08, .92, GRID))
    results = []
    for item, rendered in zip(items, renders):
        pixels = np.asarray(rendered['frames']).reshape((-1, SIZE, SIZE, 4))
        x, y = SIZE * (.1 + .8 * u), SIZE * (.1 + .8 * (1 - v if item['face'] == 0 else v))
        signal = np.array([map_coordinates(frame[:, :, :3].mean(axis=2), (y, x), order=1)
                           for frame in pixels])
        direction = item['direction']
        axis, sign = (1 if direction[0] else 0), (direction[0] or direction[1])
        result = motion(signal, np.rint(np.array(item['times']) * 1e7), axis, sign,
                        .84 / (GRID - 1), 16 if item['face'] == 0 else 15)
        reverse = motion(signal[::-1], np.rint(np.array(item['times']) * 1e7), axis, sign,
                         .84 / (GRID - 1), 16 if item['face'] == 0 else 15)
        results.append({'name': item['name'], 'result': result, 'reversed_time_rejected': not reverse['passed']})
    report = {'schema': 1, 'passed': all(row['result']['passed'] and row['reversed_time_rejected'] for row in results),
              'frames': sum(len(row['frames']) for row in renders), 'results': results,
              'inputs_sha256': inputs, 'verifier_sha256': sha(__file__),
              'game_acceptance_claimed': False, 'native_parity_claimed': False,
              'scope': 'Actual indexed top/side shaders and installed water atlas, 20Hz full-cycle temporal motion'}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': report['passed'], 'frames': report['frames'],
                      'results': [(row['name'], row['result']['correct_pair_fraction']) for row in results]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

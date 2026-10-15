"""Check actual compass fragment pixels offline; native qualification is separate."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from verify_biome_shader import shader_source

ROOT = Path(__file__).resolve().parents[1]
RENDER = r'''input => {
 const results=[];
 for(const row of input.shaders) {
  const canvas=document.createElement('canvas');canvas.width=canvas.height=input.width;
  const gl=canvas.getContext(row.version===300?'webgl2':'webgl',{antialias:false});
  if(!gl)throw Error('No GLES context');
  gl.disable(gl.DITHER);
  const program=gl.createProgram();
  const prefix=row.version===300?'#version 300 es\n':'#version 100\n';
  const attr=row.version===300?'in':'attribute',vary=row.version===300?'out':'varying';
  const vertex=prefix+'precision highp float;\n'+attr+' vec2 point;\nuniform float enchanted;\n'+
   vary+' highp vec2 itemUv;\n'+vary+' highp float itemVisible;\n'+vary+' highp float itemEnchanted;\n'+
   vary+' highp float itemClip;\n'+vary+' highp float itemFrame;\n'+vary+' highp vec3 itemLight;\n'+
   vary+' highp vec3 itemTileLight;\nvoid main(){gl_Position=vec4(point,0.,1.);itemUv=point*.5+.5;'+
   'itemVisible=1.;itemEnchanted=enchanted;itemClip=-1.;itemFrame=1.;itemLight=vec3(1.);itemTileLight=vec3(1.);}';
  for(const [type,source] of [[gl.VERTEX_SHADER,vertex],[gl.FRAGMENT_SHADER,row.fragment]]) {
   const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
   if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));
   gl.attachShader(program,shader);
  }
  gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  const uniform=name=>gl.getUniformLocation(program,name);
  gl.uniform4f(uniform('EXTRA_VECTOR4'),39687,1,0,1);gl.uniform4f(uniform('CURRENT_COLOR'),1,1,1,1);
  gl.uniformMatrix4fv(uniform('PROJ'),false,[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
  for(const [index,texture] of input.textures.entries()) {
   gl.activeTexture(gl.TEXTURE0+index);gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
   for(const param of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,param,gl.CLAMP_TO_EDGE);
   for(const param of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])
    gl.texParameteri(gl.TEXTURE_2D,param,index===0?gl.NEAREST:gl.LINEAR);
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,texture.width,texture.height,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(texture.pixels));
   gl.uniform1i(uniform('TEXTURE_'+index),index);
  }
  gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const location=gl.getAttribLocation(program,'point');gl.enableVertexAttribArray(location);
  gl.vertexAttribPointer(location,2,gl.FLOAT,false,0,0);
  for(const clock of input.times)for(const enchanted of [false,true]) {
   gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
   gl.uniform1f(uniform('TOTAL_REAL_WORLD_TIME'),clock);gl.uniform1f(uniform('enchanted'),enchanted?1:0);
   gl.drawArrays(gl.TRIANGLES,0,3);
   const pixels=new Uint8Array(input.width*input.width*4);
   gl.readPixels(0,0,input.width,input.width,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   const error=gl.getError();if(error!==gl.NO_ERROR)throw Error('GL error '+error);
   results.push({version:row.version,clock,enchanted,pixels:Array.from(pixels)});
  }
 }
 return results;
}'''


def texture(path):
    with Image.open(path) as image:
        image = image.convert('RGBA')
        return {'width': image.width, 'height': image.height,
                'pixels': list(image.tobytes())}


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('Preserve previous compass pixel verification')
    catalog_path = ROOT / 'tools/data/item_icon_catalog_nemc_3.10.0.420447.json'
    catalog = json.loads(catalog_path.read_bytes())
    loops = [(key, row) for key, row in catalog['resources'].items() if 'animation' in row]
    if len(loops) != 1:
        raise ValueError('This bounded check requires exactly the compass loop')
    key, resource = loops[0]
    atlas_path = ROOT / ('resource_pack/textures/models/modern_projection/item_icons/' + key + '.png')
    glint_path = ROOT / 'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png'
    fragment = ROOT / 'resource_pack/shaders/glsl/modern_projection_item_compass_loop.fragment'
    atlas, glint = texture(atlas_path), texture(glint_path)
    times = (0., .375, 1., 2., 4.)
    inputs = {'width': atlas['width'], 'times': times, 'textures': [atlas, glint],
              'shaders': [{'version': version,
                           'fragment': shader_source(fragment, args.headers, version, ('BLEND',))}
                          for version in (100, 300)]}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, inputs)
        finally:
            browser.close()
    atlas_pixels = np.array(atlas['pixels'], dtype=np.uint8).reshape(atlas['height'], atlas['width'], 4)
    measurements, frames = [], {}
    for result in results:
        frame = int(result['clock'] % 2. * 16.)
        expected = atlas_pixels[frame * atlas['width']:(frame + 1) * atlas['width']]
        pixels = np.array(result.pop('pixels'), dtype=np.uint8).reshape(expected.shape)
        frames[(result['version'], result['clock'], result['enchanted'])] = pixels
        mask = expected[:, :, 3] != 0
        alpha = np.array_equal(pixels[:, :, 3], expected[:, :, 3])
        outside_clear = bool(np.all(pixels[~mask] == 0))
        base_exact = bool(np.array_equal(pixels[mask], expected[mask]))
        measurements.append(dict(result, frame=frame, alpha_exact=alpha, outside_clear=outside_clear,
                                 source_frame_exact=base_exact if not result['enchanted'] else None,
                                 passed=alpha and outside_clear and (result['enchanted'] or base_exact)))
    versions = []
    for version in (100, 300):
        plain = [frames[(version, clock, False)] for clock in times]
        enchanted = [frames[(version, clock, True)] for clock in times]
        versions.append({'version': version,
            'loop_changes_frame': not np.array_equal(plain[0], plain[1]),
            'loop_returns_same_frame': bool(np.array_equal(plain[0], plain[3]) and np.array_equal(plain[0], plain[4])),
            'glint_present': bool(np.any(enchanted[0] != plain[0])),
            'glint_moves_on_same_source_frame': not np.array_equal(enchanted[0], enchanted[3])})
    report = {'schema': 1, 'scope': 'Actual fragment and native textures, offline GLES pixel verification',
              'game_started': False, 'production_qualified': False,
              'sources': {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (Path(__file__), catalog_path, atlas_path, glint_path, fragment)},
              'measurements': measurements, 'versions': versions,
              'passed': all(row['passed'] for row in measurements) and
                        all(all(value for name, value in row.items() if name != 'version') for row in versions)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

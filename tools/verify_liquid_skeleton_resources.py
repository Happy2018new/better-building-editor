"""Compile the real native strip candidate and replay pixel/alpha/frame controls."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from PIL import Image
from verify_biome_shader import shader_source

RENDER = '''async cases => {
 const rows=[];
 for (const item of cases) {
  const canvas=document.createElement('canvas');canvas.width=1;canvas.height=1;
  const gl=canvas.getContext(item.version===100?'webgl':'webgl2',{antialias:false});
  if(!gl){rows.push({name:item.name,passed:false,error:'GL unavailable'});continue;}
  try {
   function compile(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
   const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,item.vertex));
   gl.attachShader(p,compile(gl.FRAGMENT_SHADER,item.fragment));gl.linkProgram(p);
   if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));
   if(item.compile_only){rows.push({name:item.name,passed:true,compiled:true,checks:0});continue;}
   gl.useProgram(p);gl.viewport(0,0,1,1);
   const matrix=new Float32Array(16);matrix[15]=1;
   gl.uniformMatrix4fv(gl.getUniformLocation(p,'WORLDVIEWPROJ'),false,matrix);
   const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
   const pixels=Uint8Array.from(atob(item.rgba),c=>c.charCodeAt(0));
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,item.size[0],item.size[1],0,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   gl.uniform1i(gl.getUniformLocation(p,'TEXTURE_0'),0);
   gl.uniform4fv(gl.getUniformLocation(p,'HIDE_COLOR_FRAGMENT'),[1,1,1,1]);
   const position=gl.getAttribLocation(p,'POSITION');gl.disableVertexAttribArray(position);
   const failures=[];
   for(const fixture of item.fixtures){
    const projection=new Float32Array(16);projection[15]=fixture.ui?1:0;
    gl.uniformMatrix4fv(gl.getUniformLocation(p,'PROJ'),false,projection);
    gl.uniform4fv(gl.getUniformLocation(p,'CURRENT_COLOR'),[1,1,1,fixture.control_alpha??1]);
    for(let i=1;i<=4;i++)gl.uniform4fv(gl.getUniformLocation(p,'EXTRA_VECTOR'+i),fixture.uniforms[i-1]);
    gl.uniform1f(gl.getUniformLocation(p,'TIME'),fixture.time);
    gl.vertexAttrib4fv(position,fixture.position);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.POINTS,0,1);const actual=new Uint8Array(4);gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,actual);
    if(actual.some((x,i)=>Math.abs(x-fixture.expected[i])>1))failures.push({name:fixture.name,actual:[...actual],expected:fixture.expected});
   }
   rows.push({name:item.name,passed:failures.length===0,checks:item.fixtures.length,failures});
  }catch(error){rows.push({name:item.name,passed:false,error:String(error)});}
  finally{gl.getExtension('WEBGL_lose_context').loseContext();}
 }
 return rows;
}'''


def fixtures(image, ticks, frozen, diagnostic_opacity=None, sampling=None):
    rows = []
    width, height = image.size
    frames = height // width
    sampling = sampling or {'region': 'full', 'pixel_mapping': 'centers'}
    if sampling['region'] not in ('full', 'nw') or sampling['pixel_mapping'] not in ('centers', 'edges'):
        raise ValueError('Host controls need an explicit supported source-region candidate')
    span = width / 2 if sampling['region'] == 'nw' else width
    for u, v in ((0, 0), (1, 0), (1, 1), (0, 1), (.125, .125), (.875, .125),
                 (.875, .875), (.125, .875)):
        for clock in (0., .5, 1., 7.5, frames - .5, frames + .5):
            for opacity in (-1., .65):
                actual_clock = 0. if frozen else clock
                current, fraction = int(actual_clock) % frames, actual_clock % 1.
                x = min(width - 1, int(u * (span - 1) + .5 if sampling['pixel_mapping'] == 'centers' else u * span))
                y = min(width - 1, int(v * (span - 1) + .5 if sampling['pixel_mapping'] == 'centers' else v * span))
                first = image.getpixel((x, current * width + y))
                second = image.getpixel((x, ((current + 1) % frames) * width + y))
                texel = tuple(first[i] * (1. - fraction) + second[i] * fraction for i in range(4))
                expected = [round(texel[i] * tint / 255.) for i, tint in enumerate((18, 52, 86))]
                fallback = texel[3] if diagnostic_opacity is None else diagnostic_opacity * 255.
                expected.append(round((fallback if opacity < 0 else opacity * 255.) * .5))
                uniforms = [(4032., 0., 0., 0.), (45746., 45746., 0., 0.), (0.,) * 4,
                            (39686., opacity, float(0x123456), .5)]
                rows.append({'name': '%s/%s/%s/%s' % (u, v, clock, opacity),
                             'time': clock * ticks / 20., 'position': [u, v, 0., 1.],
                             'uniforms': uniforms, 'expected': expected})
    first=rows[0]
    for ui,alpha in ((True,0.),(True,.5),(True,1.),(False,0.),(False,.5)):
        expected=first['expected'][:]
        expected[3]=round(expected[3]*(alpha if ui else 1.))
        rows.append(dict(first,name='control_alpha/%s/%s' % (ui,alpha),
                         ui=ui,control_alpha=alpha,expected=expected))
    for bad in ('faces_zero', 'invalid_tag', 'unknown_rotation'):
        uniforms = [(4032., 0., 0., 0.), (45746., 45746., 0., 0.), (0.,) * 4,
                    (39686., -1., float(0xFFFFFF), 1.)]
        if bad == 'faces_zero':
            uniforms[0] = (0.,) * 4
        elif bad == 'invalid_tag':
            uniforms[3] = (0., -1., float(0xFFFFFF), 1.)
        else:
            uniforms[0] = (8128., 0., 0., 0.)
        rows.append({'name': bad, 'time': 0., 'position': [0., 0., 0., 1.],
                     'uniforms': uniforms, 'expected': [0, 0, 0, 0]})
    return rows


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    contract = json.loads((args.overlay / 'contract.json').read_bytes())
    shaders = args.overlay / 'resource_pack/shaders/glsl'
    cases = []
    for name in contract['models']:
        options = contract.get('model_options', {}).get(name, {})
        if options.get('variant') == 'matrix':
            for version in (100, 300):
                cases.append({'name': '%s/%s' % (name, version), 'version': version,
                              'vertex': shader_source(shaders / (name + '.vertex'), args.headers, version, ()),
                              'fragment': shader_source(shaders / (name + '.fragment'), args.headers, version, ()),
                              'compile_only': True})
            continue
        if options.get('variant') == 'packet' or name.endswith('_packet'):
            continue
        key = options.get('texture') or name.replace('modern_projection_liquid_', '').removesuffix('_frozen')
        texture = contract['textures'][key]
        path = args.overlay / ('resource_pack/textures/models/' + contract.get('asset_path', 'liquid_candidate') + '/' + key + '.png')
        with Image.open(path).convert('RGBA') as image:
            pixels, size = base64.b64encode(image.tobytes()).decode('ascii'), image.size
            inputs = fixtures(image, 1 if texture.get('frozen_diagnostic_only') else texture['flipbook']['ticks_per_frame'],
                              options.get('variant') == 'frozen' or name.endswith('_frozen'),
                              contract.get('diagnostic_water_opacity') if 'water' in key else None,
                              texture.get('sampling'))
        for version in (100, 300):
            for flags in (('BLEND',), ('BLEND', 'FOG')):
                cases.append({'name': '%s/%s/%s' % (name, version, flags), 'version': version,
                              'vertex': shader_source(shaders / (options.get('vertex_shader') or contract.get('vertex_shader', 'liquid_candidate.vertex')), args.headers, version, flags),
                              'fragment': shader_source(shaders / (options.get('fragment_shader') or name + '.fragment'), args.headers, version, flags),
                              'size': size, 'rgba': pixels, 'fixtures': inputs})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                              args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    report = {'schema': 1, 'results': results, 'passed': all(row['passed'] for row in results),
              'checks': sum(row.get('checks', 0) for row in results),
              'contract_sha256': hashlib.sha256((args.overlay / 'contract.json').read_bytes()).hexdigest(),
              'scope': 'Host native bitmap frame/tint/alpha controls, no native shape or public editor acceptance'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Render the actual biome shader pair on synthetic native-color fixtures.

Requires Playwright, Chromium, and the installed game's GLSL include directory.
Example: python tools/verify_biome_shader.py --headers <game/data/shaders/glsl>
    --browser <chromium.exe> --baseline-ref HEAD --report <local/result.json>
Add --vanilla-pack <game/data/resource_packs/vanilla> to check every grass
colormap color, explicit biome override, and representative boundary blend.
This checks GLES 2/3 pixels, not device screenshots or native mesh generation.
"""
import argparse
import json
import re
import subprocess
from itertools import combinations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHADERS = ROOT / 'resource_pack/shaders/glsl'
GRASS = {1: (146, 188, 88), 2: (121, 191, 90), 3: (136, 186, 103),
         4: (134, 181, 131), 5: (76, 118, 60), 6: (76, 118, 60),
         7: (88, 203, 60), 8: (190, 182, 84), 9: (190, 182, 84),
         10: (128, 180, 150)}
FOLIAGE = {1: (119, 171, 47), 2: (89, 174, 48), 3: (107, 169, 65),
           4: (104, 164, 100), 5: (106, 112, 57), 6: (141, 177, 39),
           7: (48, 187, 11), 8: (174, 164, 42), 9: (174, 164, 42),
           10: (96, 161, 123)}
# These explicit overrides are also used when installed game assets are not
# supplied. They differ from the editor's ten selectable target presets.
EXTRA_GRASS = {'badlands': (144, 129, 77), 'pale_garden': (119, 130, 114),
               'cherry_grove': (182, 219, 97), 'swamp': (106, 112, 57),
               'roofed_forest': (80, 122, 50)}


def native_grass_colors(pack):
    from PIL import Image

    colors = set(GRASS.values()) | set(EXTRA_GRASS.values())
    maps = {'grass'}
    for path in sorted((pack / 'biomes').glob('*.client_biome.json')):
        biome = json.loads(path.read_text(encoding='utf8'))['minecraft:client_biome']
        color = biome['components'].get('minecraft:grass_appearance', {}).get('color')
        if isinstance(color, str):
            colors.add(tuple(bytes.fromhex(color.lstrip('#'))))
        elif isinstance(color, dict):
            maps.add(color['color_map'])
    for name in sorted(maps):
        with Image.open(pack / 'textures/colormap' / (name + '.png')) as image:
            # Neutral white is unused colormap padding, not a grass tint.
            colors.update(c for c in image.convert('RGB').getdata() if max(c) != min(c))
    # The classifier must have no gap between accepted endpoints. Exercise
    # representative blends in addition to every actual texture color.
    anchors = set(GRASS.values()) | set(EXTRA_GRASS.values())
    for a, b in combinations(sorted(anchors), 2):
        for fraction in (.125, .25, .5, .75, .875):
            colors.add(tuple(round(x * (1-fraction) + y * fraction) for x, y in zip(a, b)))
    return sorted(colors)


def shader_source(path, headers, version, flags, ref=None):
    def expand(source):
        return re.sub(r'^\s*#include\s+"([^"]+)".*$',
                      lambda m: expand((headers / m[1]).read_text(encoding='utf8')),
                      source, flags=re.M)

    if ref:
        source = subprocess.check_output(
            ['git', 'show', ref + ':' + path.relative_to(ROOT).as_posix()],
            cwd=str(ROOT)).decode('utf8')
    else:
        source = path.read_text(encoding='utf8')
    prefix = '#version 300 es\n' if version == 300 else '#version 100\n'
    prefix += ('precision mediump float;\nprecision highp int;\n'
               '#define MCPE_NETEASE\n#define MAT4 highp mat4\n#define POS4 highp vec4\n')
    return prefix + ''.join('#define ' + f + '\n' for f in flags) + expand(source)


def fixtures(seasons=False, foliage=False):
    cases = []

    def add(name, mode, target, vertex, pixel, expected, tolerance=1):
        cases.append(dict(name=name, mode=mode, target=target, vertex=vertex,
                          pixel=list(pixel) + [255], expected=expected, tolerance=tolerance))

    for mode in ('ui', 'world'):
        for target, desired in GRASS.items():
            if seasons:
                tint = FOLIAGE[target] if foliage else desired
                add('seasonal/' + mode, mode, target, [.25, .75, 1, 1],
                    [128] * 3, [c * 128 / 255 for c in tint])
                add('seasonal-untinted/' + mode, mode, target, [.25, .75, 0, 1],
                    [128] * 3, [128] * 3)
                continue
            sources = dict(GRASS, savanna_quantized=(191, 183, 85),
                           savanna_plains_blend=(179, 184, 85))
            sources.update(EXTRA_GRASS)
            for source_name, color in sources.items():
                for shade in (1, .5, .25):
                    add('top/' + str(source_name) + '/' + str(shade) + '/' + mode,
                        mode, target, [c / 255 * shade for c in color] + [1],
                        [128] * 3, [c * 128 / 255 for c in desired])
            # The side's tinted grass fringe has neutral vertices; its dirt
            # area must retain its texture. Include the dry-biome fringe.
            for color in ((191, 183, 85), (121, 192, 90), (89, 201, 60)):
                add('side-fringe/' + str(color) + '/' + mode, mode, target, [1] * 4,
                    [round(c * .6) for c in color], [c * .6 for c in desired], 3)
            for name, pixel in (('stone', (128, 128, 128)), ('dirt', (134, 96, 67)),
                                ('yellow', (220, 205, 33)), ('green', (40, 150, 55)),
                                ('white', (255, 255, 255)), ('blue', (35, 65, 190))):
                add('neutral/' + name + '/' + mode, mode, target, [1] * 4, pixel, list(pixel))
            # Neutral vertex lighting must not become biome tint either.
            for shade in (.25, .55, .8):
                gain = max(.55, shade) if mode == 'ui' else shade
                add('neutral-light/' + str(shade) + '/' + mode, mode, target,
                    [shade] * 3 + [1], [128] * 3, [128 * gain] * 3)
            for color in ((1, .1, .1), (.2, .4, .9), (1, .8, .6)):
                gain = [max(.55, c) if mode == 'ui' else c for c in color]
                add('non-grass-vertex/' + str(color) + '/' + mode, mode, target,
                    list(color) + [1], [128] * 3, [128 * c for c in gain])
        if not seasons:
            add('untagged-world', 'native', 1, [190/255, 182/255, 84/255, 1],
                [128] * 3, [c * 128 / 255 for c in (190, 182, 84)])
    return cases


RENDER = r'''cases => {
  const results = [];
  for (const c of cases) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 4;
    const gl = canvas.getContext(c.version === 300 ? 'webgl2' : 'webgl', {antialias:false});
    if (!gl) throw Error('No GLES context: ' + c.version);
    gl.disable(gl.DITHER);
    const p = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,c.f]]) {
      const s = gl.createShader(type); gl.shaderSource(s,source); gl.compileShader(s);
      if (!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw Error(c.name+': '+gl.getShaderInfoLog(s));
      gl.attachShader(p,s);
    }
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p,gl.LINK_STATUS)) throw Error(c.name+': '+gl.getProgramInfoLog(p));
    gl.useProgram(p);
    const uniforms = {};
    function uniform(name) {
      if (!(name in uniforms)) uniforms[name] = gl.getUniformLocation(p,name);
      return uniforms[name];
    }
    const identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
    for (const name of ['WORLD','WORLDVIEW','WORLDVIEWPROJ'])
      gl.uniformMatrix4fv(uniform(name),false,identity);
    gl.uniform4f(uniform('TILE_LIGHT_COLOR'),1,1,1,1);
    gl.uniform1f(uniform('COMMON_BLOCK_GEO_FLOAT1_1'),1);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buf);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,1, 3,-1,0,1, -1,3,0,1]),gl.STATIC_DRAW);
    const position = gl.getAttribLocation(p,'POSITION');
    gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,4,gl.FLOAT,false,0,0);
    const color = gl.getAttribLocation(p,'COLOR');
    for (const name of ['TEXCOORD_0','TEXCOORD_1']) {
      const loc = gl.getAttribLocation(p,name); if (loc >= 0) gl.vertexAttrib2f(loc,.5,.5);
    }
    for (let unit=0; unit<2; ++unit) {
      gl.activeTexture(gl.TEXTURE0+unit); gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255,255]));
      gl.uniform1i(uniform('TEXTURE_'+unit),unit);
    }
    gl.activeTexture(gl.TEXTURE0);
    const failures = [], pixels = [];
    for (const f of c.fixtures) {
      const proj = identity.slice(); proj[10] = .001; proj[15] = f.mode === 'ui' ? 1 : 0;
      gl.uniformMatrix4fv(uniform('PROJ'),false,proj);
      // Preview depth -1 keeps the fixture in front of its clipping plane.
      gl.uniform4f(uniform('CURRENT_COLOR'),(208+f.target)/255,127/255,192/255,1);
      gl.uniform4f(uniform('EXTRA_ACTOR_UNIFORM4'),f.mode === 'world' ? 19487 : 0,f.target,0,0);
      if (color >= 0) gl.vertexAttrib4fv(color,f.vertex);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(f.pixel));
      gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLES,0,3);
      const pixel = new Uint8Array(4); gl.readPixels(1,1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
      if (gl.getError()) throw Error('GL draw failed: '+f.name);
      const actual = Array.from(pixel);
      if (actual[3] !== 255 || f.expected.some((v,i)=>Math.abs(actual[i]-v)>f.tolerance))
        failures.push({name:f.name,target:f.target,expected:f.expected,actual});
      if (f.name === 'top/9/1/ui') pixels.push({target:f.target,rgb:actual.slice(0,3)});
    }
    let paletteChecks = 0, paletteFailures = 0;
    const paletteFailureSamples = [];
    if (c.palette.length) {
      // Render one native-color cell per pixel, batching all sources in one
      // draw per target/mode/shade. This exercises both real shader stages
      // without thousands of synchronous readPixels calls.
      const width = 128, height = Math.ceil(c.palette.length/width);
      canvas.width = width; canvas.height = height; gl.viewport(0,0,width,height);
      const positions = new Float32Array(c.palette.length*6*4);
      const colors = new Float32Array(positions.length);
      for (let i=0; i<c.palette.length; ++i) {
        const x = i%width, y = Math.floor(i/width);
        const corners = [[x,y],[x+1,y],[x,y+1],[x+1,y],[x+1,y+1],[x,y+1]];
        for (let j=0; j<6; ++j)
          positions.set([corners[j][0]*2/width-1,corners[j][1]*2/height-1,0,1],(i*6+j)*4);
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,buf); gl.bufferData(gl.ARRAY_BUFFER,positions,gl.STATIC_DRAW);
      const colorBuffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,colorBuffer);
      gl.enableVertexAttribArray(color); gl.vertexAttribPointer(color,4,gl.FLOAT,false,0,0);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([128,128,128,255]));
      const bytes = new Uint8Array(width*height*4);
      for (const shade of [1,.5,.25]) {
        for (let i=0; i<c.palette.length; ++i)
          for (let j=0; j<6; ++j)
            colors.set([...c.palette[i].map(v=>v/255*shade),1],(i*6+j)*4);
        gl.bufferData(gl.ARRAY_BUFFER,colors,gl.DYNAMIC_DRAW);
        for (const mode of ['ui','world']) {
          const proj = identity.slice(); proj[10]=.001; proj[15]=mode==='ui'?1:0;
          gl.uniformMatrix4fv(uniform('PROJ'),false,proj);
          for (const [target, tint] of Object.entries(c.targets)) {
            gl.uniform4f(uniform('CURRENT_COLOR'),(208+Number(target))/255,127/255,192/255,1);
            gl.uniform4f(uniform('EXTRA_ACTOR_UNIFORM4'),mode==='world'?19487:0,Number(target),0,0);
            gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT);
            gl.drawArrays(gl.TRIANGLES,0,c.palette.length*6);
            gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
            if (gl.getError()) throw Error('GL palette draw failed');
            for (let i=0; i<c.palette.length; ++i) {
              ++paletteChecks;
              if (bytes[i*4+3]!==255 || tint.some((v,k)=>Math.abs(bytes[i*4+k]-v*128/255)>1)) {
                ++paletteFailures;
                if (paletteFailureSamples.length<12)
                  paletteFailureSamples.push({source:c.palette[i],mode,target,shade,
                    actual:Array.from(bytes.slice(i*4,i*4+4))});
              }
            }
          }
        }
      }
    }
    results.push({name:c.name,checks:c.fixtures.length,failures,savanna_pixels:pixels,
      palette_sources:c.palette.length,palette_checks:paletteChecks,
      palette_failures:paletteFailures,palette_failure_samples:paletteFailureSamples});
    gl.getExtension('WEBGL_lose_context').loseContext();
  }
  return results;
}'''


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser')
    parser.add_argument('--baseline-ref')
    parser.add_argument('--vanilla-pack', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    palette = native_grass_colors(args.vanilla_pack) if args.vanilla_pack else []
    cases = []
    refs = [('fixed', None)]
    if args.baseline_ref:
        refs.append(('baseline', args.baseline_ref))
    for label, ref in refs:
        for version in (100, 300):
            for flags in ((), ('BLEND', 'ALPHA_TEST'), ('SEASONS',), ('SEASONS', 'ALPHA_TEST')):
                cases.append(dict(
                    name=label + '/' + str(version) + '/' + ','.join(flags), version=version,
                    v=shader_source(SHADERS / 'modern_projection_biome_blocks.vertex',
                                    args.headers, version, flags, ref),
                    f=shader_source(SHADERS / 'modern_projection_biome_blocks.fragment',
                                    args.headers, version, flags, ref),
                    fixtures=fixtures('SEASONS' in flags, 'ALPHA_TEST' in flags),
                    palette=[] if 'SEASONS' in flags else palette,
                    targets={str(k): v for k, v in GRASS.items()}))
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True,
                                    args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        results = browser.new_page().evaluate(RENDER, cases)
        browser.close()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(results, indent=2), encoding='utf8')
    fixed = [r for r in results if r['name'].startswith('fixed/')]
    failures = [f for r in fixed for f in r['failures']]
    palette_failures = sum(r['palette_failures'] for r in fixed)
    print(json.dumps(dict(programs=len(fixed), checks=sum(r['checks'] for r in fixed),
                          palette_sources=len(palette),
                          palette_checks=sum(r['palette_checks'] for r in fixed),
                          failures=len(failures) + palette_failures,
                          baseline_failures=sum(len(r['failures']) + r['palette_failures'] for r in results
                                                if r['name'].startswith('baseline/')))))
    if failures or palette_failures:
        print(json.dumps(failures[:10]))
        print(json.dumps([r['palette_failure_samples'] for r in fixed if r['palette_failures']]))
        raise SystemExit(1)


if __name__ == '__main__':
    main()

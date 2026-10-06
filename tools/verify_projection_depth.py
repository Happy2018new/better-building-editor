"""Render the production projection/sky shaders against depth and MSAA targets.

Requires Playwright, Chromium and the installed game's GLSL include directory:
    python tools/verify_projection_depth.py --headers <game/data/shaders/glsl>
        --browser <chromium.exe> --report <result.json>

The native terrain material beside the headers supplies inheritance; repository
overrides supply the final states and shaders. Wall and particle quads are test
geometry. This verifies GPU compositing, not Minecraft's native draw ordering.
"""
import argparse
import json
import re
from pathlib import Path

from verify_biome_shader import ROOT, shader_source


def read_materials(path):
    source = path.read_text(encoding='utf8')
    return json.loads(re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S))['materials']


def terrain_materials(headers):
    """Resolve only the native material chains used by these draws."""
    native = headers.parents[1] / 'resource_packs/vanilla_netease/materials/terrain.material'
    layers, parents = {}, {}
    for path in (native, ROOT / 'resource_pack/materials/terrain.material'):
        for key, value in read_materials(path).items():
            if key == 'version':
                continue
            name, _, parent = key.partition(':')
            layers.setdefault(name, []).append(value)
            if parent:
                parents[name] = parent

    def resolve(name):
        result = resolve(parents[name]) if name in parents else {}
        for layer in layers[name]:
            for key, value in layer.items():
                if not key.startswith(('+', '-')):
                    result[key] = value
            for key in ('states', 'defines'):
                values = list(result.get(key, []))
                values += [v for v in layer.get('+' + key, []) if v not in values]
                result[key] = [v for v in values if v not in layer.get('-' + key, [])]
        return result

    return {name: resolve(name) for name in (
        'netease_block_as_mesh_opaque', 'netease_block_as_mesh_blend_enable_transparency',
        'netease_block_as_mesh_alpha_seasons', 'netease_block_as_mesh_blend_alphatest_seasons')}


def program(material, headers, msaa):
    flags = list(material.get('defines', []))
    if msaa:
        flags.append('MSAA_FRAMEBUFFER_ENABLED')
    if msaa and 'EnableAlphaToCoverage' in material['states']:
        flags.append('ALPHA_TO_COVERAGE')
    result = {'material': material}
    for stage, key in (('v', 'vertexShader'), ('f', 'fragmentShader')):
        path = ROOT / 'resource_pack' / material[key]
        if not path.exists():
            path = headers / Path(material[key]).name
        source = shader_source(path, headers, 300, flags)
        # The engine injects default precision for generic sky shaders.
        result[stage] = source.replace('#version 300 es\n',
                                      '#version 300 es\nprecision highp float;\nprecision highp int;\n', 1)
    return result


RENDER = r'''cases => {
  const results = [], size = 96;
  for (const c of cases) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const gl = canvas.getContext('webgl2', {antialias:false});
    if (!gl) throw Error('WebGL2 unavailable');
    const depthFormat = c.depth === 16 ? gl.DEPTH_COMPONENT16 : gl.DEPTH_COMPONENT24;
    let samples = 0;
    if (c.msaa) {
      const depthSamples = Array.from(gl.getInternalformatParameter(gl.RENDERBUFFER,depthFormat,gl.SAMPLES));
      const colorSamples = Array.from(gl.getInternalformatParameter(gl.RENDERBUFFER,gl.RGBA8,gl.SAMPLES));
      samples = Math.max(0,...depthSamples.filter(n=>n>1 && n<=4 && colorSamples.includes(n)));
      if (samples < 2) throw Error(c.name+': no common multisample color/depth format');
    }
    function target(multisample, depth) {
      const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER,fb);
      for (const [attachment,format] of [[gl.COLOR_ATTACHMENT0,gl.RGBA8],
                                        ...(depth ? [[gl.DEPTH_ATTACHMENT,depthFormat]] : [])]) {
        const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER,rb);
        if (multisample) gl.renderbufferStorageMultisample(gl.RENDERBUFFER,multisample,format,size,size);
        else gl.renderbufferStorage(gl.RENDERBUFFER,format,size,size);
        if (gl.getRenderbufferParameter(gl.RENDERBUFFER,gl.RENDERBUFFER_SAMPLES) !== multisample)
          throw Error('Unexpected renderbuffer sample count');
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER,attachment,gl.RENDERBUFFER,rb);
      }
      if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE)
        throw Error(c.name+': incomplete framebuffer');
      return fb;
    }
    const drawTarget = target(samples,true), readTarget = samples ? target(0,false) : drawTarget;
    gl.viewport(0,0,size,size); gl.disable(gl.DITHER);
    function compile(v,f,material) {
      const p = gl.createProgram();
      for (const [type,source] of [[gl.VERTEX_SHADER,v],[gl.FRAGMENT_SHADER,f]]) {
        const shader = gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
        if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
        gl.attachShader(p,shader);
      }
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(p));
      return {p,material};
    }
    const programs = {};
    for (const [name,p] of Object.entries(c.programs)) programs[name] = compile(p.v,p.f,p.material);
    const flat = compile('#version 300 es\nin vec4 POSITION; void main(){gl_Position=POSITION;}',
      '#version 300 es\nprecision highp float; uniform vec4 ink; out vec4 frag; void main(){frag=ink;}',{});
    const identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
    // Actual perspective: near=1, far=20, 90 degree FOV.
    const projection = [1,0,0,0, 0,1,0,0, 0,0,-21/19,-1, 0,0,-40/19,0];
    const buffer = gl.createBuffer();
    function attribute(p,name,values,width) {
      const loc = gl.getAttribLocation(p,name); if (loc < 0) return;
      gl.disableVertexAttribArray(loc);
      if (width === 2) gl.vertexAttrib2fv(loc,values); else gl.vertexAttrib4fv(loc,values);
    }
    function vertices(p,points) {
      gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(points),gl.STREAM_DRAW);
      const position = gl.getAttribLocation(p,'POSITION');
      gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,4,gl.FLOAT,false,24,0);
      const uv = gl.getAttribLocation(p,'TEXCOORD_0');
      if (uv >= 0) {gl.enableVertexAttribArray(uv); gl.vertexAttribPointer(uv,2,gl.FLOAT,false,24,16);}
      gl.drawArrays(gl.TRIANGLES,0,points.length/6);
    }
    function rectangle(bounds,depths,clip=false) {
      const [x0,y0,x1,y1] = bounds, [left,right] = Array.isArray(depths) ? depths : [depths,depths];
      const corners = [[x0,y0,left,0,0],[x1,y0,right,1,0],[x1,y1,right,1,1],[x0,y1,left,0,1]];
      return [0,1,2,0,2,3].flatMap(i=>{
        const [x,y,d,u,v] = corners[i];
        return clip ? [x,y,d,1,u,v] : [x*d,y*d,-d,1,u,v];
      });
    }
    function state(material) {
      const s = material.states || [];
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(material.depthFunc === 'LessEqual' ? gl.LEQUAL : gl.LESS);
      gl.depthMask(!s.includes('DisableDepthWrite'));
      const rgb = !s.includes('DisableColorWrite') && !s.includes('DisableRGBWrite');
      gl.colorMask(rgb,rgb,rgb,!s.includes('DisableColorWrite') && !s.includes('DisableAlphaWrite'));
      if (s.includes('DisableCulling')) gl.disable(gl.CULL_FACE);
      else {gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);}
      if (s.includes('EnableAlphaToCoverage')) gl.enable(gl.SAMPLE_ALPHA_TO_COVERAGE);
      else gl.disable(gl.SAMPLE_ALPHA_TO_COVERAGE);
      if (s.includes('Blending')) {
        gl.enable(gl.BLEND);
        const factors = {SourceAlpha:gl.SRC_ALPHA, OneMinusSrcAlpha:gl.ONE_MINUS_SRC_ALPHA, One:gl.ONE, Zero:gl.ZERO};
        gl.blendFunc(factors[material.blendSrc || 'SourceAlpha'],factors[material.blendDst || 'OneMinusSrcAlpha']);
      } else gl.disable(gl.BLEND);
    }
    const texture = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    function biome(name,points,tag,cutout=false,forceA2C=false) {
      const {p,material} = programs[name]; gl.useProgram(p); state(material);
      if (forceA2C) gl.enable(gl.SAMPLE_ALPHA_TO_COVERAGE);
      else if (gl.isEnabled(gl.SAMPLE_ALPHA_TO_COVERAGE))
        throw Error(name+': production projection/guard unexpectedly enables A2C');
      const u = name=>gl.getUniformLocation(p,name);
      for (const name of ['WORLD','WORLDVIEW']) gl.uniformMatrix4fv(u(name),false,identity);
      for (const name of ['PROJ','WORLDVIEWPROJ']) gl.uniformMatrix4fv(u(name),false,projection);
      gl.uniform4f(u('CURRENT_COLOR'),1,1,1,1);
      gl.uniform4f(u('EXTRA_ACTOR_UNIFORM4'),tag,1,0,0);
      gl.uniform4f(u('TILE_LIGHT_COLOR'),1,1,1,1);
      gl.uniform4f(u('FOG_COLOR'),0,0,0,0);
      gl.uniform1f(u('COMMON_BLOCK_GEO_FLOAT1_1'),tag === 19487 ? .45 : 1);
      attribute(p,'COLOR',[1,1,1,1],4); attribute(p,'TEXCOORD_1',[.5,.5],2);
      gl.uniform1i(u('TEXTURE_0'),0); gl.uniform1i(u('TEXTURE_1'),0);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,2,1,0,gl.RGBA,gl.UNSIGNED_BYTE,
        new Uint8Array([180,100,60,255,180,100,60,cutout ? 0 : 255]));
      vertices(p,points);
    }
    function sky() {
      const {p,material} = programs.sky; gl.useProgram(p); state(material);
      gl.uniformMatrix4fv(gl.getUniformLocation(p,'WORLDVIEWPROJ'),false,identity);
      gl.uniform4f(gl.getUniformLocation(p,'CURRENT_COLOR'),.16,.43,.75,1);
      gl.uniform4f(gl.getUniformLocation(p,'FOG_COLOR'),.16,.43,.75,1);
      attribute(p,'COLOR',[0,0,0,1],4);
      vertices(p,rectangle([-1,-1,1,1],0,true));
    }
    function solid(bounds,d,ink,particle=false) {
      const {p} = flat; gl.useProgram(p);
      state({states:particle ? ['DisableDepthWrite','Blending'] : [],blendSrc:'SourceAlpha',blendDst:'One'});
      gl.uniform4fv(gl.getUniformLocation(p,'ink'),ink);
      // Project fixture depth with the same perspective used by biome draws.
      vertices(p,rectangle(bounds,(21*d-40)/(19*d),true));
    }
    function frame(draw) {
      gl.bindFramebuffer(gl.FRAMEBUFFER,drawTarget);
      gl.colorMask(true,true,true,true); gl.depthMask(true);
      gl.clearColor(.04,.06,.09,1); gl.clearDepth(1); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      draw();
      if (samples) {
        gl.bindFramebuffer(gl.READ_FRAMEBUFFER,drawTarget); gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER,readTarget);
        gl.blitFramebuffer(0,0,size,size,0,0,size,size,gl.COLOR_BUFFER_BIT,gl.NEAREST);
      }
      gl.bindFramebuffer(gl.FRAMEBUFFER,readTarget);
      const pixels = new Uint8Array(size*size*4);
      gl.readPixels(0,0,size,size,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
      const error = gl.getError(); if (error) throw Error(c.name+': GL error '+error);
      return pixels;
    }
    function difference(a,b,index) {
      return Math.max(...[0,1,2].map(k=>Math.abs(a[index*4+k]-b[index*4+k])));
    }
    function changed(a,b,bounds=[-1,-1,1,1]) {
      let n=0;
      for (let y=0;y<size;y++) for (let x=0;x<size;x++) {
        const nx=(x+.5)*2/size-1, ny=(y+.5)*2/size-1;
        if (nx>bounds[0] && nx<bounds[2] && ny>bounds[1] && ny<bounds[3] && difference(a,b,y*size+x)>2) ++n;
      }
      return n;
    }
    function result(name,measurements,conditions) {
      results.push({name:c.name+'/'+name,samples,depth_bits:c.depth,measurements,checks:Object.keys(conditions).length,
        failures:Object.entries(conditions).filter(([name,ok])=>!ok).map(([name])=>name)});
    }
    const quad = rectangle([-.85,-.75,.85,.75],4);
    const starBounds = [[-.65,-.2,-.35,.2],[-.15,-.2,.15,.2],[.25,-.2,.55,.2]];
    function scene(stars,guard=true,surface=true) {
      return frame(()=>{
        solid([.2,-.3,.65,.3],5,[.2,.28,.24,1]);
        if (guard) biome('guard',quad,19488);
        if (surface) biome('projection',quad,19487);
        sky();
        if (stars) starBounds.forEach((bounds,i)=>solid(bounds,i===1 ? 3 : 6,[1,.7,.15,.8],true));
      });
    }
    const baseline=scene(false), stars=scene(true), noSurface=scene(false,true,false), noGuard=scene(false,false);
    const behind=changed(stars,baseline,starBounds[0]), front=changed(stars,baseline,starBounds[1]);
    const blocked=changed(stars,baseline,starBounds[2]);
    const surface=changed(baseline,noSurface,[-.75,.35,.75,.65]);
    const guardControl=changed(baseline,noGuard,[-.75,.35,.75,.65]);
    result('star-and-real-wall',{behind,front,blocked,surface,guard_control:guardControl},
      {behind_projection_visible:behind>100,front_visible:front>100,wall_blocks_star:blocked===0,
       projection_surface_present:surface>500,sky_really_overwrites_without_guard:guardControl>500});

    const skyOnly=frame(sky);
    function cutout(guard=true,forceA2C=false) {
      return frame(()=>{
        if (guard) biome('cutoutGuard',quad,19488,true,forceA2C);
        biome('cutoutProjection',quad,19487,true); sky();
      });
    }
    const leaves=cutout(), withoutLeafGuard=cutout(false);
    const hole=changed(leaves,skyOnly,[.1,-.6,.7,.6]);
    const leaf=changed(leaves,skyOnly,[-.7,-.6,-.1,.6]);
    const leafGuard=changed(leaves,withoutLeafGuard,[-.7,-.6,-.1,.6]);
    const a2cControl=samples ? changed(cutout(true,true),withoutLeafGuard,[-.7,-.6,-.1,.6]) : null;
    result('cutout-sky',{hole,leaf,guard_control:leafGuard,a2c_control:a2cControl},
      {holes_retain_sky:hole===0,leaf_surface_present:leaf>1000,guard_protects_leaf:leafGuard>1000,
       msaa_a2c_control:samples===0 || a2cControl===0});

    // The normal draw is a GPU clipping oracle. The guard must not resurrect
    // fully clipped quads or the clipped portions of near/far-crossing quads.
    const clipping = [rectangle([-.85,.2,-.15,.8],.5),rectangle([.15,.2,.85,.8],25),
      rectangle([-.85,-.8,-.15,-.2],[.5,3]),rectangle([.15,-.8,.85,-.2],[12,30])].flat();
    const clear=frame(()=>{});
    const clippedSurface=frame(()=>biome('projection',clipping,19487));
    const clippedGuard=frame(()=>{biome('guard',clipping,19488);sky();});
    const visible=[], masked=[];
    for (let i=0;i<size*size;i++) {
      visible.push(difference(clippedSurface,clear,i)>2);
      masked.push(difference(clippedGuard,skyOnly,i)>2);
    }
    let leaks=0,missing=0,interior=0;
    for (let y=1;y<size-1;y++) for (let x=1;x<size-1;x++) {
      const i=y*size+x, neighbors=[];
      for (let dy=-1;dy<=1;dy++) for (let dx=-1;dx<=1;dx++) neighbors.push(visible[i+dy*size+dx]);
      if (!neighbors.some(Boolean) && masked[i]) ++leaks;
      if (neighbors.every(Boolean)) {++interior;if (!masked[i]) ++missing;}
    }
    const fullyClipped=changed(clippedGuard,skyOnly,[-.9,.1,.9,.9]);
    result('original-near-far-clipping',{visible_pixels:visible.filter(Boolean).length,
      guard_pixels:masked.filter(Boolean).length,interior,leaks,missing,fully_clipped:fullyClipped},
      {crossing_fixture_nonempty:interior>100,no_resurrected_fragments:leaks===0,
       retained_fragments_protected:missing===0,fully_clipped_geometry_has_no_mask:fullyClipped===0});
    gl.getExtension('WEBGL_lose_context').loseContext();
  }
  return results;
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    headers = args.headers.resolve()
    materials = terrain_materials(headers)
    sky = read_materials(ROOT / 'resource_pack/materials/sky.material')['skyplane']
    names = dict(guard='netease_block_as_mesh_opaque',
                 projection='netease_block_as_mesh_blend_enable_transparency',
                 cutoutGuard='netease_block_as_mesh_alpha_seasons',
                 cutoutProjection='netease_block_as_mesh_blend_alphatest_seasons')
    cases = []
    for depth in (16, 24):
        for msaa in (False, True):
            programs = {name: program(materials[key], headers, msaa) for name, key in names.items()}
            programs['sky'] = program(sky, headers, msaa)
            cases.append(dict(name='D%d/%s' % (depth, 'MSAA' if msaa else 'single'),
                              depth=depth, msaa=msaa, programs=programs))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, cases)
        finally:
            browser.close()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(results, indent=2), encoding='utf8')
    failures = [dict(name=r['name'], failures=r['failures']) for r in results if r['failures']]
    print(json.dumps(dict(groups=len(results), checks=sum(r['checks'] for r in results),
                          failures=failures), indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

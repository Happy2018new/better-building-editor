"""Render real preview outline/grid shader branches under GLES 2 and GLES 3.

Uses the same installed engine headers and Chromium options as
verify_biome_shader.py. Example:
    python tools/verify_outline_shader.py --headers <game/data/shaders/glsl>
        --browser <chromium.exe> --report .runtime/outline_shader_checks.json

Each of the twelve encoded outline source quads is rendered separately. An
independent screen-space line oracle checks silhouette, color, alpha and signed
clipping, including maximum packed dimensions and phase/depth carry boundaries.
Grid checks measure distances to projected integer lines, including empty cells
and multiple native UI widths. This is software GPU shader validation; it does
not launch Minecraft or verify native mesh generation or PaperDoll binding.
"""
import argparse
import json
import math
from pathlib import Path

from verify_biome_shader import SHADERS, shader_source


WIDTH = 256
UI_SPAN = 128.
PIXELS_PER_UI = WIDTH / UI_SPAN


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def matrix(rows, translation=(0., 0., 0.)):
    return [rows[row][col] if row < 3 and col < 3 else
            translation[row] if row < 3 else float(col == 3)
            for col in range(4) for row in range(4)]


def pose(yaw, pitch, scale):
    yaw, pitch = math.radians(yaw), math.radians(pitch)
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    rotation = ((cy, 0., -sy), (sy*sp, cp, cy*sp), (sy*cp, -sp, cy*cp))
    return [[v*scale for v in row] for row in rotation], rotation[2]


def screen(point, rows, translation=(0., 0., 0.)):
    return [WIDTH/2. + (dot(point, rows[i])+translation[i])*PIXELS_PER_UI
            for i in (0, 1)]


def depth_packet(distance):
    return max(0, min(65535, math.floor(distance*64.+.5)+32768))


def outline_fixture(index, size, rows, toward, *, style='blue', phase=0,
                    distance=-300., thickness=1.4, alpha=1., translation=(0., 0., 0.)):
    # Explicit cuboid endpoints are the oracle, independent of the shader's
    # index/axis swizzles. Four corners for each of X, Y and Z.
    axis = index // 4
    fixed_axes = [a for a in range(3) if a != axis]
    signs = ((-1, -1), (-1, 1), (1, -1), (1, 1))[index % 4]
    start, end = [0., 0., 0.], [0., 0., 0.]
    for fixed, sign in zip(fixed_axes, signs):
        start[fixed] = end[fixed] = sign*size[fixed]/2.
    start[axis], end[axis] = -size[axis]/2., size[axis]/2.
    tag = {'blue': 224, 'spectrum': 225, 'invalid': 226}[style]
    dimensions = size[0]-1 + (size[1]-1)*64 + (size[2]-1)*8192
    depth = depth_packet(distance)
    distance = (depth-32768)/64.
    hue = [dot([p[i]/size[i]+.5 for i in range(3)], (.1875, .3125, .125))
           + phase/256. for p in (start, end)]
    # Actor block geometry presents the source plane as X=[2*i-1,2*i],
    # Z=[-1,0]. These are input vertices, not post-shader screen quads.
    vertices = [[2*index-1+along, 0., across-1., 1.]
                for along, across in ((0, 0), (1, 0), (0, 1), (1, 0), (1, 1), (0, 1))]
    return dict(name='outline/%s/%s/edge%d/phase%d/depth%s' %
                (style, 'x'.join(map(str, size)), index, phase, distance),
                kind='outline', vertices=vertices, worldview=matrix(rows, translation),
                color=[(tag+thickness/8.)/255., dimensions/524288.,
                       (depth*256+phase)/16777216., alpha],
                start=screen(start, rows, translation), end=screen(end, rows, translation),
                clips=[dot(p, toward)+distance for p in (start, end)],
                hue=hue, style=style, thickness=thickness*PIXELS_PER_UI, alpha=alpha)


def grid_fixture(yaw, pitch, scale, thickness, distance=-300., translation=(0., 0., 0.)):
    rows, toward = pose(yaw, pitch, scale)
    extent = 3.
    vertices = [[2*index-1+along,0.,across-1.,1.]
                for index in range(130)
                for along,across in ((0,0),(1,0),(0,1),(1,0),(1,1),(0,1))]
    depth = depth_packet(distance)
    distance = (depth-32768)/64.
    lines = []
    for coordinate in range(-3, 4):
        for axis in (0, 2):
            a, b = [0., 0., 0.], [0., 0., 0.]
            a[axis] = b[axis] = coordinate
            a[2-axis], b[2-axis] = -extent, extent
            lines.append([screen(a, rows, translation), screen(b, rows, translation)])
    return dict(name='grid/yaw%s/pitch%s/scale%s/width%s/depth%s' %
                (yaw, pitch, scale, thickness, distance),
                kind='grid', vertices=vertices, worldview=matrix(rows, translation),
                color=[(223.+thickness/8.)/255., (5+5*8192)/524288., depth*256/16777216., 1.],
                origin=screen((0., 0., 0.), rows, translation),
                axis_x=[dot((1., 0., 0.), row)*PIXELS_PER_UI for row in rows[:2]],
                axis_z=[dot((0., 0., 1.), row)*PIXELS_PER_UI for row in rows[:2]],
                toward=toward, distance=distance, extent=extent, lines=lines,
                thickness=thickness*PIXELS_PER_UI, alpha=1.)


def fixtures():
    cases = []
    for size in ((1, 1, 1), (3, 5, 7), (64, 128, 64)):
        for yaw, pitch in ((35, 25), (125, 65)):
            rows, toward = pose(yaw, pitch, 60./max(size))
            for style, phase in (('blue', 0), ('spectrum', 0), ('spectrum', 137), ('invalid', 255)):
                for index in range(12):
                    case = outline_fixture(index, size, rows, toward, style=style, phase=phase)
                    case['name'] += '/yaw%s' % yaw
                    cases.append(case)

    rows, toward = pose(35, 25, 7.)
    for distance in (-2., 0., 2.):
        for index in range(12):
            cases.append(outline_fixture(index, (8, 6, 4), rows, toward,
                                          style='spectrum', phase=255, distance=distance, alpha=.6))

    # Float32 state values above 2**23 cannot safely be rounded with +0.5:
    # odd phases round up; phase 255 carries into the signed clip distance.
    # Place a pixel centre 1/128 block on either side of the clip plane.
    rows = [[6.4, 0., 4.8], [0., 8., 0.], [-4.8, 0., 6.4]]
    toward = [-.6, 0., .8]
    for distance, phase in ((0., 255), (.5, 1)):
        for clip in (-1./128., 1./128.):
            point = [(distance-.4-clip)/.6, -2., -.5]
            translation = tuple(.25-dot(point, row) for row in rows[:2]) + (0.,)
            case = outline_fixture(0, (8, 4, 1), rows, toward, style='spectrum', phase=phase,
                                   distance=distance, translation=translation)
            case['name'] += '/clip-probe%s' % clip
            case['probes'] = [[128, 128]]
            cases.append(case)

    # At a fragment-grid half-width boundary, the outline must still cover
    # that pixel. This deliberately probes the tiny inclusive-width epsilon.
    rows = [[8., 0., 0.], [0., 8., 0.], [0., 0., 8.]]
    for thickness in (.65, 1.4, 2.2):
        translation = (0., .25+8.-thickness/2., 0.)
        case = outline_fixture(0, (8, 2, 2), rows, (0., 0., 1.),
                               thickness=thickness, translation=translation)
        case['name'] += '/inclusive-width%s' % thickness
        case['probes'] = [[132, 128]]
        cases.append(case)
        grid = grid_fixture(0, 90, 8., thickness, translation=(0., .25-thickness/2., 0.))
        grid['name'] += '/inclusive-width%s' % thickness
        grid['probes'] = [[132, 128]]
        cases.append(grid)

    for yaw, pitch in ((0, 90), (35, 25), (125, 65)):
        for scale in (6., 12.):
            for thickness in (.65, 1.4, 2.2):
                cases.append(grid_fixture(yaw, pitch, scale, thickness))
    for distance in (-.5, 0., .5):
        cases.append(grid_fixture(35, 25, 10., 1.4, distance))
    return cases


RENDER = r'''cases => {
  const results = [], clear = [17,29,41,255], width = 256;
  const identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
  const projection = identity.slice(); projection[0]=projection[5]=2/128; projection[10]=.001;
  function mix(a,b,t) { return a+(b-a)*t; }
  function ink(f,t) {
    if (f.kind==='grid') return [155,172,204,255*f.alpha];
    if (f.style==='blue') return [71,122,244,255*f.alpha];
    if (f.style==='invalid') return [211,92,114,255*f.alpha];
    const hue=mix(f.hue[0],f.hue[1],t);
    return [0,2/3,1/3].map(offset => {
      const cycle=((hue+offset)%1+1)%1;
      const channel=Math.max(0,Math.min(1,Math.abs(cycle*6-3)-1));
      return .98*(.45+.55*channel)*255;
    }).concat(255*f.alpha);
  }
  function lineDistance(point,a,b) {
    const dx=b[0]-a[0],dy=b[1]-a[1];
    return Math.abs((point[0]-a[0])*dy-(point[1]-a[1])*dx)/Math.hypot(dx,dy);
  }
  function expected(f,x,y,probe=false) {
    const point=[x+.5,y+.5];
    if (f.kind==='outline') {
      const dx=f.end[0]-f.start[0],dy=f.end[1]-f.start[1],length=Math.hypot(dx,dy);
      const t=((point[0]-f.start[0])*dx+(point[1]-f.start[1])*dy)/(length*length);
      const across=lineDistance(point,f.start,f.end),half=f.thickness/2;
      const clip=mix(f.clips[0],f.clips[1],t);
      // Avoid rasterization ownership ambiguities on triangle edges. Explicit
      // probes below keep the signed-depth and inclusive-width boundaries strict.
      if (!probe && (Math.min(Math.abs(t),Math.abs(1-t))*length<.15 ||
          Math.abs(across-half)<.15 || Math.abs(clip)<.002)) return null;
      const visible=t>=0 && t<=1 && across<=half+.00001 && clip<=0;
      return {rgba:visible?ink(f,t):clear,visible};
    }
    const [ax,ay]=f.axis_x,[zx,zy]=f.axis_z;
    const px=point[0]-f.origin[0],py=point[1]-f.origin[1],det=ax*zy-ay*zx;
    const localX=(px*zy-py*zx)/det,localZ=(ax*py-ay*px)/det;
    const candidates=f.lines.map(([a,b])=>{
      const dx=b[0]-a[0],dy=b[1]-a[1];
      const t=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(dx*dx+dy*dy);
      const centre=[mix(a[0],b[0],t)-f.origin[0],mix(a[1],b[1],t)-f.origin[1]];
      const cx=(centre[0]*zy-centre[1]*zx)/det,cz=(ax*centre[1]-ay*centre[0])/det;
      return {distance:lineDistance(point,a,b),t,clip:f.toward[0]*cx+f.toward[2]*cz+f.distance};
    });
    const distance=Math.min(...candidates.map(c=>c.t>=0&&c.t<=1?c.distance:Infinity));
    const boundary=Math.min(Math.abs(Math.abs(localX)-f.extent),Math.abs(Math.abs(localZ)-f.extent));
    // A low-precision GPU snaps source triangles at 1/16 pixel. Bound the
    // resulting clip interpolation ambiguity in block units; explicit probes
    // still test signed clipping on either side of the plane without a skip.
    const clipTolerance=Math.hypot(f.toward[0]*zy-f.toward[2]*ay,
                                  f.toward[2]*ax-f.toward[0]*zx)/Math.abs(det)/16;
    if (!probe && (boundary<.015 || candidates.some(c=>Math.abs(c.distance-f.thickness/2)<.15) ||
        candidates.some(c=>c.distance<f.thickness/2+.15&&Math.abs(c.clip)<clipTolerance))) return null;
    const visible=candidates.some(c=>c.t>=0&&c.t<=1&&c.distance<=f.thickness/2+.00001&&c.clip<=0);
    return {rgba:visible?ink(f,0):clear,visible};
  }
  for (const c of cases) {
    const canvas=document.createElement('canvas');canvas.width=canvas.height=width;
    const gl=canvas.getContext(c.version===300?'webgl2':'webgl',
      {antialias:false,premultipliedAlpha:false});
    if (!gl) throw Error('No GLES context: '+c.version);
    gl.disable(gl.DITHER);gl.disable(gl.BLEND);gl.disable(gl.CULL_FACE);
    const program=gl.createProgram();
    for (const [type,source] of [[gl.VERTEX_SHADER,c.v],[gl.FRAGMENT_SHADER,c.f]]) {
      const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(c.name+': '+gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(c.name+': '+gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const uniforms={};
    const uniform=name=>Object.hasOwn(uniforms,name)?uniforms[name]:(uniforms[name]=gl.getUniformLocation(program,name));
    for (const name of ['WORLD','WORLDVIEW','WORLDVIEWPROJ']) gl.uniformMatrix4fv(uniform(name),false,identity);
    gl.uniformMatrix4fv(uniform('PROJ'),false,projection);
    gl.uniform2f(uniform('VIEWPORT_SIZE'),width,width);
    gl.uniform4f(uniform('TILE_LIGHT_COLOR'),1,1,1,1);
    gl.uniform1f(uniform('COMMON_BLOCK_GEO_FLOAT1_1'),1);
    for (const name of ['COLOR','TEXCOORD_0','TEXCOORD_1']) {
      const loc=gl.getAttribLocation(program,name);
      if (loc>=0) name==='COLOR'?gl.vertexAttrib4f(loc,1,1,1,1):gl.vertexAttrib2f(loc,.5,.5);
    }
    for (let unit=0;unit<2;++unit) {
      gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255,255]));
      gl.uniform1i(uniform('TEXTURE_'+unit),unit);
    }
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    const position=gl.getAttribLocation(program,'POSITION');
    gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,4,gl.FLOAT,false,0,0);
    const bytes=new Uint8Array(width*width*4),measurements=[],failures=[];
    let pixelChecks=0;
    for (const f of c.fixtures) {
      const combined=f.worldview.slice();
      for (let col=0;col<4;++col)
        for (let row=0;row<3;++row) combined[col*4+row]*=projection[row*4+row];
      gl.uniformMatrix4fv(uniform('WORLDVIEW'),false,f.worldview);
      gl.uniformMatrix4fv(uniform('WORLDVIEWPROJ'),false,combined);
      gl.uniform4fv(uniform('CURRENT_COLOR'),f.color);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(f.vertices.flat()),gl.STREAM_DRAW);
      gl.clearColor(...clear.map(v=>v/255));gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES,0,f.vertices.length);
      gl.readPixels(0,0,width,width,gl.RGBA,gl.UNSIGNED_BYTE,bytes);
      const error=gl.getError();if(error) throw Error(f.name+': GL error '+error);
      let checked=0,expectedInk=0,actualInk=0,mismatches=0;
      const samples=[];
      function check(x,y,probe=false) {
        const want=expected(f,x,y,probe);if(!want)return;
        ++checked;if(want.visible)++expectedInk;
        const actual=Array.from(bytes.slice((y*width+x)*4,(y*width+x)*4+4));
        if(actual.some((v,i)=>Math.abs(v-clear[i])>1))++actualInk;
        if(want.rgba.some((v,i)=>Math.abs(v-actual[i])>1)) {
          ++mismatches;if(samples.length<6)samples.push({x,y,probe,expected:want.rgba,actual});
        }
      }
      for(let y=0;y<width;++y)for(let x=0;x<width;++x)check(x,y);
      for(const [x,y] of f.probes||[])check(x,y,true);
      pixelChecks+=checked;
      measurements.push({name:f.name,pixels:checked,expected_ink:expectedInk,actual_ink:actualInk,
        mismatches,probes:(f.probes||[]).length});
      if(mismatches)failures.push({name:f.name,mismatches,samples});
      if(!expectedInk && f.kind==='grid' && f.distance< -10)
        throw Error('Vacuous grid fixture: '+f.name);
      if(!expectedInk && f.kind==='outline' && Math.max(...f.clips)<0)
        throw Error('Vacuous outline fixture: '+f.name);
    }
    results.push({name:c.name,subpixel_bits:gl.getParameter(gl.SUBPIXEL_BITS),
      checks:c.fixtures.length,pixel_checks:pixelChecks,failures,measurements});
    console.log(JSON.stringify({program:c.name,fixtures:c.fixtures.length,failures:failures.length}));
    gl.getExtension('WEBGL_lose_context').loseContext();
  }
  return results;
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--filter', help='Run only fixture names containing this text')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright

    cases = []
    samples = fixtures()
    if args.filter:
        samples = [sample for sample in samples if args.filter in sample['name']]
        if not samples:
            parser.error('--filter matched no fixtures')
    for version in (100, 300):
        for flags in ((), ('BLEND', 'ALPHA_TEST'), ('SEASONS', 'ALPHA_TEST'), ('FOG', 'BLEND')):
            cases.append(dict(name=str(version)+'/'+','.join(flags), version=version,
                              v=shader_source(SHADERS/'modern_projection_biome_blocks.vertex',
                                              args.headers, version, flags),
                              f=shader_source(SHADERS/'modern_projection_biome_blocks.fragment',
                                              args.headers, version, flags), fixtures=samples))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                                            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page()
            page.on('console', lambda message: print(message.text, flush=True)
                    if message.type == 'log' else None)
            results = page.evaluate(RENDER, cases)
        finally:
            browser.close()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(results, indent=2), encoding='utf8')
    failures = [dict(program=result['name'], **failure)
                for result in results for failure in result['failures']]
    print(json.dumps(dict(programs=len(results), fixtures=sum(r['checks'] for r in results),
                          pixel_checks=sum(r['pixel_checks'] for r in results), failures=len(failures))))
    if failures:
        print(json.dumps(failures[:10], indent=2))
        raise SystemExit(1)


if __name__ == '__main__':
    main()

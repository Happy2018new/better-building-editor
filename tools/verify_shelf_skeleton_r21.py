"""Verify the isolated shelf mesh and compile/render its real shader pairs."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from verify_biome_shader import shader_source
from verify_item_icon_shaders import COMPILE


ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_shelf_skeleton_r21_'
NORMALS = {'north': (0, 0, -1), 'east': (1, 0, 0), 'south': (0, 0, 1),
           'west': (-1, 0, 0), 'up': (0, 1, 0), 'down': (0, -1, 0)}


def cross(left, right):
    return [left[1]*right[2]-left[2]*right[1], left[2]*right[0]-left[0]*right[2],
            left[0]*right[1]-left[1]*right[0]]


def verify_mesh(data):
    """Check actual indexed triangles, including each slot's decoded bounds."""
    failures, slots = [], {slot: [] for slot in range(4)}
    mesh = data['mesh'][0]
    for index, vertex in enumerate(mesh['vertices']):
        point, normal, uv = vertex['pos'], vertex['normal'], vertex['uvcoord']
        slot = int(math.floor(point[2]/4.))
        if slot not in slots:
            failures.append('invalid slot at vertex '+str(index))
            continue
        decoded = [point[0]+.5, point[1], point[2]-slot*4.-1.+.5]
        slots[slot].append(decoded)
        if tuple(normal) not in NORMALS.values():
            failures.append('non-axis normal at vertex '+str(index))
        if len(uv) != 2 or any(not 0. <= value <= 1. for value in uv):
            failures.append('invalid UV at vertex '+str(index))
        if vertex['weight'] != [['root', 1.]]:
            failures.append('invalid root ownership at vertex '+str(index))
    for number, triangle in enumerate(mesh['indices']):
        vertices = [mesh['vertices'][index] for index in triangle]
        a, b, c = [vertex['pos'] for vertex in vertices]
        geometric = cross([b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)])
        if sum(value*value for value in geometric) <= 0.:
            failures.append('degenerate triangle '+str(number))
        if any(sum(geometric[i]*vertex['normal'][i] for i in range(3)) <= 0. for vertex in vertices):
            failures.append('normal opposes indexed winding at triangle '+str(number))
    bounds = {}
    for slot, points in slots.items():
        if not points:
            failures.append('missing slot '+str(slot))
            continue
        bounds[str(slot)] = [[min(point[axis] for point in points) for axis in range(3)],
                             [max(point[axis] for point in points) for axis in range(3)]]
        if bounds[str(slot)] != [[0., 0., 11./16.], [1., 1., 1.]]:
            failures.append('shelf dimension drift in slot '+str(slot))
    return {'passed': not failures, 'vertices': len(mesh['vertices']),
            'triangles': len(mesh['indices']), 'decoded_bounds': bounds, 'failures': failures}


PIXELS = r'''cases => {
 const results=[],identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
 for(const c of cases){
  const canvas=document.createElement('canvas');canvas.width=canvas.height=4;
  const gl=canvas.getContext(c.version===300?'webgl2':'webgl',{antialias:false,premultipliedAlpha:false});
  const result={name:c.name,passed:false,checks:[],failures:[]};
  if(!gl){result.failures.push('No WebGL context');results.push(result);continue;}
  try{
   function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
   const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,c.vertex));
   gl.attachShader(p,shader(gl.FRAGMENT_SHADER,c.fragment));gl.linkProgram(p);
   if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
   function matrix(name,value){const location=gl.getUniformLocation(p,name);if(location!==null)gl.uniformMatrix4fv(location,false,value);}
   function vec(name,value){const location=gl.getUniformLocation(p,name);if(location!==null)gl.uniform4fv(location,value);}
   function attr(name,size,values){const location=gl.getAttribLocation(p,name);if(location<0)return;
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);}
   matrix('WORLD',identity);matrix('WORLDVIEW',identity);matrix('PROJ',identity);
   matrix('WORLDVIEWPROJ',c.world?[2,0,0,0,0,2,0,0,0,0,0,0,1,1,0,1]:[2,0,0,0,0,0,0,0,0,-2,0,0,-1,1,0,1]);
   vec('CURRENT_COLOR',[1,1,1,1]);vec('TILE_LIGHT_COLOR',[.25,.5,.75,1]);
   vec('EXTRA_VECTOR3',[0,0,0,0]);
   const texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
   gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
   gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([160,80,40,255]));
   const sampler=gl.getUniformLocation(p,'TEXTURE_0');if(sampler!==null)gl.uniform1i(sampler,0);
   attr('POSITION',3,c.vertices.flatMap(row=>row.pos));attr('NORMAL',3,c.vertices.flatMap(row=>row.normal));
   attr('TEXCOORD_0',2,c.vertices.flatMap(row=>row.uvcoord));
   gl.disable(gl.DITHER);gl.disable(gl.BLEND);gl.disable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.viewport(0,0,4,4);
   for(const row of c.fixtures){
    vec('EXTRA_VECTOR1',[row.code,0,0,0]);vec('EXTRA_VECTOR2',[row.mode,0,0,0]);
    vec('EXTRA_VECTOR4',[row.tag,1,16777215,row.opacity]);
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,c.vertices.length);
    const pixel=new Uint8Array(4);gl.readPixels(2,2,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
    const actual=Array.from(pixel),passed=row.expected.every((value,index)=>Math.abs(value-actual[index])<1.6);
    const check={name:row.name,expected:row.expected,actual,passed};result.checks.push(check);if(!passed)result.failures.push(check);
   }
   result.passed=result.failures.length===0;
  }catch(error){result.failures.push(String(error));}
  results.push(result);
 }
 return results;
}'''

FUNCTION_PIXELS = r'''payload => {
 const results=[];
 for(const version of [100,300]){
  const canvas=document.createElement('canvas');canvas.width=payload.rows.length;canvas.height=1;
  const gl=canvas.getContext(version===300?'webgl2':'webgl',{antialias:false});
  const result={version,passed:false,checks:[],failures:[]};
  if(!gl){result.failures.push('No WebGL context');results.push(result);continue;}
  try{
   const header=(version===300?'#version 300 es\n':'')+'precision highp float;\n';
   const vertex=header+(version===300?'in':'attribute')+' vec3 aNormal;\n'+(version===300?'in':'attribute')+
    ' vec3 aCodes;\n'+(version===300?'out':'varying')+' vec4 resultValue;\n'+payload.functions+
    'void main(){vec3 N=shelfTurn(aNormal,aCodes.x);resultValue=vec4(N*0.5+0.5,shelfAxisIntensity(N,aCodes.y));'+
    'gl_PointSize=1.0;gl_Position=vec4((aCodes.z+0.5)/'+payload.rows.length+'.0*2.0-1.0,0.0,0.0,1.0);}';
   const fragment=header+(version===300?'in vec4 resultValue;out vec4 color;':'varying vec4 resultValue;')+
    'void main(){'+(version===300?'color':'gl_FragColor')+'=resultValue;}';
   function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
   const p=gl.createProgram();gl.attachShader(p,shader(gl.VERTEX_SHADER,vertex));gl.attachShader(p,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(p);
   if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));gl.useProgram(p);
   function attr(name,size,values){const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);const location=gl.getAttribLocation(p,name);
    gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);}
   attr('aNormal',3,payload.rows.flatMap(row=>row.normal));attr('aCodes',3,payload.rows.flatMap((row,index)=>[row.angle,row.light_direction,index]));
   gl.disable(gl.DITHER);gl.viewport(0,0,canvas.width,1);gl.drawArrays(gl.POINTS,0,canvas.width);
   const pixels=new Uint8Array(canvas.width*4);gl.readPixels(0,0,canvas.width,1,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   for(let index=0;index<payload.rows.length;index++){
    const row=payload.rows[index],actual=Array.from(pixels.slice(index*4,index*4+4));
    const passed=row.expected.every((value,channel)=>Math.abs(value*255-actual[channel])<1.6);
    const check={name:row.name,expected:row.expected,actual,passed};result.checks.push(check);if(!passed)result.failures.push(check);
   }
   result.passed=result.failures.length===0;
  }catch(error){result.failures.push(String(error));}
  results.push(result);
 }
 return results;
}'''


def function_rows():
    rows = []
    horizontal = ('north', 'east', 'south', 'west')
    for rotation in range(4):
        for name, normal in NORMALS.items():
            oriented = NORMALS[horizontal[(horizontal.index(name)+rotation) % 4]] if name in horizontal else normal
            for light in (-1., 0., 1.):
                if oriented[1]:
                    intensity = 1. if oriented[1]*light > 0. else .45 if oriented[1]*light < 0. else .725
                else:
                    intensity = .625 if oriented[0] else .825
                rows.append({'name': '%s/turn%d/light%s' % (name, rotation, light),
                    'normal': list(normal), 'angle': rotation*math.pi/2., 'light_direction': light,
                    'expected': [value*.5+.5 for value in oriented]+[intensity]})
    return rows


def fixtures(flags):
    rgb = [160*.25*.825, 80*.5*.825, 40*.75*.825]
    values = [rgb, [127.5, 127.5, 0.], [127.5, 127.5, 0.], [255*.825]*3,
              [255*.25, 255*.5, 255*.75], [255., 0., 255.], [160., 80., 40.],
              [255.*('FANCY' in flags), 255.*('RNGL_UNLIT' in flags), 255.*('RNGL_LIGHT' in flags)]]
    rows = [{'name': 'mode'+str(mode), 'mode': mode, 'code': 85., 'tag': 39686., 'opacity': 1.,
             'expected': value+[255.]} for mode, value in enumerate(values)]
    for name, field, value in (('hidden_slot', 'code', 21.), ('invalid_tag', 'tag', 0.), ('zero_opacity', 'opacity', 0.)):
        row = dict(rows[5], name=name, expected=[0.]*4)
        row[field] = value
        rows.append(row)
    rows.append(dict(rows[5], name='half_opacity', opacity=.5, expected=[255., 0., 255., 127.5]))
    return rows


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh shelf skeleton report')
    contract = json.loads((args.project/'contract.json').read_bytes())
    hashes = {path: hashlib.sha256((args.project/path).read_bytes()).hexdigest() == digest
              for path, digest in contract['output_sha256'].items()}
    meshes = {path: verify_mesh(json.loads((args.project/path).read_bytes()))
              for path in hashes if path.endswith('_mesh.json')}
    first_mesh = json.loads((args.project/next(iter(meshes))).read_bytes())['mesh'][0]
    quad_start = next(index for index, vertex in enumerate(first_mesh['vertices'])
                      if vertex['normal'] == [0, 0, -1] and vertex['pos'][1] == .75)
    vertices = [first_mesh['vertices'][quad_start+offset] for offset in (0, 1, 2, 0, 2, 3)]
    directory = args.project/'resource_pack/shaders/glsl'
    cases, pixels = [], []
    for world in (False, True):
        route = '_world' if world else ''
        vertex = directory/(PREFIX+'body'+route+'.vertex')
        fragment = directory/(PREFIX+'body.fragment')
        for version in (100, 300):
            for flags in (('BLEND',), ('BLEND', 'FANCY'), ('BLEND', 'RNGL_UNLIT'), ('BLEND', 'RNGL_LIGHT')):
                row = {'name': '%s/%d/%s' % (route or 'ui', version, ','.join(flags)), 'version': version,
                       'vertex': shader_source(vertex, args.headers, version, flags),
                       'fragment': shader_source(fragment, args.headers, version, flags)}
                cases.append(row)
                pixels.append(dict(row, world=world, vertices=vertices, fixtures=fixtures(flags)))
            if world and version == 300:
                for flags in (('BLEND', 'USE_SKINNING', 'NETEASE_SKINNING'),
                              ('BLEND', 'USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE')):
                    cases.append({'name': route+'/300/'+','.join(flags), 'version': version,
                        'vertex': shader_source(vertex, args.headers, version, flags),
                        'fragment': shader_source(fragment, args.headers, version, flags)})
    source = (directory/(PREFIX+'body.vertex')).read_text(encoding='ascii')
    functions = source[source.index('vec3 shelfTurn('):source.index('void main() {')]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page()
            compiled = page.evaluate(COMPILE, cases)
            rendered = page.evaluate(PIXELS, pixels)
            axes = page.evaluate(FUNCTION_PIXELS, {'functions': functions, 'rows': function_rows()})
        finally:
            browser.close()
    passed = all(hashes.values()) and all(row['passed'] for row in meshes.values()) and all(
        row['compiled'] and row['linked'] for row in compiled) and all(row['passed'] for row in rendered+axes)
    report = {'schema_version': 1, 'passed': passed, 'production_qualified': False,
        'native_pixels_qualified': False, 'manifest': hashes, 'mesh_checks': meshes,
        'programs': compiled, 'actual_pair_synthetic_pixels': rendered, 'axis_function_pixels': axes,
        'scope': 'Actual target headers and real shader pairs; synthetic mesh input only. No game capture.',
        'skinning_scope': 'GLES3 compile/link only; native bone matrices, instance depth and lifecycle remain open'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'passed': passed, 'programs': len(compiled),
        'pair_pixel_checks': sum(len(row['checks']) for row in rendered),
        'axis_pixel_checks': sum(len(row['checks']) for row in axes),
        'failures': [row for row in rendered+axes if not row['passed']]}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

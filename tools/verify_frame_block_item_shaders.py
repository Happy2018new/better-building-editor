"""Compile frame-block material pairs with actual target-engine GLES headers."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from verify_biome_shader import shader_source
from verify_item_icon_shaders import COMPILE

ROOT = Path(__file__).resolve().parents[1]
UV_CHECK = '''payload => {
 const results=[];
 for(const version of [100,300]) {
  const canvas=document.createElement('canvas');
  canvas.width=payload.vertices.length;canvas.height=1;
  const gl=canvas.getContext(version===300?'webgl2':'webgl');
  if(!gl) {results.push({version,passed:false,error:'No WebGL context'});continue;}
  const pre=version===300?'#version 300 es\\n':'';
  const attribute=version===300?'in':'attribute', varying=version===300?'out':'varying';
  const vertex=pre+'precision highp float;\\n'+attribute+' vec3 aPosition;\\n'+attribute+
   ' vec3 aNormal;\\n'+attribute+' float aIndex;\\n'+varying+' vec2 faceUv;\\n'+payload.function+
   'void main(){faceUv=blockFaceUv(aPosition,aNormal);gl_PointSize=1.0;gl_Position=vec4((aIndex+0.5)/'+
   payload.vertices.length+'.0*2.0-1.0,0.0,0.0,1.0);}';
  const fragment=pre+'precision highp float;\\n'+(version===300?'in vec2 faceUv;out vec4 color;':'varying vec2 faceUv;')+
   'void main(){'+(version===300?'color':'gl_FragColor')+'=vec4(faceUv,0.0,1.0);}';
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  try {
   const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));
   gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
   if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
   gl.useProgram(program);
   function bind(name,size,values){const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);
    const location=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);}
   bind('aPosition',3,payload.vertices.flatMap(row=>row.slice(0,3)));
   bind('aNormal',3,payload.vertices.flatMap(row=>row.slice(3,6)));
   bind('aIndex',1,payload.vertices.map((row,index)=>index));
   gl.viewport(0,0,canvas.width,1);gl.drawArrays(gl.POINTS,0,canvas.width);
   const pixels=new Uint8Array(canvas.width*4);gl.readPixels(0,0,canvas.width,1,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   const failures=[];
   for(let i=0;i<canvas.width;i++) {
    const expected=payload.expected[i];const actual=Array.from(pixels.slice(i*4,i*4+4));
    if(Math.abs(actual[0]-expected[0]*255)>1||Math.abs(actual[1]-expected[1]*255)>1||actual[3]!==255)
     failures.push({vertex:i,expected,actual});
   }
   results.push({version,passed:failures.length===0,vertices:canvas.width,failures});
  } catch(error) {results.push({version,passed:false,error:String(error)});}
 }
 return results;
}'''
POSE_CHECK = r'''payload => {
 const results=[];
 for(const version of [100,300]) {
  const canvas=document.createElement('canvas');canvas.width=payload.rows.length;canvas.height=1;
  const gl=canvas.getContext(version===300?'webgl2':'webgl');
  if(!gl){results.push({version,passed:false,error:'No WebGL context'});continue;}
  const pre=version===300?'#version 300 es\n':'';
  const attribute=version===300?'in':'attribute',varying=version===300?'out':'varying';
  const vertex=pre+'precision highp float;\n'+attribute+' vec3 aPoint;\n'+attribute+' vec2 aPose;\n'+
   attribute+' float aIndex;\n'+varying+' vec3 projected;\n'+payload.function+
   'void main(){projected=orientItem(aPoint,aPose.x,aPose.y,0.0)*0.5+0.5;gl_PointSize=1.0;'+
   'gl_Position=vec4((aIndex+0.5)/'+payload.rows.length+'.0*2.0-1.0,0.0,0.0,1.0);}';
  const fragment=pre+'precision highp float;\n'+(version===300?'in vec3 projected;out vec4 color;':'varying vec3 projected;')+
   'void main(){'+(version===300?'color':'gl_FragColor')+'=vec4(projected,1.0);}';
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  try {
   const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vertex));
   gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
   if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
   function bind(name,size,values){const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);const location=gl.getAttribLocation(program,name);
    gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);}
   bind('aPoint',3,payload.rows.flatMap(row=>row.slice(0,3)));
   bind('aPose',2,payload.rows.flatMap(row=>row.slice(3,5)));
   bind('aIndex',1,payload.rows.map((row,index)=>index));
   gl.viewport(0,0,canvas.width,1);gl.drawArrays(gl.POINTS,0,canvas.width);
   const pixels=new Uint8Array(canvas.width*4);gl.readPixels(0,0,canvas.width,1,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
   const failures=[];
   for(let i=0;i<canvas.width;i++) {
    const actual=Array.from(pixels.slice(i*4,i*4+4)),expected=payload.expected[i].map(value=>(value*0.5+0.5)*255);
    if(expected.some((value,index)=>Math.abs(value-actual[index])>1.1)||actual[3]!==255)
     failures.push({row:i,expected,actual});
   }
   results.push({version,passed:failures.length===0,samples:canvas.width,failures:failures.slice(0,20)});
  }catch(error){results.push({version,passed:false,error:String(error)});}
 }
 return results;
}'''


def pose_samples(vertices, normals=False):
    """Independent face bases plus clockwise in-plane rotation for all 48 poses."""
    rows, expected = [], []
    for face in range(6):
        for step in range(8):
            angle = step * math.pi / 4.
            cosine, sine = math.cos(angle), math.sin(angle)
            for vertex in vertices:
                point = vertex['normal'] if normals else [vertex['pos'][0] % 2. - .5,
                    vertex['pos'][1] - .5, vertex['pos'][2]]
                x, y, z = point
                sign = -1. if face < 2 else 1.
                u, v = sign * (cosine * x + sine * y), sign * (-sine * x + cosine * y)
                basis = ((-u, z, -v), (-u, -z, v), (-u, v, z),
                         (u, v, -z), (z, v, u), (-z, v, -u))[face]
                rows.append(list(point) + [face, angle])
                expected.append(list(basis))
    return rows, expected


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=ROOT,
                        help='Frozen diagnostic resources, defaults to this project')
    parser.add_argument('--shader-prefix', default='modern_projection_frame_block')
    parser.add_argument('--materials', nargs='+', choices=('opaque', 'cutout', 'translucent'),
                        default=('opaque', 'cutout', 'translucent'))
    parser.add_argument('--mesh-directory', default='resource_pack/models/modern_projection/frame_block_items')
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh frame-block shader report')
    shaders = args.project / 'resource_pack/shaders/glsl'
    cases, hashes = [], {}
    for material in args.materials:
        for route in ('', '_world'):
            vertex = shaders / (args.shader_prefix + route + '.vertex')
            fragment = shaders / (args.shader_prefix + '_' + material + '.fragment')
            for path in (vertex, fragment):
                hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            for version in (100, 300):
                flags_rows = [('BLEND',), ('BLEND', 'USE_OVERLAY')]
                # The installed skeletal header uses GLES3 non-square matrices.
                if route and version == 300:
                    flags_rows.extend((('BLEND', 'USE_SKINNING', 'NETEASE_SKINNING'),
                                       ('BLEND', 'USE_SKINNING', 'NETEASE_SKINNING', 'USE_INSTANCE')))
                for flags in flags_rows:
                    cases.append({'name': '%s%s/%s/%d' % (material, route, ','.join(flags), version),
                        'version': version, 'vertex': shader_source(vertex, args.headers, version, flags),
                        'fragment': shader_source(fragment, args.headers, version, flags)})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            page = browser.new_page()
            results = page.evaluate(COMPILE, cases)
            source = (shaders / (args.shader_prefix + '.vertex')).read_text(encoding='ascii')
            function = source[source.index('vec2 blockFaceUv('):source.index('void main() {')]
            mesh_path = next((args.project / args.mesh_directory).glob('*_mesh.json'))
            vertices = json.loads(mesh_path.read_bytes())['mesh'][0]['vertices']
            uv_results = page.evaluate(UV_CHECK, {'function': function,
                'vertices': [row['pos'] + row['normal'] for row in vertices],
                'expected': [[0, 0], [1, 0], [1, 1], [0, 1]] * 24})
            orientation = source[source.index('vec3 orientItem('):source.index('float frameIntensity(')]
            pose_results = {}
            for normals in (False, True):
                rows, expected = pose_samples(vertices, normals)
                pose_results['normals' if normals else 'positions'] = page.evaluate(POSE_CHECK,
                    {'function': orientation, 'rows': rows, 'expected': expected})
        finally:
            browser.close()
    report = {'schema': 1, 'shader_sha256': hashes, 'results': results,
              'glint_face_uv': uv_results,
              'pose_48': pose_results,
              'skinning_scope': 'GLES3 skinning and instance paths only; installed uniformAnimationConstants.h uses mat3x4 and gl_InstanceID unsupported by GLES2',
              'passed': all(row['compiled'] and row['linked'] for row in results) and
                        all(row['passed'] for row in uv_results) and
                        all(row['passed'] for rows in pose_results.values() for row in rows),
              'production_qualified': False, 'scope': 'Offline compilation only; native pixels remain unaccepted'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': report['passed'], 'cases': len(results), 'glint_face_uv': uv_results,
                      'pose_48': pose_results,
                      'failures': [row for row in results if not row['compiled'] or not row['linked']]}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

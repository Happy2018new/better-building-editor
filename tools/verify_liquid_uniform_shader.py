"""Compile uniform carriers against installed headers and verify host GLES samples."""
import argparse
import hashlib
import json
from pathlib import Path

from verify_biome_shader import shader_source

RENDER = '''cases => cases.map(item => {
  const canvas=document.createElement('canvas'); canvas.width=1; canvas.height=1;
  const gl=canvas.getContext(item.version===100?'webgl':'webgl2',{antialias:false});
  if (!gl) return {name:item.name,passed:false,error:'GL context unavailable'};
  function compile(type,source) {
    const shader=gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
    if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
    return shader;
  }
  try {
    const program=gl.createProgram();
    gl.attachShader(program,compile(gl.VERTEX_SHADER,item.vertex));
    gl.attachShader(program,compile(gl.FRAGMENT_SHADER,item.fragment)); gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
    gl.useProgram(program); gl.viewport(0,0,1,1);
    const matrix=new Float32Array(16); matrix[15]=1;
    gl.uniformMatrix4fv(gl.getUniformLocation(program,'WORLDVIEWPROJ'),false,matrix);
    const position=gl.getAttribLocation(program,'POSITION'); gl.disableVertexAttribArray(position);
    const failures=[];
    for (const fixture of item.fixtures) {
      for (let group=1;group<=4;group++) gl.uniform4fv(gl.getUniformLocation(program,(item.uniformPrefix||'EXTRA_ACTOR_UNIFORM')+group),fixture.uniforms[group-1]);
      gl.vertexAttrib4fv(position,fixture.position);
      gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.POINTS,0,1);
      const actual=new Uint8Array(4); gl.readPixels(0,0,1,1,gl.RGBA,gl.UNSIGNED_BYTE,actual);
      if (actual.some((value,index)=>Math.abs(value-fixture.expected[index])>1)) failures.push({name:fixture.name,actual:[...actual],expected:fixture.expected});
    }
    return {name:item.name,linked:true,checks:item.fixtures.length,failures,passed:failures.length===0};
  } catch(error) { return {name:item.name,linked:false,passed:false,error:String(error)}; }
  finally { gl.getExtension('WEBGL_lose_context').loseContext(); }
})'''


def fixtures():
    from probe_liquid_uniform_transport import HEIGHT_CODES, uniforms
    rows=[]
    for slot,heights in enumerate(HEIGHT_CODES):
        for kind in range(7):
            for u,v in ((0,0),(1,0),(1,1),(0,1)):
                for mode in (2,5):
                    expected=list(heights[:3]) if mode==2 else [heights[3],slot*85,kind/6.*255]
                    rows.append({'name':'%s/%s/%s/%s' % (slot,kind,(u,v),mode),
                                 'position':[slot+u*.5-.25,kind,v*.5-.25,1.],
                                 'uniforms':[list(value) for group,value in uniforms(mode)],
                                 'expected':expected+[255]})
    return rows


def direct_fixtures():
    from probe_liquid_uniform_transport import HEIGHT_CODES, uniforms
    return [{'name':'direct/%d' % slot,'position':[slot*16.,0.,0.,1.],
             'uniforms':[list(value) for group,value in uniforms(2)],
             'expected':list(heights[:3])+[255]} for slot,heights in enumerate(HEIGHT_CODES)]


def skeleton_fixtures():
    from probe_liquid_uniform_transport import HEIGHT_CODES, uniforms
    rows=[]
    for mode in (2,5,6,7):
        for slot,heights in enumerate(HEIGHT_CODES):
            values=[list(value) for group,value in uniforms(mode)]
            expected=list(heights[:3]) if mode==2 else [heights[3],slot*85,(0,5,42,63)[slot]*4]
            if mode in (6,7):
                values[3]=[39686.,.5,float(0x123456),float(mode)]
                expected=[18,52,86 if mode==6 else 128]
            rows.append({'name':'skeleton/%d/%d' % (mode,slot),
                         'position':[slot*1.1-1.65,0.,0.,1.],
                         'uniforms':values,'expected':expected+[255]})
    for slot in range(4):
        values=[list(value) for group,value in uniforms(2)]
        values[3][0]=0.
        rows.append({'name':'skeleton/badtag/%d' % slot,'position':[slot*1.1-1.65,0.,0.,1.],
                     'uniforms':values,'expected':[255,0,255,255]})
    return rows


def main():
    from playwright.sync_api import sync_playwright
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overlay',required=True,type=Path)
    parser.add_argument('--headers',required=True,type=Path)
    parser.add_argument('--browser')
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--direct-entity',action='store_true')
    parser.add_argument('--skeleton',action='store_true')
    args=parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh report')
    if args.direct_entity and args.skeleton:
        parser.error('Choose one diagnostic model path')
    shaders=args.overlay/'resource_pack/shaders/glsl'
    prefix='liquid_skeleton_r9' if args.skeleton else ('liquid_uniform_direct_r9' if args.direct_entity else 'liquid_uniform_r9')
    paths=[shaders/(prefix+'.'+extension) for extension in ('vertex','fragment')]
    cases=[]
    for version in (100,300):
        for flags in (('BLEND',),('BLEND','FOG')):
            cases.append({'name':'%s/%s' % (version,flags),'version':version,
                          'vertex':shader_source(paths[0],args.headers,version,flags),
                          'fragment':shader_source(paths[1],args.headers,version,flags),
                          'uniformPrefix':'EXTRA_VECTOR' if args.skeleton else 'EXTRA_ACTOR_UNIFORM',
                          'fixtures':skeleton_fixtures() if args.skeleton else (direct_fixtures() if args.direct_entity else fixtures())})
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=args.browser,headless=True,
            args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        try:
            results=browser.new_page().evaluate(RENDER,cases)
        finally:
            browser.close()
    report={'schema':1,'results':results,'checks':sum(row.get('checks',0) for row in results),
            'direct_entity_diagnostic':args.direct_entity,
            'skeleton_diagnostic':args.skeleton,
            'passed':all(row.get('passed',False) for row in results),
            'shader_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
            'scope':'Host GLES 2/3 and synthetic attributes; not native rendering acceptance',
            'native_geometry_accepted':False,'accuracy_accepted':False,'production_memory_accepted':False}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='ascii')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

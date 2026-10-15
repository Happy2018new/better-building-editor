"""Pair native/selector GLES programs and verify RGB stripes and native alpha."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_shelf_native_routes_r21 import ROUTES, fragment_path, verify
from verify_biome_shader import shader_source


RENDER = r'''pairs => pairs.map(c => {
 const canvas=document.createElement('canvas');canvas.width=64;canvas.height=4;
 const gl=canvas.getContext(c.version===300?'webgl2':'webgl',{antialias:false,premultipliedAlpha:false});
 const result={name:c.name,programs:[],checks:[],passed:false};
 if(!gl){result.error='No GLES context';return result;}
 const programs=[];
 for(const variant of ['native','selector']){
  const p=gl.createProgram(),errors=[];
  for(const [stage,type,source] of [['vertex',gl.VERTEX_SHADER,c.vertex],['fragment',gl.FRAGMENT_SHADER,c[variant]]]){
   const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
   if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))errors.push({stage,log:gl.getShaderInfoLog(s)});
   gl.attachShader(p,s);
  }
  gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))errors.push({stage:'link',log:gl.getProgramInfoLog(p)});
  result.programs.push({variant,errors,passed:errors.length===0});programs.push(p);
 }
 if(result.programs.some(row=>!row.passed)){
  result.inherited_native_failure=c.allow_native_skinning_failure && !result.programs[0].passed &&
   JSON.stringify(result.programs[0].errors)===JSON.stringify(result.programs[1].errors);
  gl.getExtension('WEBGL_lose_context')?.loseContext();return result;
 }
 if(!c.compile_only){
  const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
  for(const fixture of [{name:'opaque',alpha:255,vertexAlpha:1},{name:'half_texel',alpha:128,vertexAlpha:1},
                        {name:'half_vertex',alpha:255,vertexAlpha:.5},{name:'zero_texel',alpha:0,vertexAlpha:1}]){
   const outputs=[];
   for(const p of programs){
    gl.useProgram(p);
    const uniform=name=>gl.getUniformLocation(p,name);
    for(const name of ['WORLD','WORLDVIEWPROJ','WORLDVIEW','PROJ','BONE'])gl.uniformMatrix4fv(uniform(name),false,identity);
    gl.uniform4f(uniform('TILE_LIGHT_COLOR'),1,1,1,1);gl.uniform4f(uniform('CURRENT_COLOR'),1,1,1,1);
    gl.uniform4f(uniform('OVERLAY_COLOR'),0,0,0,0);gl.uniform4f(uniform('FOG_COLOR'),0,0,0,0);
    gl.uniform4f(uniform('CHUNK_ORIGIN_AND_SCALE'),0,0,0,1);gl.uniform4f(uniform('HIDE_COLOR'),0,1,0,0);
    gl.uniform4f(uniform('TEXTURE_DIMENSIONS'),1,1,1,1);
    gl.uniform2f(uniform('FOG_CONTROL'),10,20);gl.uniform1f(uniform('RENDER_DISTANCE'),100);
    gl.uniform1f(uniform('FAR_CHUNKS_DISTANCE'),100);gl.uniform1f(uniform('RENDER_CHUNK_FOG_ALPHA'),0);
    function constant(name,value){const loc=gl.getAttribLocation(p,name);if(loc>=0){gl.disableVertexAttribArray(loc);gl.vertexAttrib4fv(loc,value);}}
    const pos=gl.getAttribLocation(p,'POSITION');
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,1,3,-1,0,1,-1,3,0,1]),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,4,gl.FLOAT,false,0,0);
    constant('NORMAL',[0,1,0,0]);constant('COLOR',[1,1,1,fixture.vertexAlpha]);
    constant('TEXCOORD_0',[.5,.5,0,0]);constant('TEXCOORD_1',[.5,.5,0,0]);
    for(let unit=0;unit<3;unit++){
     gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
     gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
     const texel=unit===0?[180,120,60,fixture.alpha]:unit===1&&c.family==='entity'?[0,0,0,0]:[255,255,255,255];
     gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(texel));gl.uniform1i(uniform('TEXTURE_'+unit),unit);
    }
    gl.disable(gl.BLEND);gl.disable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.disable(gl.DITHER);
    gl.viewport(0,0,64,4);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,3);
    const pixels=[];
    for(let strip=0;strip<4;strip++){const pixel=new Uint8Array(4);gl.readPixels(strip*16+8,1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);pixels.push(Array.from(pixel));}
    outputs.push(pixels);
   }
   const bypass=c.flags.includes('BYPASS_PIXEL_SHADER'),discard=c.flags.includes('ALPHA_TEST')&&fixture.alpha===0;
   for(let strip=0;strip<4;strip++){
    const baseline=outputs[0][strip],actual=outputs[1][strip];
    const expected=strip%2||bypass||discard?baseline:[...c.marker.map(v=>v*255),baseline[3]];
    const error=gl.getError();
    const passed=!error&&expected.every((value,index)=>Math.abs(value-actual[index])<=2);
    result.checks.push({fixture:fixture.name,strip,baseline,expected,actual,error,passed});
   }
  }
 }
 result.passed=result.checks.every(row=>row.passed);
 gl.getExtension('WEBGL_lose_context')?.loseContext();return result;
})'''


def variants(family):
    if family == 'entity':
        base = ('USE_OVERLAY',)
        extras = ((), ('FANCY',), ('FANCY', 'ALPHA_TEST'), ('FANCY', 'RNGL_UNLIT'),
                  ('FANCY', 'RNGL_LIGHT'), ('FANCY', 'ALWAYS_LIT'), ('FANCY', 'USE_SKINNING'))
    else:
        base = ('LOW_PRECISION', 'TEXEL_AA', 'ATLAS_TEXTURE')
        extras = ((), ('FOG',), ('FOG', 'FANCY'), ('FOG', 'ALWAYS_LIT'), ('FOG', 'ALPHA_TEST'),
            ('FOG', 'ALPHA_TEST', 'ALPHA_TO_COVERAGE'), ('FOG', 'SEASONS'),
            ('FOG', 'SEASONS', 'ALPHA_TEST'), ('FOG', 'SEASONS', 'SEASONS_FAR'),
            ('FOG', 'BLEND', 'FANCY'), ('FOG', 'ALLOW_FADE'), ('FOG', 'BYPASS_PIXEL_SHADER'),
            ('FOG', 'AS_ENTITY_RENDERER'))
    return [base+extra for extra in extras]


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('Choose a fresh compiler report')
    frozen = verify(args.freeze)
    project = Path(frozen['project'])
    pairs = []
    for root, (family, variable, marker) in ROUTES.items():
        for version in (100, 300):
            for flags in variants(family):
                native = shader_source(args.headers/(family+'.fragment'), args.headers, version, flags)
                boundary = native.index('\n')+1
                native = native[:boundary]+'precision highp float;\nprecision highp int;\n'+native[boundary:]
                pairs.append({'name': root+'/'+str(version)+'/'+','.join(flags),
                    'family': family, 'version': version, 'flags': flags, 'marker': marker,
                    'vertex': shader_source(args.headers/(family+'.vertex'), args.headers, version, flags),
                    'native': native, 'selector': shader_source(project/fragment_path(root), args.headers, version, flags),
                    'compile_only': 'USE_SKINNING' in flags,
                    'allow_native_skinning_failure': family == 'entity' and version == 100 and 'USE_SKINNING' in flags})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        try:
            results = browser.new_page().evaluate(RENDER, pairs)
        finally:
            browser.close()
    passed = all(row['passed'] or row.get('inherited_native_failure') for row in results)
    report = {'schema_version': 1, 'passed': passed, 'native_route_qualified': False,
        'frozen_manifest_sha256': hashlib.sha256(args.freeze.read_bytes()).hexdigest(),
        'expanded_source_sha256': {row['name']: {stage: hashlib.sha256(row[stage].encode('utf8')).hexdigest()
                                    for stage in ('vertex', 'native', 'selector')} for row in pairs},
        'pairs': len(results), 'programs': sum(len(row['programs']) for row in results),
        'pixel_checks': sum(len(row['checks']) for row in results),
        'inherited_native_failures': [row['name'] for row in results if row.get('inherited_native_failure')],
        'results': results, 'scope': 'Synthetic GLES native/selector pairs; native shelf routing remains unproven.'}
    verify(args.freeze)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({key: report[key] for key in ('passed', 'pairs', 'programs', 'pixel_checks', 'inherited_native_failures')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())

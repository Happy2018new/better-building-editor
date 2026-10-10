"""Compile actual native actor/sign shaders and verify sign pixels in WebGL 1/2.

The game includes are expanded by verify_biome_shader.shader_source. This is an
offline GLES check, not native game appearance acceptance.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from verify_biome_shader import shader_source


ENTITY_VARIANTS = (
    ('normal', ('USE_OVERLAY',)),
    ('transparent', ('USE_OVERLAY', 'ALPHA_TEST', 'BLEND', 'ENABLE_SET_TRANSPARENCY')),
    ('emissive', ('USE_OVERLAY', 'ALPHA_TEST', 'USE_EMISSIVE')),
    ('multitexture', ('USE_OVERLAY', 'ALPHA_TEST', 'USE_MULTITEXTURE')),
    ('local_light', ('USE_OVERLAY', 'RNGL_LOCAL_LIGHT')),
    ('skinning', ('USE_OVERLAY', 'USE_SKINNING')),
    ('glint_bloom', ('USE_OVERLAY', 'GLINT', 'USE_BLOOM')),
    ('glint_bloom_multitexture', ('USE_OVERLAY', 'GLINT', 'USE_BLOOM', 'USE_MULTITEXTURE')),
)
SIGN_VARIANTS = (
    ('normal', ('ALPHA_TEST', 'USE_LIGHTING')),
    ('glow', ('ALPHA_TEST', 'USE_EMISSIVE')),
    ('msdf', ('ALPHA_TEST', 'USE_LIGHTING', 'MSDF')),
    ('msdf_glow', ('ALPHA_TEST', 'USE_EMISSIVE', 'MSDF')),
)


def smoothstep(low, high, value):
    fraction = max(0., min(1., (value-low)/(high-low)))
    return fraction*fraction*(3.-2.*fraction)


def sign_expected(flags, tagged, opacity=1., pixel=None, color=None, darken=None, lighting=None):
    pixel = pixel or ([153, 153, 153, 255] if 'MSDF' in flags else [204, 204, 204, 255])
    color, darken, lighting = color or [.8, .6, .4, .75], darken or [.9, .8, .7, .6], lighting or [.25, .5, .75, 1.]
    if 'ALPHA_TEST' in flags and pixel[3] < 128:
        return [0., 0., 0., 0.]
    gain = lighting if 'USE_LIGHTING' in flags and not tagged else [1.]*4
    if 'MSDF' in flags:
        distance = sorted(pixel[:3])[1]/255.
        outer = smoothstep(.3, .7, distance)
        rgb = [color[i]*gain[i]*outer*darken[i]*255. for i in range(3)]
        # A transparent shadow isolates the two native outer-alpha factors.
        alpha = color[3]*outer*outer*darken[3]*opacity*255.
    else:
        diffuse = pixel[0]/255.
        rgb = [diffuse*color[i]*gain[i]*darken[i]*255. for i in range(3)]
        alpha = smoothstep(.4, 1., diffuse)*color[3]*darken[3]*opacity*255.
    return rgb+[alpha]


def sign_fixtures(flags):
    fixtures = []
    base_pixel = [153, 153, 153, 255] if 'MSDF' in flags else [204, 204, 204, 255]

    def add(name, tagged=False, bank=0., common=.125, local=False, opacity=1., blank=False, pixel=None):
        pixel = base_pixel if pixel is None else pixel
        fixtures.append({'name': name, 'packet': [19487. if tagged else 0., 0., bank, opacity],
                         'local': [0., 0., 0., 19490. if local else 0.], 'common': common,
                         'vertex_color': [.8, .6, .4, .75*common if tagged and bank else .75],
                         'pixel': pixel, 'expected': [0.]*4 if blank else sign_expected(flags, tagged, opacity if bank else 1., pixel),
                         'blank': blank, 'tolerance': 2})

    add('untagged_material_lighting')
    add('tagged_ignores_lighting', True)
    add('tagged_opacity_times_glyph_alpha', True, bank=1., opacity=.5)
    add('tagged_zero_opacity', True, bank=1., opacity=0.)
    add('glyph_alpha_test_blank', True, bank=1., pixel=[204, 204, 204, 32], blank=True)
    add('glyph_shape_alpha', True, bank=1., opacity=.5, pixel=[128, 128, 128, 255])
    for local in (False, True):
        label = 'local' if local else 'world'
        add(label+'_bank1_visible', True, bank=1., common=.125, local=local)
        add(label+'_bank2_hidden_for_bank1', True, bank=2., common=.125, local=local, blank=True)
        add(label+'_bank2_visible', True, bank=2., common=.625, local=local)
        add(label+'_bank1_hidden_for_bank2', True, bank=1., common=.625, local=local, blank=True)
    add('local_hidden_code_blanks_bank1', True, bank=1., common=1., local=True, blank=True)
    add('local_hidden_code_blanks_bank2', True, bank=2., common=1., local=True, blank=True)
    return fixtures


RENDER = r'''cases => {
  const results = [];
  const identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1];
  for (const c of cases) {
    const canvas = document.createElement('canvas'); canvas.width=canvas.height=4;
    const gl = canvas.getContext(c.version===300?'webgl2':'webgl',
      {antialias:false,alpha:true,premultipliedAlpha:false,preserveDrawingBuffer:true});
    const result = {name:c.name,kind:c.kind,version:c.version,flags:c.flags,
      compiled:false,linked:false,compile_errors:[],pixel_checks:[],failures:[]};
    if (!gl) { result.compile_errors.push('WebGL context unavailable'); results.push(result); continue; }
    const debug = gl.getExtension('WEBGL_debug_renderer_info');
    result.renderer = debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    gl.disable(gl.DITHER); gl.disable(gl.BLEND);
    const program = gl.createProgram();
    for (const [stage,type,source] of [['vertex',gl.VERTEX_SHADER,c.v],['fragment',gl.FRAGMENT_SHADER,c.f]]) {
      const shader = gl.createShader(type); gl.shaderSource(shader,source); gl.compileShader(shader);
      const log = gl.getShaderInfoLog(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) result.compile_errors.push({stage,log});
      gl.attachShader(program,shader);
    }
    result.compiled = result.compile_errors.length===0;
    if (result.compiled) {
      gl.linkProgram(program); result.linked = gl.getProgramParameter(program,gl.LINK_STATUS);
      if (!result.linked) result.compile_errors.push({stage:'link',log:gl.getProgramInfoLog(program)});
    }
    if (result.linked && c.fixtures.length) {
      gl.useProgram(program);
      const uniform = name => gl.getUniformLocation(program,name);
      for (const name of ['WORLD','WORLDVIEW','WORLDVIEWPROJ','PROJ','BONE'])
        gl.uniformMatrix4fv(uniform(name),false,identity);
      gl.uniform4f(uniform('TILE_LIGHT_COLOR'),.25,.5,.75,1);
      gl.uniform4f(uniform('DARKEN'),.9,.8,.7,.6);
      gl.uniform4f(uniform('SHADOW_COLOR'),0,0,0,0);
      gl.uniform2f(uniform('SHADOW_OFFSET'),0,0);
      gl.uniform1f(uniform('GLYPH_SMOOTH_RADIUS'),.2);
      gl.uniform1f(uniform('OUTLINE_CUTOFF'),.5);
      gl.uniform1f(uniform('SHADOW_SMOOTH_RADIUS'),.2);
      const buffer = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,1, 3,-1,0,1, -1,3,0,1]),gl.STATIC_DRAW);
      const position=gl.getAttribLocation(program,'POSITION');
      gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,4,gl.FLOAT,false,0,0);
      const color=gl.getAttribLocation(program,'COLOR'); if(color>=0) gl.vertexAttrib4f(color,.8,.6,.4,.75);
      const uv=gl.getAttribLocation(program,'TEXCOORD_0'); if(uv>=0) gl.vertexAttrib2f(uv,.5,.5);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.uniform1i(uniform('TEXTURE_0'),0);
      for(const fixture of c.fixtures) {
        if(color>=0) gl.vertexAttrib4fv(color,fixture.vertex_color);
        gl.uniform4fv(uniform('EXTRA_ACTOR_UNIFORM4'),fixture.packet);
        gl.uniform4fv(uniform('EXTRA_ACTOR_UNIFORM1'),fixture.local);
        gl.uniform1f(uniform('COMMON_BLOCK_GEO_FLOAT1_1'),fixture.common);
        gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array(fixture.pixel));
        gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT); gl.drawArrays(gl.TRIANGLES,0,3);
        const pixels = new Uint8Array(4*4*4); gl.readPixels(0,0,4,4,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
        const glError=gl.getError(), actual=Array.from(pixels.slice(20,24));
        const blank=Array.from(pixels).every(value=>value===0);
        const passed=!glError && (fixture.blank ? blank : fixture.expected.every((v,i)=>Math.abs(actual[i]-v)<=fixture.tolerance));
        const checked={name:fixture.name,passed,expected:fixture.expected,actual,
          required_blank:fixture.blank,entire_frame_blank:blank,gl_error:glError};
        result.pixel_checks.push(checked); if(!passed) result.failures.push(checked);
      }
    }
    result.passed=result.linked && result.failures.length===0;
    results.push(result); const lose=gl.getExtension('WEBGL_lose_context'); if(lose) lose.loseContext();
  }
  return results;
}'''


def digest(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def included_headers(paths, headers):
    found = {}

    def visit(path):
        for name in re.findall(r'^\s*#include\s+"([^"]+)"', path.read_text(encoding='utf8'), re.M):
            include = headers/name
            if name not in found:
                found[name] = digest(include)
                visit(include)

    for path in paths:
        visit(path)
    return found


def build_cases(project, headers):
    material_path = headers.parents[1]/'resource_packs/vanilla_netease/materials/entity.material'
    materials = json.loads(material_path.read_text(encoding='utf8'))['materials']
    native_material = materials['netease_block_as_entity_transparency:entity_alphatest_netease']
    native_vertex_name = native_material['vertexShader']
    native_vertex = headers/native_vertex_name.removeprefix('shaders/')
    native_fragment = headers/native_material['fragmentShader'].removeprefix('shaders/')
    paths = {'native_vertex': native_vertex,
             'entity_fragment': project/'resource_pack/shaders/glsl/modern_projection_native_actor.fragment',
             'sign_vertex': project/'resource_pack/shaders/glsl/modern_projection_sign_text.vertex',
             'sign_fragment': project/'resource_pack/shaders/glsl/modern_projection_sign_text.fragment',
             'native_fragment': native_fragment}
    cases = []
    for version in (100, 300):
        for name, flags in ENTITY_VARIANTS:
            cases.append({'name': 'entity/%d/%s' % (version, name), 'kind': 'entity', 'version': version,
                          'flags': flags, 'v': shader_source(paths['native_vertex'], headers, version, flags),
                          'f': shader_source(paths['entity_fragment'], headers, version, flags), 'fixtures': []})
            native_source = shader_source(native_fragment, headers, version, flags)
            version_end = native_source.index('\n')+1
            native_source = (native_source[:version_end]+'precision highp float;\nprecision highp int;\n'+
                             native_source[version_end:])
            cases.append({'name': 'native_baseline/%d/%s' % (version, name), 'kind': 'native_baseline',
                          'version': version, 'flags': flags,
                          'v': shader_source(native_vertex, headers, version, flags),
                          'f': native_source, 'fixtures': []})
        for name, flags in SIGN_VARIANTS:
            cases.append({'name': 'sign/%d/%s' % (version, name), 'kind': 'sign', 'version': version,
                          'flags': flags, 'v': shader_source(paths['sign_vertex'], headers, version, flags),
                          'f': shader_source(paths['sign_fragment'], headers, version, flags),
                          'fixtures': sign_fixtures(flags)})
    identities = {key: digest(path) for key, path in paths.items()}
    identities['native_material'] = digest(material_path)
    identities['native_material_key'] = 'netease_block_as_entity_transparency:entity_alphatest_netease'
    identities['expanded_headers'] = included_headers(paths.values(), headers)
    for case in cases:
        case['expanded_vertex_sha256'] = hashlib.sha256(case['v'].encode('utf8')).hexdigest()
        case['expanded_fragment_sha256'] = hashlib.sha256(case['f'].encode('utf8')).hexdigest()
    return cases, identities


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--headers', type=Path, required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    cases, identities = build_cases(args.project.resolve(), args.headers.resolve())
    report = {'schema': 1, 'completed': False, 'project': str(args.project.resolve()),
              'headers': str(args.headers.resolve()), 'browser': args.browser, 'sources': identities,
              'scope': 'Actual game GLSL include expansion, WebGL1/2 compile/link and synthetic sign pixels; no native appearance claim',
              'baseline_fragment_prelude': 'Explicit highp float/int defaults for WebGL; native source has no precision declaration',
              'sign_vertex_alpha_contract': 'Tagged banked geometry receives COLOR.a multiplied by encoded COMMON_BLOCK_GEO_FLOAT1_1; native runtime proof is separate',
              'pixel_tolerance': 2, 'required_blank': 'Every RGBA channel of every framebuffer pixel must be zero'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True,
                args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            try:
                report['results'] = browser.new_page().evaluate(RENDER, cases)
            finally:
                browser.close()
        report['sources_unchanged_after_render'] = all(
            digest(Path(identities[key]['path']))['sha256'] == identities[key]['sha256']
            for key in ('native_vertex', 'native_fragment', 'entity_fragment', 'sign_vertex', 'sign_fragment', 'native_material'))
        report['headers_unchanged_after_render'] = all(
            digest(Path(row['path']))['sha256'] == row['sha256']
            for row in identities['expanded_headers'].values())
        for result, case in zip(report['results'], cases):
            result['expanded_vertex_sha256'] = case['expanded_vertex_sha256']
            result['expanded_fragment_sha256'] = case['expanded_fragment_sha256']
        report['completed'] = True
        report['programs'] = len(report['results'])
        report['linked_programs'] = sum(result['linked'] for result in report['results'])
        report['pixel_checks'] = sum(len(result['pixel_checks']) for result in report['results'])
        report['pixel_failures'] = sum(len(result['failures']) for result in report['results'])
        report['passed'] = (report['sources_unchanged_after_render'] and report['headers_unchanged_after_render'] and
                            all(result['passed'] for result in report['results']))
        baseline = {result['name'].removeprefix('native_baseline/'): result for result in report['results']
                    if result['kind'] == 'native_baseline'}
        for result in report['results']:
            if result['kind'] == 'entity':
                result['native_baseline_linked'] = baseline[result['name'].removeprefix('entity/')]['linked']
                result['inherited_compile_failure'] = not result['linked'] and not result['native_baseline_linked']
        print(json.dumps({key: report[key] for key in ('completed', 'programs', 'linked_programs', 'pixel_checks', 'pixel_failures', 'passed')}))
        for result in report['results']:
            if not result['passed']:
                print(json.dumps({'name': result['name'], 'compile_errors': result['compile_errors'], 'failures': result['failures']}))
    finally:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())

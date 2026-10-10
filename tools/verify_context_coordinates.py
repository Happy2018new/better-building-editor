"""Run the production context coordinate decoder through WebGL transform feedback."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VERTEX = ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex'


def decoder(source):
    start = source.index('if (logicalPosition.y >= 512.0) {')
    depth = 0
    for end in range(start, len(source)):
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
            if depth == 0:
                return source[start:end + 1]
    raise ValueError('Unclosed context decoder')


def fixtures():
    rows = []
    for tx, ty, tz in ((0, 0, 0), (15, 15, 15), (16, 16, 16)):
        for ny in (-1, 0, 1):
            for nx in (-1, 0, 1):
                for nz in (-1, 0, 1):
                    for fy in (.001, .25, .5, .75, .999):
                        for fx in (.001, .25, .5, .75, .999):
                            for fz in (.001, .25, .5, .75, .999):
                                palette = (4*tx+1+nx+fx, 512+4*ty+1+ny+fy,
                                           4*tz+1+nz+fz)
                                native = (.5-palette[0], palette[1], .5-palette[2])
                                logical = (tx+nx+fx, ty+ny+fy, tz+nz+fz)
                                phase = tuple(value % 4. for value in palette)
                                visible = all(1. <= value <= 2. for value in phase)
                                rows.append((native, phase, logical, visible, (nx, ny, nz)))
    return rows


RENDER = r'''({vertex, positions}) => {
  const gl = document.createElement('canvas').getContext('webgl2');
  if (!gl) throw Error('WebGL2 unavailable');
  const program = gl.createProgram();
  const shader = gl.createShader(gl.VERTEX_SHADER);
  gl.shaderSource(shader, vertex); gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
  gl.attachShader(program, shader);
  const fragment = gl.createShader(gl.FRAGMENT_SHADER);
  gl.shaderSource(fragment, '#version 300 es\nprecision highp float;\nout vec4 color; void main(){color=vec4(1.0);}');
  gl.compileShader(fragment);
  if (!gl.getShaderParameter(fragment, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(fragment));
  gl.attachShader(program, fragment);
  gl.transformFeedbackVaryings(program, ['decodedContext', 'decodedPosition'], gl.INTERLEAVED_ATTRIBS);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(program));
  gl.useProgram(program);
  const input = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, input);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);
  const location = gl.getAttribLocation(program, 'POSITION');
  gl.enableVertexAttribArray(location); gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 0, 0);
  const output = gl.createBuffer(); gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, output);
  gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, positions.length / 3 * 7 * 4, gl.DYNAMIC_READ);
  gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, output);
  gl.enable(gl.RASTERIZER_DISCARD);
  gl.beginTransformFeedback(gl.POINTS);
  gl.drawArrays(gl.POINTS, 0, positions.length / 3);
  gl.endTransformFeedback();
  const result = new Float32Array(positions.length / 3 * 7);
  gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER, 0, result);
  return Array.from(result);
}'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    block = decoder(VERTEX.read_text(encoding='utf8'))
    vertex = '''#version 300 es
precision highp float;
in vec3 POSITION;
out vec4 decodedContext;
out vec3 decodedPosition;
void main() {
    vec3 logicalPosition = POSITION;
    vec4 renderContext = vec4(0.0);
    %s
    decodedContext = renderContext;
    decodedPosition = logicalPosition;
    gl_Position = vec4(0.0,0.0,0.0,1.0);
}''' % block
    cases = fixtures()
    positions = [axis for row in cases for axis in row[0]]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(args.browser), headless=True,
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        actual = browser.new_page().evaluate(RENDER, {'vertex': vertex, 'positions': positions})
        browser.close()
    failures = []
    native_signs = set()
    center_visible = 0
    for index, (native, phase, logical, visible, neighbor) in enumerate(cases):
        values = actual[index*7:(index+1)*7]
        got_phase, got_logical = values[:3], values[4:7]
        native_signs.update((axis > 0 for axis in (native[0], native[2])))
        if neighbor == (0, 0, 0):
            center_visible += 1
            expected_context = (phase[0], phase[1], phase[2], 1.)
        else:
            expected_context = (phase[0], phase[1], phase[2], 1.)
        expected_position = (.5-logical[0], logical[1], .5-logical[2])
        expected = expected_context + expected_position
        got_visible = all(1. <= value <= 2. for value in got_phase)
        if (any(abs(a-b) > 0.0002 for a, b in zip(values, expected)) or
                got_visible != visible or visible != (neighbor == (0, 0, 0))):
            failures.append({'index': index, 'native': native, 'expected': expected,
                             'actual': values, 'visible': visible,
                             'got_visible': got_visible, 'neighbor': neighbor})
            if len(failures) == 12:
                break
    result = {'checks': len(cases), 'center_visible_samples': center_visible,
              'native_axis_signs': sorted(native_signs), 'failures': failures}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result, indent=2))
    if failures or native_signs != {False, True}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

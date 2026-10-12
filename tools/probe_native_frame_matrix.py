"""Read matrix uniforms from an explicit native block-actor pixel marker.

The owner installs the printed fragment marker and selects a rectangle wholly
inside the frame backing. This tool only captures/decodes; it changes neither
game state nor shader files. All coordinates are native PNG, top-left origin.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MATRICES = ('WORLDVIEWPROJ', 'WORLDVIEW', 'PROJ', 'WORLD', 'BONE', 'PACKETS')
SCALE = 2048.
BIAS = 8388608
CONTROLS = (123.5, -456.25)
FIELDS = ('shader_flags', 'common', 'current_alpha', 'actor_tag_div8',
          'actor_bank', 'actor_opacity', 'positive_control', 'negative_control')


def fragment_preamble(matrix):
    """File-scope additions to the existing native actor fragment, used once."""
    lines = ['#include "uniformWorldConstants.h"',
             '#include "uniformShaderConstants.h"']
    if matrix == 'BONE':
        lines.extend(('#ifdef USE_SKINNING',
                      '#include "uniformAnimationConstants.h"', '#endif'))
    if matrix == 'PACKETS':
        lines.append('uniform highp vec4 EXTRA_ACTOR_UNIFORM1;')
    return '\n'.join(lines)


def element_multiplier(matrix, index):
    if matrix == 'PACKETS':
        if index < 4:
            return 2048.
        if index < 12:
            return .125
    return 1.


def validate_rectangle(rectangle, size):
    x, y, width, height = rectangle
    if width < 16 or height < 24 or width % 4 or height % 6:
        raise ValueError('Marker rectangle needs integer cells of at least 4 x 4 pixels')
    if not (x >= 0 and y >= 0 and x + width <= size[0] and y + height <= size[1]):
        raise ValueError('Marker rectangle is outside the native PNG')


def fragment_marker(matrix, rectangle, size):
    """Body of main(), inserted before native sampling/bank/alpha discards.

    Place fragment_preamble() at file scope, not inside main(). PACKETS also
    needs EXTRA_ACTOR_UNIFORM1. Do not duplicate an existing declaration. The
    existing actor fragment declares COMMON_BLOCK_GEO_FLOAT1_1 (conditional)
    and EXTRA_ACTOR_UNIFORM4. BONE is unavailable under large/Netease skinning.
    This deliberately has no projection-tag guard: a missing tag is a result.
    """
    validate_rectangle(rectangle, size)
    x, y, width, height = rectangle
    matrix_code = 'mat4 probeMatrix = %s;' % matrix
    if matrix == 'BONE':
        matrix_code = '''#if defined(USE_SKINNING) && !defined(LARGE_VERTEX_SHADER_UNIFORMS) && !defined(NETEASE_SKINNING)
    mat4 probeMatrix = BONE;
#else
    mat4 probeMatrix = mat4(0.0);
    probeFlags += 128.0;
#endif'''
    elif matrix == 'PACKETS':
        matrix_code = '''#ifdef ENABLE_SET_TRANSPARENCY
    vec4 probeCommon = vec4(COMMON_BLOCK_GEO_FLOAT1_1,0.0,0.0,0.0);
#else
    vec4 probeCommon = vec4(-1234.0,0.0,0.0,0.0);
#endif
    mat4 probeMatrix = mat4(CURRENT_COLOR,EXTRA_ACTOR_UNIFORM1,EXTRA_ACTOR_UNIFORM4,probeCommon);'''
    encoding_code = ''
    if matrix == 'PACKETS':
        encoding_code = '''// Preserve color packet bits and keep actor tags within signed24.
    if (probeIndex < 4.0) probeValue *= 2048.0;
    else if (probeIndex < 12.0) probeValue *= 0.125;'''
    return '''// Diagnostic only. Rectangle is native PNG top-left x/y/width/height.
    vec2 probePixel = vec2(gl_FragCoord.x, %(frame_height).1f-gl_FragCoord.y);
    vec2 probeCell = floor((probePixel-vec2(%(x).1f,%(y).1f))/vec2(%(cw).1f,%(ch).1f));
    if (any(lessThan(probeCell,vec2(0.0))) || any(greaterThanEqual(probeCell,vec2(4.0,6.0)))) discard;
    float probeFlags = 0.0;
    #ifdef GLINT
    probeFlags += 1.0;
    #endif
    #ifdef USE_SKINNING
    probeFlags += 2.0;
    #endif
    #ifdef NETEASE_SKINNING
    probeFlags += 4.0;
    #endif
    #ifdef LARGE_VERTEX_SHADER_UNIFORMS
    probeFlags += 8.0;
    #endif
    #ifdef ENABLE_SET_TRANSPARENCY
    probeFlags += 16.0;
    #endif
    %(matrix_code)s
    float probeIndex = probeCell.y*4.0+probeCell.x;
    float probeValue = 0.0;
    if (probeIndex < 16.0) {
        // Constant indexing also works on GLES 2 implementations.
        %(entries)s
    } else if (probeIndex < 17.0) probeValue = probeFlags;
    else if (probeIndex < 18.0) {
        #ifdef ENABLE_SET_TRANSPARENCY
        probeValue = COMMON_BLOCK_GEO_FLOAT1_1;
        #else
        probeValue = -1234.0;
        #endif
    } else if (probeIndex < 19.0) probeValue = CURRENT_COLOR.a;
    else if (probeIndex < 20.0) probeValue = EXTRA_ACTOR_UNIFORM4.x/8.0;
    else if (probeIndex < 21.0) probeValue = EXTRA_ACTOR_UNIFORM4.z;
    else if (probeIndex < 22.0) probeValue = EXTRA_ACTOR_UNIFORM4.w;
    else if (probeIndex < 23.0) probeValue = 123.5;
    else probeValue = -456.25;
    %(encoding_code)s
    if (probeValue < -4096.0 || probeValue > 4095.99951171875) {
        gl_FragColor = vec4(1.0,0.0,1.0,1.0);
        return;
    }
    float probeCode = floor(probeValue*2048.0+0.5)+8388608.0;
    gl_FragColor = vec4(floor(probeCode/65536.0),mod(floor(probeCode/256.0),256.0),mod(probeCode,256.0),255.0)/255.0;
    return;
''' % dict(frame_height=size[1], x=x, y=y, cw=width / 4., ch=height / 6.,
           matrix_code=matrix_code, encoding_code=encoding_code, entries='\n        '.join(
               '%s (probeIndex < %.1f) probeValue = probeMatrix[%d][%d];' %
               ('if' if index == 0 else 'else if', index + 1., index // 4, index % 4)
               for index in range(16)))


def decode(image, rectangle, matrix):
    validate_rectangle(rectangle, image.size)
    x, y, width, height = rectangle
    cell_width, cell_height = width // 4, height // 6
    samples, values, errors = [], [], []
    rgb = image.convert('RGB')
    for index in range(24):
        column, row = index % 4, index // 4
        center = (x + column * cell_width + cell_width // 2,
                  y + row * cell_height + cell_height // 2)
        points = [(center[0] + dx, center[1] + dy)
                  for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))]
        colors = [rgb.getpixel(point) for point in points]
        color = colors[0]
        value = ((color[0] << 16 | color[1] << 8 | color[2]) - BIAS) / SCALE
        if len(set(colors)) != 1:
            errors.append('Cell %d is not constant at its five sample pixels' % index)
        if color == (255, 0, 255):
            errors.append('Cell %d is outside the signed24 range' % index)
        samples.append({'index': index, 'points': points, 'rgb': colors, 'value': value})
        values.append(value)
    if tuple(values[22:24]) != CONTROLS:
        errors.append('Both independent signed24 controls must match exactly')
    flags = int(values[16])
    if values[16] != flags or flags < 0 or flags & ~159:
        errors.append('Shader flags are invalid')
    available = not bool(flags & 128)
    if matrix == 'BONE' and not available:
        errors.append('BONE unavailable for this native skinning variant')
    multipliers = [element_multiplier(matrix, index) for index in range(16)]
    elements = [value / multiplier for value, multiplier in zip(values[:16], multipliers)]
    result = {'passed': not errors, 'errors': errors, 'matrix': matrix,
            'elements_column_major': elements, 'matrix_available': available,
            'observations': dict(zip(FIELDS, values[16:])),
            'actor_tag': values[19] * 8., 'samples': samples,
            'element_encoding_multipliers': multipliers,
            'element_maximum_quantization_errors': [1. / (4096. * value) for value in multipliers],
            'maximum_quantization_error': max(1. / (4096. * value) for value in multipliers)}
    if matrix == 'PACKETS':
        result['packets'] = {'CURRENT_COLOR': elements[:4],
                             'EXTRA_ACTOR_UNIFORM1': elements[4:8],
                             'EXTRA_ACTOR_UNIFORM4': elements[8:12],
                             'COMMON_BLOCK_GEO_FLOAT1_1': elements[12],
                             'common_available': bool(flags & 16)}
    return result


def decode_capture(receipt, rectangle, matrix):
    if not (receipt.get('ok') and receipt.get('reliable') and receipt.get('background_only')
            and receipt.get('background_safe') and receipt.get('native_resolution')
            and receipt.get('backend') == 'Windows.Graphics.Capture'):
        raise ValueError('A successful background native WGC receipt is required')
    payload = Path(receipt['path']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != receipt['sha256'] or len(payload) != receipt['bytes']:
        raise ValueError('Native PNG bytes differ from the immutable receipt')
    frame = receipt['frame']
    if not frame.get('ok') or frame['frame_qpc_100ns'] < frame['request_qpc_100ns']:
        raise ValueError('The native WGC frame is stale')
    with Image.open(BytesIO(payload)) as image:
        if (image.format != 'PNG' or image.size != (receipt['width'], receipt['height'])
                or image.size != (frame['width'], frame['height'])):
            raise ValueError('PNG encoding or native dimensions differ from receipt')
        return decode(image, rectangle, matrix)


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', choices=MATRICES, required=True)
    parser.add_argument('--rectangle', type=int, nargs=4, required=True, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'))
    parser.add_argument('--print-fragment-marker', action='store_true')
    parser.add_argument('--print-fragment-preamble', action='store_true',
                        help='File-scope includes/declarations; add once outside main()')
    parser.add_argument('--framebuffer-size', type=int, nargs=2)
    parser.add_argument('--score-capture', type=Path, help='Existing immutable .capture.json')
    parser.add_argument('--session')
    parser.add_argument('--owner')
    parser.add_argument('--capture-exe', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.print_fragment_preamble:
        print(fragment_preamble(args.matrix))
        return 0
    if args.print_fragment_marker:
        if not args.framebuffer_size:
            parser.error('--print-fragment-marker requires --framebuffer-size')
        print(fragment_marker(args.matrix, args.rectangle, args.framebuffer_size))
        return 0
    if not args.output or args.output.exists():
        parser.error('Choose a fresh --output JSON path')
    if not args.score_capture and not all((args.session, args.owner, args.capture_exe)):
        parser.error('Live capture requires --session, --owner and --capture-exe')
    png = args.output.with_name(args.output.stem + '_' + args.matrix + '.png')
    if not args.score_capture and (png.exists() or png.with_suffix('.capture.json').exists()):
        parser.error('Choose fresh PNG and receipt paths')
    report = {'schema': 1, 'completed': False, 'passed': False,
              'production_rendering_accepted': False, 'game_mutations': False,
              'rectangle_top_left_xywh': args.rectangle, 'matrix': args.matrix,
              'scope': 'Actual native block-actor uniform pixel readback; no appearance acceptance',
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        if args.score_capture:
            raw = args.score_capture.read_bytes()
            receipt = json.loads(raw)
            report['source_receipt'] = {'path': str(args.score_capture.resolve()),
                                        'sha256': hashlib.sha256(raw).hexdigest()}
        else:
            from capture_native_window import capture, load_session
            session = load_session(args.session, args.owner, live=True)
            if Path(session['project']).resolve() != ROOT:
                raise ValueError('The owned session belongs to another project')
            receipt = capture(args.session, args.owner, png, args.capture_exe)
        report['capture'] = receipt
        marker = fragment_marker(args.matrix, args.rectangle, (receipt['width'], receipt['height']))
        report['expected_marker_main_sha256'] = hashlib.sha256(marker.encode('ascii')).hexdigest()
        report['readback'] = decode_capture(receipt, args.rectangle, args.matrix)
        report['completed'] = True
        report['passed'] = report['readback']['passed']
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_new(args.output, report)
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'matrix')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

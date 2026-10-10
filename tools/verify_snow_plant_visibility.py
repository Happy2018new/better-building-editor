"""Compare native snow and plant visibility at one fixed editor/world position."""
import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageChops
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, STATUS, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code, world_closeup
from verify_shulker_orientations import viewport_crop

FOCUS = (1, 1, 1)
LOAD = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import AIR,make_cell
from modern_projection.projection.block_registry import from_states
doc=Document((3,3,3),name='Snow plant visibility check')
plant=(%r,0)
height=%d
kind=%r
snow=from_states('minecraft:snow_layer',{'height':height,'covered_bit':kind=='covered'})
value=plant if kind=='plant' else make_cell(snow,plant if kind=='covered' else AIR)
doc.blocks[(1,1,1)]=value
sys._blueprint_qa_identity='snow.visibility.'+kind
s._loaded(doc)
s.camera_pivot=(1.5,1.5,1.5)
s.camera_view(35.,25.,12.)
_result=True
'''


def green_mask(frame):
    red, green, blue = frame.convert('RGB').split()
    first = ImageChops.subtract(green, red).point(lambda value: 255 if value > 7 else 0)
    second = ImageChops.subtract(green, blue).point(lambda value: 255 if value > 7 else 0)
    brightness = green.point(lambda value: 255 if value > 25 else 0)
    return ImageChops.multiply(ImageChops.multiply(first, second), brightness)


def analyze(path, crop, output, hidden=None):
    with Image.open(path) as source:
        frame = source.convert('RGB').crop(crop)
    mask = green_mask(frame)
    if hidden is not None:
        with Image.open(hidden) as source:
            reference = source.convert('RGB').crop(crop)
        delta = ImageChops.difference(frame, reference)
        channels = delta.split()
        largest = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        changed = largest.point(lambda value: 255 if value > 12 else 0)
        mask = ImageChops.multiply(mask, changed)
    mask.save(output)
    return {'green_pixels': mask.histogram()[255], 'bounds': mask.getbbox(),
            'crop': crop, 'mask': str(output.resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--plant', action='append', choices=('short_grass', 'fern', 'dandelion', 'poppy'))
    parser.add_argument('--height', type=int, action='append', choices=tuple(range(8)))
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    evidence = {'schema': 1, 'completed': False, 'rows': [], 'focus': FOCUS,
                'scope': 'Fixed-position green foliage pixels compare plant, snow and covered plant; inspect screenshots for clipping.'}
    installed = visual_saved = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual_saved = True
                check.refresh()
                for plant in args.plant or ('short_grass', 'fern'):
                    cases = [('plant', 0)] + [(kind, height)
                            for height in args.height or (0, 5) for kind in ('snow', 'covered')]
                    editor_crop = None
                    for kind, height in cases:
                        label = '%s_%s_h%d' % (plant, kind, height)
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        check.run(LOAD % ('minecraft:' + plant, height, kind))
                        state = check.wait('snow visibility preview',
                                           lambda value: not value['preview_pending'] and not value['running'] and
                                           not value['dirty'] and not value['mounting'] and value['model_revision_current'] and
                                           all(not row['pending'] for row in value['parts']),
                                           lambda: check.run(STATUS))
                        if state['preview_error']:
                            raise AssertionError(state)
                        time.sleep(.3)
                        editor = check.capture(label + '_editor')
                        if editor_crop is None:
                            editor_crop = viewport_crop(check, editor)
                        pixels = analyze(editor['path'], editor_crop,
                                         args.output.with_name(args.output.stem + '_' + label + '_editor_mask.png'))
                        world = world_closeup(check, label, FOCUS, (-2., 1.6, -2.5), 1.)
                        width, height_pixels = world['screenshot']['size']
                        crop = (width // 4, height_pixels // 4, width * 3 // 4, height_pixels * 3 // 4)
                        world_pixels = analyze(world['screenshot']['path'], crop,
                                               args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'),
                                               world['hidden_screenshot']['path'])
                        evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height,
                                                 'editor': editor, 'editor_pixels': pixels,
                                                 'world': world, 'world_pixels': world_pixels})
                        write_json(args.output, evidence)
                        print(json.dumps({'label': label, 'editor': pixels['green_pixels'],
                                          'world': world_pixels['green_pixels']}), flush=True)
                        check.run('b.stop_projection()\n_result=True')
                        check.run(camera_restore_code(False))
                evidence['completed'] = True
            finally:
                if visual_saved:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if installed:
                    was_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if was_open:
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('restore workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('restore closed workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                    evidence['restored'] = True
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)


if __name__ == '__main__':
    main()

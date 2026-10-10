"""Compare native snow and plant visibility at one fixed editor/world position."""
import argparse
import base64
import json
import time
from pathlib import Path

from PIL import Image, ImageChops
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, STATUS, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code, world_closeup
from verify_shulker_orientations import viewport_crop

ROOT = Path(__file__).resolve().parents[1]
LOAD = '''from modern_projection.projection.model import Document
from modern_projection.projection.cell import _covered_snow,foreground,rebase
from modern_projection.projection.debug_blueprints import build,VISUAL_CASES
from modern_projection.projection import block_registry as registry
plant=%r
height=%d
kind=%r
case=VISUAL_CASES['snow_plant_visibility']
focus=case['focus']
row=next(row for row in case['cells'] if row['plant']==plant)
source_pos=row['standalone'] if kind=='plant' else next(pos for h,pos in row['covered'] if h==height)
source=build(case['fixture'])
value=source.get(source_pos)
if kind=='snow':value=_covered_snow(foreground(value),False)
doc=Document(case['size'],name='Snow plant visibility check')
doc.blocks[focus]=rebase(value,tuple(focus[i]-source_pos[i] for i in range(3)))
sys._blueprint_qa_identity='snow.visibility.'+kind
s._loaded(doc)
s.camera_pivot=tuple(v+.5 for v in focus)
s.camera_view(*case['camera']['editor'])
_result=json.dumps({'fixture':case['fixture'],'fixture_schema':case['schema'],
 'source_position':source_pos,'focus':focus,'registry_version':registry.source_version(),
 'registry_fingerprint':registry.fingerprint()})
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
    parser.add_argument('--plant', action='append', choices=('short_grass', 'fern', 'dandelion', 'poppy', 'blue_orchid', 'allium'))
    parser.add_argument('--height', type=int, action='append', choices=(0, 5))
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    evidence = {'schema': 2, 'completed': False, 'rows': [],
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
                blueprint_path = ROOT / 'behavior_pack/modern_projection/projection/debug_blueprints.py'
                case = check.run('import base64\nimport modern_projection.projection.debug_blueprints as refreshed\n'
                                 'eval(compile(base64.b64decode(%r),%r,"exec"),refreshed.__dict__)\n'
                                 '_result=json.dumps(refreshed.VISUAL_CASES["snow_plant_visibility"])' %
                                 (base64.b64encode(blueprint_path.read_bytes()).decode('ascii'), str(blueprint_path)))
                focus = tuple(case['focus'])
                evidence['focus'] = focus
                evidence['blueprint_case'] = case
                for plant in args.plant or ('short_grass', 'fern'):
                    cases = [('plant', 0)] + [(kind, height)
                            for height in args.height or (0, 5) for kind in ('snow', 'covered')]
                    editor_crop = None
                    for kind, height in cases:
                        label = '%s_%s_h%d' % (plant, kind, height)
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('open workspace', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                        source = check.run(LOAD % (plant, height, kind))
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
                        world = world_closeup(check, label, focus, tuple(case['camera']['world_offset']), 1.)
                        width, height_pixels = world['screenshot']['size']
                        crop = (width // 4, height_pixels // 4, width * 3 // 4, height_pixels * 3 // 4)
                        world_pixels = analyze(world['screenshot']['path'], crop,
                                               args.output.with_name(args.output.stem + '_' + label + '_world_mask.png'),
                                               world['hidden_screenshot']['path'])
                        evidence['rows'].append({'plant': plant, 'kind': kind, 'height': height, 'source': source,
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

"""Predeclared native projection diagnostic on the unchanged water freeze."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/bbe-r18-water-production')
OUTPUT = ROOT / '.runtime/water-final-r19-world-v5'
PREVIOUS = ROOT / '.runtime/water-final-r19-world-v4'
os.environ['MCDEV_WATER_FINAL_OUTPUT'] = str(OUTPUT)
os.environ['MCDEV_WATER_START_WAIT'] = '180'
os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
spec = importlib.util.spec_from_file_location('water_final', ROOT / '.runtime/run-water-final-r19.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
sys.path.insert(0, str(PROJECT / 'tools'))


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grids():
    result = {}
    for name, horizontal, height in (
            ('original', np.linspace(.12, .88, 18), np.linspace(.16, .72, 14)),
            ('texel_centers', np.arange(2, 14) / 15., 1. - np.arange(5, 13) / 15.)):
        u, h = np.meshgrid(horizontal, height)
        for face, positions in (('south', ((3, 3, 4), (4, 3, 4))),
                                ('east', ((4, 3, 3), (4, 3, 4)))):
            for position in positions:
                x, y, z = position
                points = [(x + 1. - a, y + b, z + 1.) if face == 'south'
                          else (x + 1., y + b, z + a) for a, b in zip(u.ravel(), h.ravel())]
                key = '%s_%s_%s' % (name, face, '_'.join(map(str, position)))
                result[key] = {'grid': name, 'face': face, 'cell': position,
                               'dimensions': u.shape, 'points': points}
    return result


def prepare():
    if OUTPUT.exists():
        raise ValueError('Choose fresh diagnostic output')
    OUTPUT.mkdir()
    shutil.copyfile(PREVIOUS / 'launch-inputs.json', OUTPUT / 'launch-inputs.json')
    plan = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
            'frozen_source_contract': '20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272',
            'tool_sha256': digest(Path(__file__)), 'grids': grids(),
            'route': 'full', 'case': 'pool', 'shader_formula': 'u*15+.5; (1-height)*15+.5',
            'native_coordinate_units': 'physical pixels; unscaled, independently checked on stone hull',
            'pixel_center_subtractions': [.5, 0., 1.], 'primary_pixel_center_subtraction': .5,
            'fov_diagnostic_values': [66.3, 66.6], 'original_acceptance_unchanged': True,
            'negative_controls': ['horizontal mirror', 'constant', 'wrong phase 5 columns',
                                  'erroneous native UI-to-physical x/y scaling'],
            'limits': {'correlation': .85, 'rgb_rmse': 8., 'contrast': 1.}}
    save('plan.json', plan)
    save('plan-receipt.json', {'sha256': digest(OUTPUT / 'plan.json'), 'prelaunch': True})


NATIVE_STATE = '''cam=b.factory.CreateCamera(b.level)
assert hasattr(cam,'WorldToScreenPoint')
world_points=json.loads(%r)
projected={}
for key,points in world_points.items():
 projected[key]=[cam.WorldToScreenPoint(*tuple(point[i]+s.origin[i] for i in range(3))) for point in points]
''' + runner.__doc__[:0]


def native_code(plan):
    from probe_liquid_workspace import WATER_OWNER
    return (NATIVE_STATE % json.dumps({key: row['points'] for key, row in plan['grids'].items()})
            + WATER_OWNER + '''renderer=liquid.renderer if liquid is not None else None
groups=[]
if renderer is not None:
 for key,record in sorted(renderer.active.items(),key=lambda item:repr(item[0])):
  model_id=record['model_id'];group=record['group']
  groups.append({'key':repr(key),'id':model_id,'group':group,'anchor':record['anchor'],
   'visible':record['visible'],'expected_center':renderer.center(renderer.anchor,group.origin),
   'actual_uniforms':dict((index,renderer.model.GetExtraUniformValue(model_id,index)) for index in (1,2,3,4))})
_result=json.dumps({'projection':projected,'groups':groups,'origin':s.origin,
 'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
''')


STONE_NATIVE = '''cam=b.factory.CreateCamera(b.level)
assert hasattr(cam,'WorldToScreenPoint')
points=[tuple(s.origin[i]+offset[i] for i in range(3))
 for offset in ((x,y,z) for x in (1.,2.) for y in (1.,2.) for z in (1.,2.))]
_result=json.dumps({'world_points':points,'projected':[cam.WorldToScreenPoint(*point) for point in points],
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'camera_position':cam.GetPosition()})
'''


def calibration():
    import verify_camera_projection as tool
    from capture_native_window import capture
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=runner.OWNER)
    readings = {}

    def frame(self, label, tree=None):
        readings[label] = {'before': self.run(STONE_NATIVE)}
        save('calibration-native.json', readings)
        result = capture(bound['session_file'], runner.OWNER, OUTPUT / ('calibration_' + label + '.png'), runner.CAPTURE)
        result['size'] = [result['width'], result['height']]
        readings[label]['after'] = self.run(STONE_NATIVE)
        save('calibration-native.json', readings)
        return result

    tool.SignCheck.capture = frame
    sys.argv = ['verify_camera_projection.py', str(OUTPUT / 'calibration.json'),
                '--native-resolution', '--skyward-tilted', '--fixture-lift-y', '64']
    return tool.main()


def world():
    import probe_product_water as probe
    bound = json.loads((OUTPUT / 'start.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=runner.OWNER)
    plan = json.loads((OUTPUT / 'plan.json').read_bytes())
    original = probe.base.capture
    readings = {}
    code = native_code(plan)

    def frame(*args, **kwargs):
        label = args[2].stem
        with probe.base.Client(timeout=45) as client:
            check = probe.blueprints.BlueprintCheck(client, OUTPUT / 'native-readback.json', 45.)
            readings[label] = {'before': check.run(code)}
            save('world-native.json', readings)
            result = original(*args, **kwargs)
            readings[label]['after'] = check.run(code)
            save('world-native.json', readings)
            return result

    probe.base.capture = frame
    sys.argv = ['probe_product_water.py', '--session', bound['session_file'], '--owner', runner.OWNER,
                '--capture-exe', str(runner.CAPTURE), '--launch-inputs', str(OUTPUT / 'launch-inputs.json'),
                '--output', str(OUTPUT / 'world.json'), '--frozen', '--opaque-side-controls',
                '--visibility-controls', '--max-seconds', '180', '--route', 'full', '--case', 'pool',
                '--camera-calibration', str(OUTPUT / 'calibration.json'), '--world-fixture-lift-y', '64',
                '--world-view-scale', '.5', '--pool-view-scale', '.5']
    return probe.main()


def values(image, coordinates, dimensions, subtraction=.5):
    coordinates = np.asarray(coordinates)
    samples = np.stack([map_coordinates(image[:, :, channel].astype(float),
        (coordinates[:, 1] - subtraction, coordinates[:, 0] - subtraction), order=1, mode='nearest')
        for channel in range(3)], axis=1)
    return samples.reshape(tuple(dimensions) + (3,))


def pair(first, second):
    from analyze_water_acceptance_r16 import repetition
    result = repetition(first, second)
    result['negative_mirrored'] = repetition(first, second[:, ::-1])
    result['negative_constant'] = repetition(first, np.full_like(second, second.mean()))
    result['negative_wrong_phase'] = repetition(first, np.roll(second, 5, axis=1))
    result['passed'] = result['passed'] and all(not result[name]['passed'] for name in
        ('negative_mirrored', 'negative_constant', 'negative_wrong_phase'))
    return result


def offline():
    from analyze_product_water import project, rgb
    from analyze_water_acceptance_r16 import side_checks
    source = json.loads((PREVIOUS / 'world.json').read_bytes())
    row = source['extra_rows']['full_pool_wet_side_opaque']
    image = rgb(source['captures']['full_pool_wet_side_opaque']['path'])
    shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']}
    result = {'diagnostic_only': True, 'production_qualified': False, 'variants': {}}
    for fov in (66.3, 66.6):
        source['camera_calibration']['vertical_fov'] = fov
        for subtraction in (.5, 0., 1.):
            observed = {}
            for key, grid in grids().items():
                coordinates = project(grid['points'], shapes[tuple(grid['cell'])], row, source, (image.shape[1], image.shape[0]))
                observed[key] = values(image, coordinates, grid['dimensions'], subtraction)
            variant = {}
            for grid in ('original', 'texel_centers'):
                for face, cells in (('south', ('3_3_4', '4_3_4')), ('east', ('4_3_3', '4_3_4'))):
                    variant[grid + '_' + face] = pair(*(observed[grid + '_' + face + '_' + cell] for cell in cells))
            result['variants']['fov_%s_subtract_%s' % (fov, subtraction)] = variant
    save('offline-conventions.json', result)
    print(json.dumps({key: {name: row['correlation'] for name, row in variant.items()}
                      for key, variant in result['variants'].items()}))


def analyze():
    from analyze_product_water import project, rgb
    from verify_camera_projection import stone_signal
    from verify_missing_neighbor_visuals import hull
    from PIL import Image, ImageDraw, ImageChops
    source = json.loads((OUTPUT / 'world.json').read_bytes())
    native = json.loads((OUTPUT / 'world-native.json').read_bytes())
    plan = json.loads((OUTPUT / 'plan.json').read_bytes())
    label = 'full_pool_wet_side_opaque'
    row = source['extra_rows'][label]
    image = rgb(source['captures'][label]['path'])
    readings = native['world_' + label]
    shapes = {tuple(shape['position']): shape for shape in row['ready']['shapes']}
    report = {'diagnostic_only': True, 'production_qualified': False,
              'plan_sha256': digest(OUTPUT / 'plan.json'), 'variants': {}, 'coordinates': {}, 'stone': {}}
    for mapping in ('analytic', 'native', 'native_wrong_ui_scaling'):
        for subtraction in plan['pixel_center_subtractions']:
            observed = {}
            for key, grid in plan['grids'].items():
                actual = np.asarray([(point['screenX'], point['screenY']) for point in readings['before']['projection'][key]])
                analytical = np.asarray(project(grid['points'], shapes[tuple(grid['cell'])], row, source,
                                                  (image.shape[1], image.shape[0])))
                if mapping == 'analytic':
                    coordinates = analytical
                elif mapping == 'native':
                    coordinates = actual
                else:
                    coordinates = actual * np.asarray([image.shape[1], image.shape[0]]) / readings['before']['screen']
                observed[key] = values(image, coordinates, grid['dimensions'], subtraction)
                if mapping == 'native' and subtraction == .5:
                    delta = actual - analytical
                    after = np.asarray([(p['screenX'], p['screenY']) for p in readings['after']['projection'][key]])
                    report['coordinates'][key] = {'mean_native_minus_analytic': delta.mean(axis=0).tolist(),
                        'range_native_minus_analytic': [delta.min(axis=0).tolist(), delta.max(axis=0).tolist()],
                        'maximum_before_after_delta': float(abs(after - actual).max()),
                        'native_bounds': [actual.min(axis=0).tolist(), actual.max(axis=0).tolist()]}
            variant = {}
            for name in ('original', 'texel_centers'):
                for face, cells in (('south', ('3_3_4', '4_3_4')), ('east', ('4_3_3', '4_3_4'))):
                    variant[name + '_' + face] = pair(*(observed[name + '_' + face + '_' + cell] for cell in cells))
            report['variants']['%s_subtract_%s' % (mapping, subtraction)] = variant
    calibration = json.loads((OUTPUT / 'calibration.json').read_bytes())
    cal_native = json.loads((OUTPUT / 'calibration-native.json').read_bytes())
    for row in calibration['views']:
        signal = stone_signal(row['shown']['path'], row['hidden']['path'])
        points = cal_native[row['view'] + '_shown']['before']['projected']
        polygon = hull((point['screenX'], point['screenY']) for point in points)
        expected = Image.new('L', signal.size)
        ImageDraw.Draw(expected).polygon(polygon, fill=255)
        count = signal.histogram()[255]
        expected_count = expected.histogram()[255]
        intersection = ImageChops.multiply(signal, expected).histogram()[255]
        report['stone'][row['view']] = {'native_api_bounds': expected.getbbox(), 'observed_bounds': signal.getbbox(),
            'native_api_mask_iou': intersection / max(1, count + expected_count - intersection)}
    save('native-projection-analysis.json', report)
    print(json.dumps({'stone': report['stone'], 'variants': {key: {name: row['correlation'] for name, row in variant.items()}
                      for key, variant in report['variants'].items()}}))


def batch():
    phases = {'completed': False, 'production_qualified': False}
    try:
        for phase in ('launch', 'workspace-ready', 'calibration', 'world'):
            result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), phase],
                                    capture_output=True, text=True, encoding='utf8')
            save(phase + '-execution.json', {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
            phases[phase] = result.returncode == 0
            save('batch.json', phases)
            print(json.dumps({'phase': phase, 'returncode': result.returncode}), flush=True)
            if result.returncode:
                raise RuntimeError('Native diagnostic failed: ' + phase)
        phases['completed'] = True
    finally:
        if (OUTPUT / 'start.json').exists():
            result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), 'stop'],
                                    capture_output=True, text=True, encoding='utf8')
            phases['stop_returncode'] = result.returncode
        save('batch.json', phases)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode in ('prepare', 'offline', 'calibration', 'world', 'analyze', 'batch'):
        raise SystemExit(globals()[mode]())
    raise SystemExit(runner.launch() if mode == 'launch' else runner.run(mode))

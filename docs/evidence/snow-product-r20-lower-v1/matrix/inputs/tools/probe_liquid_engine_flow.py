"""Observe production water shader motion in a separately owned minimal world.

Four equal-height top faces have independent cardinal UV directions. A fifth
control exposes one falling side. Magenta, opaque uniforms isolate the moving
artwork from the world without changing the production shaders or textures.
This diagnoses the engine resource path; it is not Scene/WorldProjection owner
acceptance or a claim of native water parity.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import load_session
from mcdk import Client, return_value
from capture_native_burst import capture
from analyze_product_water_flow import GRID, burst_frames, motion
from probe_product_water import snapshot_sources, snapshot_digest


SETUP = '''import sys,json
import mod.client.extraClientApi as api
assert not hasattr(sys,'_liquid_flow_engine_probe')
factory=api.GetEngineCompFactory();level=api.GetLevelId()
foot=factory.CreatePos(api.GetLocalPlayerId()).GetFootPos()
assert foot and len(foot)==3
origin=tuple(foot[i]+(6.,5.,6.)[i] for i in range(3))
center=tuple(value+2. for value in origin)
cam=factory.CreateCamera(level);model=factory.CreateModel(level)
saved={'model_id':None,'origin':origin,'center':center}
sys._liquid_flow_engine_probe=saved
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
_result=json.dumps({'origin':origin,'runtime':api.GetMinecraftVersion()})
'''
SHOW = '''import sys,json
import mod.client.extraClientApi as api
saved=sys._liquid_flow_engine_probe
factory=api.GetEngineCompFactory();level=api.GetLevelId()
model=factory.CreateModel(level);cam=factory.CreateCamera(level)
if saved['model_id'] is not None:assert model.RemoveFreeModel(saved['model_id'])
side=%r
name='modern_projection_liquid_product_flowing_water_grey'+('' if side else '_top')+'_world'
model_id=model.CreateFreeModel(name,0);assert model_id
saved['model_id']=model_id
assert model.SetFreeModelScale(model_id,16.,16.,16.)
assert model.SetFreeModelBoundingBox(model_id,(-4.,-4.,-4.),(4.,4.,4.))
assert model.SetFreeModelRot(model_id,0.,0.,0.)
assert model.SetFreeModelPos(model_id,*saved['center'])
codes=(256.,0.,0.,0.) if side else (64.+4096.*192.,65.,68.+4096.*64.,69.+4096.*128.)
payload=(codes,(65535.,65535.,65535.,65535.),(65535.,65535.,65535.,65535.),(39686.,1.,16711935.,1.))
for index,value in enumerate(payload,1):assert model.SetExtraUniformValue(model_id,index,value)
offset=(.5,.5,1.) if side else (1.,1.,1.)
target=tuple(saved['origin'][i]+offset[i] for i in range(3))
position=tuple(target[i]+((0.,-3.,3.) if side else (0.,4.,2.5))[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'model':name,'payload':payload,'position':position,'target':target,'rotation':rotation})
'''
STATE = '''import sys,json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory();cam=factory.CreateCamera(api.GetLevelId())
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':factory.CreateGame(api.GetLevelId()).GetScreenSize(),
 'model_id':sys._liquid_flow_engine_probe['model_id']})
'''
RESTORE = '''import sys,json
import mod.client.extraClientApi as api
saved=getattr(sys,'_liquid_flow_engine_probe',None)
if saved is not None:
 factory=api.GetEngineCompFactory();level=api.GetLevelId()
 if saved['model_id'] is not None:assert factory.CreateModel(level).RemoveFreeModel(saved['model_id'])
 factory.CreateCamera(level).UnDepartCamera()
 del sys._liquid_flow_engine_probe
_result=json.dumps({'restored':True})
'''


def isolated_face_map(rgb, side):
    """Recover the known level rectangle from its opaque diagnostic tint.

    Camera yaw is zero relative to the rectangle; x grows to the right and z
    grows toward the viewer. For the falling south side, physical y grows up.
    The four corners are fitted from independent pixel boundaries, not UVs or
    animation motion. This also avoids assuming a camera FOV convention.
    """
    selected = (rgb[:, :, 0] > 30) & (rgb[:, :, 1] < 3) & (rgb[:, :, 2] > 30)
    y, x = np.where(selected)
    if len(x) < 500:
        raise ValueError('Opaque diagnostic surface has insufficient native pixels')
    low, high = int(y.min()), int(y.max())
    edge_rows = []
    for row in range(low + 2, high - 1):
        columns = np.flatnonzero(selected[row])
        if len(columns) >= 20:
            edge_rows.append((row, columns[0], columns[-1]))
    edges = np.array(edge_rows, dtype=float)
    if len(edges) < 20:
        raise ValueError('Diagnostic rectangle is clipped or too small')
    left = np.polyfit(edges[:, 0], edges[:, 1], 1)
    right = np.polyfit(edges[:, 0], edges[:, 2], 1)
    corners = np.array([[np.polyval(left, low), low], [np.polyval(right, low), low],
                        [np.polyval(left, high), high], [np.polyval(right, high), high]])
    units = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=float)
    a, b = [], []
    for (u, v), (px, py) in zip(units, corners):
        a.extend(([u, v, 1, 0, 0, 0, -u * px, -v * px],
                  [0, 0, 0, u, v, 1, -u * py, -v * py]))
        b.extend((px, py))
    h = np.append(np.linalg.solve(a, b), 1).reshape((3, 3))
    return h, {'corners': corners.tolist(), 'support_pixels': len(x), 'side': side}


def analyze_burst(receipt, side):
    paths, times = burst_frames(receipt)
    with Image.open(paths[0]) as image:
        h, boundary = isolated_face_map(np.asarray(image.convert('RGB')), side)
    pixels = []
    for path in paths:
        with Image.open(path) as image:
            pixels.append(np.asarray(image.convert('RGB'))[:, :, 0].astype(float))
    u, v = np.meshgrid(np.linspace(.08, .92, GRID), np.linspace(.08, .92, GRID))
    rows = [('falling_side', 0, -1, u, 1 - v, .84 / (GRID - 1), 15)] if side else [
        ('flow_east', 1, 1, u / 2, v / 2, .84 / (GRID - 1), 16),
        ('flow_south', 0, 1, (u + 1) / 2, v / 2, .84 / (GRID - 1), 16),
        ('flow_west', 1, -1, u / 2, (v + 1) / 2, .84 / (GRID - 1), 16),
        ('flow_north', 0, -1, (u + 1) / 2, (v + 1) / 2, .84 / (GRID - 1), 16)]
    results = {}
    for name, axis, sign, x, y, spacing, texels in rows:
        points = h @ np.stack((x.ravel(), y.ravel(), np.ones(GRID * GRID)))
        points /= points[2]
        signal = np.array([map_coordinates(frame, (points[1], points[0]), order=1).reshape(GRID, GRID)
                           for frame in pixels])
        results[name] = motion(signal, np.asarray(times), axis, sign, spacing, texels)
        results[name]['reversed_time_rejected'] = not motion(
            signal[::-1], np.asarray(times), axis, sign, spacing, texels)['passed']
    return {'boundary': boundary, 'frames': len(paths), 'results': results,
            'passed': all(row['passed'] and row['reversed_time_rejected'] for row in results.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--burst-exe', type=Path, required=True)
    parser.add_argument('--burst-sha256', required=True)
    parser.add_argument('--faces', choices=('both', 'top', 'side'), default='both')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh flow evidence')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    project = Path(session['project'])
    source = snapshot_sources(project)
    report = {'completed': False, 'restored': False, 'cleanup_errors': [], 'source_unchanged': False,
              'source_contract_sha256': snapshot_digest(source), 'source_sha256': source,
              'session_id': session['id'], 'owner': args.owner, 'project': str(project),
              'product_acceptance_claimed': False, 'rows': {}}
    with Client(timeout=30) as client:
        def run(code):
            result = return_value(client.call('execute_code', {'code': code, 'is_client': True, 'direct_return': True}))
            return json.loads(result) if isinstance(result, str) else result
        try:
            report['setup'] = run(SETUP)
            for side in ((False, True) if args.faces == 'both' else (args.faces == 'side',)):
                label = 'side' if side else 'top'
                row = report['rows'][label] = {'setup': run(SHOW % side)}
                time.sleep(.5)
                row['camera_before'] = run(STATE)
                row['capture'] = capture(args.session, args.owner, args.output.with_name(args.output.stem + '_' + label),
                    args.burst_exe, args.burst_sha256, duration_ms=1600, max_frames=240, max_gap_ms=150)
                row['camera_after'] = run(STATE)
                if row['camera_before'] != row['camera_after']:
                    raise ValueError('Camera changed during native flow burst')
                row['analysis'] = analyze_burst(row['capture'], side)
            report['completed'] = all(row['analysis']['passed'] for row in report['rows'].values())
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
        finally:
            try:
                report['restore'] = run(RESTORE)
                report['restored'] = True
            except Exception as error:
                report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
            report['source_unchanged'] = snapshot_sources(project) == source
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
    return 0 if report['completed'] and report['restored'] and report['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

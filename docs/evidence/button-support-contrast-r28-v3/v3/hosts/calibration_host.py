"""Bind actual mounted UI/scissor reads to the saved owned WGC frame; no launch."""
import hashlib
import itertools
import json
import math
from pathlib import Path


def dimension_pair(value, label):
    assert type(value) in (tuple, list), label + ': expected tuple/list dimensions'
    assert len(value) == 2, label + ': expected exactly two dimensions'
    assert all(type(item) is int and item > 0 for item in value), label + ': dimensions must be positive integers'
    return tuple(value)


def bind_capture(calibration, capture, observer_config):
    png = Path(capture['path'])
    raw = png.read_bytes()
    sidecar = png.with_suffix('.capture.json')
    record = json.loads(sidecar.read_bytes())
    assert record['ok'] is True and record['reliable'] is True
    assert record['native_resolution'] is True
    assert record['owner'] == observer_config['owner']
    assert record['game_identity'] == observer_config['game_identity']
    assert Path(record['path']).resolve() == png.resolve()
    digest = hashlib.sha256(raw).hexdigest()
    assert record['sha256'] == capture['sha256'] == digest
    frame = record['frame']
    assert frame['ok'] is True
    assert frame['frame_qpc_100ns'] >= frame['request_qpc_100ns']
    pixels = dimension_pair((frame['width'], frame['height']), 'raw WGC frame')
    capture_pixels = dimension_pair(capture['size'], 'capture return')
    record_pixels = dimension_pair((record['width'], record['height']), 'PNG record')
    assert pixels == capture_pixels == record_pixels, 'Capture dimensions differ by value'
    physical = calibration['physical_screen_info']
    assert type(physical) in (list, tuple) and len(physical) == 4
    assert all(isinstance(v,(int,float)) and math.isfinite(v) for v in physical)
    assert min(physical[:2]) > 0
    screen = calibration['logical_screen']
    assert len(screen) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in screen)
    assert calibration['native_gui_scale'] == max(1., round(float(physical[0])/screen[0]))
    assert calibration['native_gui_scale_source'] == 'frozen_Theme_configure_formula_from_actual_Game_tuples'
    ratios = tuple(float(pixels[i])/screen[i] for i in range(2))
    assert abs(ratios[0]/ratios[1]-1.) < .005, 'UI/capture aspect ratio mismatch'
    canvas, clipping = calibration['canvas'], calibration['clipping']
    x, y = canvas['global']
    cw, ch = canvas['size']
    assert canvas['visible'] and clipping['visible'] and cw > 0 and ch > 0
    geometry = (math.ceil(x)-x, math.ceil(y)-y,
                max(0., math.floor(x+cw)-math.ceil(x)),
                max(0., math.floor(y+ch)-math.ceil(y)))
    assert len(calibration['clip_geometry']) == 4
    assert all(abs(a-b) < 1e-5 for a,b in zip(geometry, calibration['clip_geometry']))
    expected_global = (x+geometry[0], y+geometry[1])
    assert all(abs(clipping['global'][i]-expected_global[i]) < 1e-4 for i in range(2))
    assert all(abs(clipping['size'][i]-geometry[2+i]) < 1e-4 for i in range(2))
    assert all(abs(clipping['position'][i]-geometry[i]) < 1e-4 for i in range(2))
    clip_ui = (expected_global[0],expected_global[1],
               expected_global[0]+geometry[2],expected_global[1]+geometry[3])
    clip_pixels = tuple(clip_ui[i]*ratios[i%2] for i in range(4))
    assert clip_pixels[0] >= 0 and clip_pixels[1] >= 0
    assert clip_pixels[2] <= pixels[0]+1 and clip_pixels[3] <= pixels[1]+1
    props, theme = calibration['scene_props'], calibration['theme_scale']
    assert math.isfinite(theme) and theme > 0
    unit = min(props)*theme*12.*.72/32.
    assert abs(unit-calibration['cell_unit']) < 1e-6
    assert abs(calibration['native_pose'][0]-unit*calibration['scene_scale']/10.) < 1e-8
    assert calibration['native_pose'][1:] == [-170.0,35]
    rx, uy, tx, ty = calibration['camera_projection']
    assert len(rx) == len(uy) == 3
    assert abs(rx[1]) < 1e-8
    assert abs(uy[1]+unit*math.cos(math.radians(-80))) < 1e-6
    boxes = {}
    for label, bottom in (('original_support',4),('derived_support_yplus4',8)):
        points = []
        for point in itertools.product((3.,4.),(float(bottom),float(bottom+1)),(27.,28.)):
            ui = (x+tx+sum(point[i]*rx[i] for i in range(3)),
                  y+ty+sum(point[i]*uy[i] for i in range(3)))
            points.append(tuple(ui[i]*ratios[i] for i in range(2)))
        box = [min(v[0] for v in points),min(v[1] for v in points),
               max(v[0] for v in points),max(v[1] for v in points)]
        assert box[0] > clip_pixels[0]+1 and box[1] > clip_pixels[1]+1, 'Projected support hits leading scissor edge'
        assert box[2] < clip_pixels[2]-1 and box[3] < clip_pixels[3]-1, 'Projected support hits trailing scissor edge'
        boxes[label] = box
    delta_ui = (4.*rx[1],4.*uy[1])
    return {'capture_path':str(png.resolve()),'capture_sha256':digest,
            'capture_metadata_path':str(sidecar.resolve()),
            'capture_metadata_sha256':hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            'actual_frame_pixels':pixels,'logical_screen':screen,'UI_to_frame_ratio_xy':ratios,
            'window_metadata':record['window'],
            'physical_screen_info':calibration['physical_screen_info'],
            'scene_props':props,'theme_scale':theme,'cell_unit':unit,
            'native_gui_scale':calibration['native_gui_scale'],
            'native_pose':calibration['native_pose'],'scene_scale':calibration['scene_scale'],
            'canvas_UI':canvas,'scissor_UI':clip_ui,'scissor_frame_pixels':clip_pixels,
            'projected_support_bounds_frame_pixels':boxes,
            'expected_delta_UI':delta_ui,
            'expected_delta_frame_pixels':tuple(delta_ui[i]*ratios[i] for i in range(2)),
            'calibration_basis':'Actual mounted Camera cache, UI control geometry and owned saved WGC frame dimensions.',
            'GPU_matrix_or_scissor_readback':False,
            'occupied_bounds_hypothesis_qualified':False,'pixels_qualified':False}

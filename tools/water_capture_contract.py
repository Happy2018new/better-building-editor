"""Pure camera/layout contracts for paired water captures."""
import math


def camera_matches(actual, expected):
    try:
        position = all(math.isfinite(actual['position'][i]) and math.isfinite(expected['position'][i])
                       and abs(actual['position'][i] - expected['position'][i]) < .02 for i in range(3))
        rotation = all(math.isfinite(actual['rotation'][i]) and math.isfinite(expected['rotation'][i])
                       and abs((actual['rotation'][i] - expected['rotation'][i] + 180.) % 360. - 180.) < .2
                       for i in range(3))
        viewport = (actual['screen'] == expected['screen'] and math.isfinite(actual['fov'])
                    and math.isfinite(expected['fov']) and abs(actual['fov'] - expected['fov']) < .0001)
    except (KeyError, IndexError, TypeError):
        return False
    return position and rotation and viewport


def calibrated_viewport_matches(camera, calibration):
    return (camera.get('screen') == calibration.get('engine_screen')
            and isinstance(camera.get('fov'), (float, int))
            and isinstance(calibration.get('reported_fov'), (float, int))
            and abs(camera['fov'] - calibration['reported_fov']) < .0001)


def scene_pose(state):
    keys = ('camera_pose', 'camera_pan', 'camera_depth', 'depth_plane', 'scene_origin', 'scene_size', 'screen_size')
    if not isinstance(state, dict) or any(key not in state for key in keys):
        return None
    return {key: state[key] for key in keys}


def scene_capture_state(state):
    result = scene_pose(state)
    if result is None or not isinstance(state.get('liquid_control_requests'), list):
        return None
    keys = ('key', 'geometry', 'visible', 'poses', 'doll_positions', 'doll_sizes')
    if any(not isinstance(row, dict) or any(key not in row for key in keys)
           for row in state['liquid_control_requests']):
        return None
    result['liquid_layout'] = [
        {key: row[key] for key in keys}
        for row in state['liquid_control_requests']]
    return result

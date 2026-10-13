"""Pure, strict contracts for independent item sprite capture controls."""
import hashlib
import json
import math
from pathlib import Path


def snapshot_sources(root):
    paths = [path for folder in ('behavior_pack', 'resource_pack')
             for path in (root / folder).rglob('*') if path.is_file()
             and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')]
    paths += list((root / 'tools').glob('*.py'))
    paths += list((root / 'tools/data').glob('*item*.json'))
    paths += [root / 'tools/data/block_registry_manifest.json']
    paths += list((root / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def snapshot_digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True,
                                    separators=(',', ':')).encode('ascii')).hexdigest()


def finite_tuple(value, count):
    return (isinstance(value, (list, tuple)) and len(value) == count
            and all(type(axis) in (int, float) and math.isfinite(axis) for axis in value))


def camera_matches(actual, expected):
    if not isinstance(actual, dict) or not isinstance(expected, dict):
        return False
    if any(not finite_tuple(row.get('position'), 3) or not finite_tuple(row.get('rotation'), 3)
           or not finite_tuple(row.get('screen'), 2) or type(row.get('fov')) not in (int, float)
           or not math.isfinite(row['fov']) or not 0 < row['fov'] < 180 for row in (actual, expected)):
        return False
    return (all(abs(actual['position'][i]-expected['position'][i]) < .02 for i in range(3))
            and all(abs((actual['rotation'][i]-expected['rotation'][i]+180.) % 360.-180.) < .2
                    for i in range(3)) and actual['screen'] == expected['screen']
            and abs(actual['fov']-expected['fov']) < .0001)


def scene_pose(state):
    keys = ('camera_pose', 'camera_pan', 'camera_depth', 'screen_size')
    if not isinstance(state, dict) or any(key not in state for key in keys):
        return None
    if (not finite_tuple(state['camera_pose'], 3) or not finite_tuple(state['camera_pan'], 2)
            or type(state['camera_depth']) not in (int, float) or not math.isfinite(state['camera_depth'])
            or not finite_tuple(state['screen_size'], 2) or min(state['screen_size']) <= 0):
        return None
    return {key: state[key] for key in keys}


def scene_layout(state):
    pose = scene_pose(state)
    if pose is None or not isinstance(state.get('banks'), list):
        return None
    rows = []
    for bank in state['banks']:
        keys = ('key', 'front', 'ids', 'poses', 'doll_positions', 'doll_sizes')
        if not isinstance(bank, dict) or any(key not in bank for key in keys):
            return None
        slot = bank['front']
        if type(slot) is not int or slot not in (0, 1):
            return None
        try:
            size, position, applied = (bank['doll_sizes'][slot], bank['doll_positions'][slot],
                                       bank['poses'][slot])
            if (not finite_tuple(size, 2) or min(size) <= 0 or not finite_tuple(position, 2)
                    or not finite_tuple(applied, 4) or applied[0] <= 0 or bank['ids'][slot] is None):
                return None
        except (IndexError, TypeError):
            return None
        rows.append({key: bank[key] for key in keys})
    pose['item_layout'] = rows
    return pose


def paired_layout_matches(positive, negative):
    first, second = scene_layout(positive), scene_layout(negative)
    return first is not None and first == second

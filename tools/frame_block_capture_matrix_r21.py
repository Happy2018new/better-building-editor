"""Validate bounded frame block rows while reusing one calibrated capture session."""
from copy import deepcopy
import math
import re


def matrix(orientations, manifest):
    if (manifest.get('schema') != 1 or manifest.get('production_qualified') is not False or
            not isinstance(manifest.get('cases'), list) or not 1 <= len(manifest['cases']) <= 96):
        raise ValueError('Frame block capture matrix requires 1-96 explicitly unqualified cases')
    indexed = {row['id']: row for row in orientations}
    result, seen = [], set()
    for request in manifest['cases']:
        label = request.get('id')
        item = request.get('item')
        angle = request.get('view_angle_degrees', 0.)
        enchanted = request.get('artificially_enchanted', False)
        orientation = indexed.get(request.get('orientation'))
        if (not isinstance(label, str) or not re.fullmatch('[a-zA-Z0-9_.-]+', label) or label in seen or
                not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str) or
                not item[0].startswith('minecraft:') or type(item[1]) is not int or item[1] < 0 or
                type(enchanted) is not bool or type(angle) not in (int, float) or
                not math.isfinite(angle) or abs(angle) > 85. or orientation is None or
                (angle and orientation['facing'] != 2)):
            raise ValueError('Invalid or duplicate frame block case: ' + repr(label))
        source = deepcopy(orientation)
        source.update(item=item[:], view_angle_degrees=float(angle),
                      artificially_enchanted=enchanted, empty_frame_control=True)
        result.append(('orientation.block.' + label, source))
        seen.add(label)
    return result

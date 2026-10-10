"""Perspective projection helper for live visual QA tools."""
import math


def _normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1e-9:
        raise ValueError('Camera basis is degenerate')
    return tuple(value / length for value in vector)


def project_points(points, position, target, screen, fov_degrees, roll_degrees=0.):
    """Project points using vertical FOV and a top-left screen origin."""
    width, height = (float(value) for value in screen)
    fov = float(fov_degrees)
    if width <= 0 or height <= 0 or not 0 < fov < 180:
        raise ValueError('Screen size and FOV must describe a perspective viewport')

    forward = _normalize(tuple(float(target[i]) - float(position[i]) for i in range(3)))
    right = _normalize((-forward[2], 0., forward[0]))
    up = _normalize((right[1] * forward[2] - right[2] * forward[1],
                     right[2] * forward[0] - right[0] * forward[2],
                     right[0] * forward[1] - right[1] * forward[0]))
    roll = math.radians(float(roll_degrees))
    right, up = (tuple(right[i] * math.cos(roll) + up[i] * math.sin(roll) for i in range(3)),
                 tuple(up[i] * math.cos(roll) - right[i] * math.sin(roll) for i in range(3)))
    focal = height / (2. * math.tan(math.radians(fov) / 2.))
    result = []
    for point in points:
        relative = tuple(float(point[i]) - float(position[i]) for i in range(3))
        depth = sum(relative[i] * forward[i] for i in range(3))
        if depth <= 1e-8:
            x = y = float('nan')
            visible = False
        else:
            x = width / 2. + focal * sum(relative[i] * right[i] for i in range(3)) / depth
            y = height / 2. - focal * sum(relative[i] * up[i] for i in range(3)) / depth
            visible = 0. <= x <= width and 0. <= y <= height
        result.append({'screenX': x, 'screenY': y, 'isInScreen': visible, 'depth': depth})
    return result


def project_box_corners(points, position, target, screen, fov_degrees,
                        roll_degrees=0., near=0.05):
    """Project a cuboid clipped against the camera near plane."""
    if len(points) != 8 or near <= 0:
        raise ValueError('A box requires eight corners and a positive near plane')
    projected = project_points(points, position, target, screen, fov_degrees, roll_degrees)
    depths = [row['depth'] for row in projected]
    visible = [points[index] for index, depth in enumerate(depths) if depth >= near]
    edges = ((0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
             (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7))
    for first, second in edges:
        first_depth, second_depth = depths[first], depths[second]
        if (first_depth < near) == (second_depth < near):
            continue
        ratio = (near - first_depth) / (second_depth - first_depth)
        visible.append(tuple(points[first][axis] + ratio *
                             (points[second][axis] - points[first][axis]) for axis in range(3)))
    return project_points(visible, position, target, screen, fov_degrees, roll_degrees)

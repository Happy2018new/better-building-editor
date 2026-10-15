"""Find isolated liquid silhouette candidates; never infer hidden corners.

The input is a caller-validated binary difference mask, not an arbitrary game
image. Capture identity, native snapshots and calibration remain separate gates.
"""
import math

from PIL import ImageChops, ImageDraw

from measure_native_liquid_surface import (
    CORNERS, measure_height, pixel_viewport, projected_pixels, vector)
from verify_missing_neighbor_visuals import hull


def visible_corners(camera, origin):
    """An elevated diagonal view exposes three outer top corners of one cell."""
    position = vector(camera['position'], 3, 'camera position')
    origin = vector(origin, 3, 'cell origin')
    if position[1] <= origin[1] + 1:
        raise ValueError('Silhouette diagnostics require an elevated camera')
    if any(origin[axis] <= position[axis] <= origin[axis] + 1 for axis in (0, 2)):
        raise ValueError('Silhouette diagnostics require a diagonal camera outside the cell')
    # The near top corner is an interior junction of top and side faces.
    interior = tuple(int(position[axis] > origin[axis] + 1) for axis in (0, 2))
    return tuple(corner for corner in CORNERS if corner != interior)


def bounded_mask(mask, camera, origin):
    """Keep the fixed projected unit cell, without image-dependent ROI fitting."""
    viewport = pixel_viewport(camera)
    if (mask.mode != 'L' or tuple(mask.size) != viewport['observation_screen'] or
            any(count for code, count in enumerate(mask.histogram()) if code not in (0, 255))):
        raise ValueError('A binary mask in the complete declared viewport is required')
    points = [(origin[0] + x, origin[1] + y, origin[2] + z)
              for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    projected = projected_pixels(points, camera, viewport)
    if any(not point['isInScreen'] or point['depth'] < .05 for point in projected):
        raise ValueError('The complete unit cell must be visible and in front of the near plane')
    polygon = hull((point['screenX'], point['screenY']) for point in projected)
    fixed = mask.copy()
    fixed.paste(0, (0, 0, mask.width, mask.height))
    ImageDraw.Draw(fixed).polygon(polygon, fill=255)
    return ImageChops.multiply(mask, fixed)


def silhouette(mask):
    """Use row endpoints to avoid expanding every interior pixel into a tuple."""
    bounds = mask.getbbox()
    if bounds is None:
        return ()
    x0, y0, x1, y1 = bounds
    pixels, points = mask.load(), []
    for y in range(y0, y1):
        occupied = [x for x in range(x0, x1) if pixels[x, y]]
        if occupied:
            # Pixel centres, rather than inclusive/exclusive box coordinates.
            points.extend(((occupied[0] + .5, y + .5), (occupied[-1] + .5, y + .5)))
    return tuple(hull(points))


def find_candidates(mask, camera, origin, pixel_budget=3., minimum_pixels=100):
    """Return only visible hull vertices near their known X/Z height lines.

    This is deliberately restricted to an isolated single-cell liquid mask.
    Neighboring liquid silhouettes and support/body pixels must be excluded by
    the caller's independent controls. A convex hull is not a corner detector
    for connected pools, waterlogged bodies or occluded scenes.
    """
    origin = vector(origin, 3, 'cell origin')
    budget = float(pixel_budget)
    if not math.isfinite(budget) or budget < 0 or minimum_pixels <= 0:
        raise ValueError('A finite nonnegative pixel budget and positive pixel minimum are required')
    visible = visible_corners(camera, origin)
    bounded = bounded_mask(mask, camera, origin)
    pixels = bounded.histogram()[255]
    vertices = silhouette(bounded) if pixels >= minimum_pixels else ()
    rows = []
    for corner in CORNERS:
        row = {'corner': corner, 'status': 'unobservable', 'reason': 'no_visible_hull_candidate'}
        if corner not in visible:
            row['reason'] = 'near_top_corner_is_interior_junction'
        elif pixels < minimum_pixels:
            row['reason'] = 'insufficient_independent_liquid_pixels'
        else:
            candidates = []
            for pixel in vertices:
                measured = measure_height(camera, (origin[0] + corner[0], origin[2] + corner[1]),
                                          origin[1], pixel, budget)
                if measured['status'] == 'diagnostic':
                    candidates.append((pixel, measured))
            if candidates:
                # A side's lower endpoint may share the same X/Z height line.
                pixel, measured = max(candidates, key=lambda item: item[1]['height_estimate'])
                row.update(status='candidate', reason=None, pixel=pixel, diagnostic=measured,
                           candidate_count=len(candidates))
        rows.append(row)
    return {'schema_version': 1, 'method': 'isolated_visible_silhouette_vertices',
            'cell_origin': origin, 'camera': camera, 'declared_pixel_budget': budget,
            'minimum_pixels': minimum_pixels, 'independent_mask_pixels': pixels,
            'hull': vertices, 'corners': rows,
            'native_geometry_accepted': False, 'accuracy_accepted': False,
            'public_controls_eligible': False,
            'limits': {'capture_binding_verified': False, 'native_snapshot_verified': False,
                       'calibration_verified': False, 'corner_assignment_requires_review': True,
                       'isolated_cell_required': True, 'hidden_corners_filled': False}}

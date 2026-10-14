"""Fit native cauldron top boundaries using an independently sampled camera.

The fitter has no cauldron height or inset constants. Its two unknowns are the
liquid elevation and symmetric footprint inset. Only the far boundary and its
adjacent side segments participate, so the near shell cannot bias the result.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize
from scipy.spatial import ConvexHull


def camera_matrix(points):
    rows, answers = [], []
    for point in points:
        xyz = np.array(point['local'] + [1.], dtype=float)
        u, v = (point['screen'][name] for name in ('screenX', 'screenY'))
        rows.append(np.r_[xyz, [0.] * 4, -u * xyz[:3]])
        answers.append(u)
        rows.append(np.r_[[0.] * 4, xyz, -v * xyz[:3]])
        answers.append(v)
    result = np.linalg.lstsq(rows, answers, rcond=None)[0]
    matrix = np.r_[result, 1.].reshape(3, 4)
    fitted = project(matrix, [point['local'] for point in points])
    observed = np.array([[p['screen']['screenX'], p['screen']['screenY']] for p in points])
    error = float(np.max(np.linalg.norm(fitted - observed, axis=1)))
    if error > .05:
        raise ValueError('Native camera projection samples are inconsistent: %.6f px' % error)
    return matrix, error


def project(matrix, points):
    xyz = np.c_[np.asarray(points), np.ones(len(points))]
    screen = xyz @ matrix.T
    return screen[:, :2] / screen[:, 2:]


def calibrate_pixels(folder, matrix):
    """Measure SDK-to-frame pixel offset with a real, ordinary full cube."""
    rgb = np.asarray(Image.open(folder / 'frame.png').convert('RGB'), dtype=np.int16)
    r, g, b = np.moveaxis(rgb, -1, 0)
    projected = project(matrix, [(x, y, z) for x in (0., 1.) for y in (0., 1.) for z in (0., 1.)])
    polygon = projected[ConvexHull(projected).vertices]
    low, high = projected.min(axis=0).astype(int)-5, projected.max(axis=0).astype(int)+5
    roi = np.zeros(r.shape, dtype=bool)
    roi[max(0, low[1]):high[1], max(0, low[0]):high[0]] = True
    mask = (r > g+20) & (r > b+20) & roi
    ys, xs = np.nonzero(mask)
    first, last = int(ys.min()), int(ys.max())
    boundary = []
    for y in range(first+2, last-1):
        positions = np.flatnonzero(mask[y])
        if len(positions):
            boundary.append((float(y), positions[0]-.5, positions[-1]+.5))

    def residual(offset):
        points = polygon + offset
        result = [3.*(points[:, 1].min()-(first-.5)), 3.*(points[:, 1].max()-(last+.5))]
        for y, left, right in boundary:
            crossings = []
            for a, b in zip(points, np.roll(points, -1, axis=0)):
                if min(a[1], b[1]) <= y < max(a[1], b[1]):
                    t = (y-a[1])/(b[1]-a[1])
                    crossings.append(a[0]+t*(b[0]-a[0]))
            if len(crossings) != 2:
                return [1000.] * (2+2*len(boundary))
            result.extend((min(crossings)-left, max(crossings)-right))
        return result

    fitted = optimize.least_squares(residual, (-.5, -3.), bounds=((-10.,-10.),(10.,10.)))
    corrected = matrix.copy()
    corrected[0] += fitted.x[0]*matrix[2]
    corrected[1] += fitted.x[1]*matrix[2]
    return corrected, {'source': str(folder), 'pixel_offset': fitted.x.tolist(),
                       'rms_pixels': float(np.sqrt(np.mean(np.square(residual(fitted.x))))),
                       'control': 'minecraft:red_concrete native unit cube',
                       'image_sha256': hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest()}


def liquid_mask(image, matrix, family):
    rgb = np.asarray(image.convert('RGB'), dtype=np.int16)
    r, g, b = np.moveaxis(rgb, -1, 0)
    if family == 'water':
        chromatic = (g > r + 5) & (b > g + 1)
    elif family == 'snow':
        chromatic = (np.minimum.reduce((r, g, b)) > 150) & (np.maximum.reduce((r, g, b))-np.minimum.reduce((r, g, b)) < 40)
    else:
        chromatic = (r > g + 10) & (g > b + 10)
    cube = project(matrix, [(x, y, z) for x in (0., 1.) for y in (0., 1.) for z in (0., 1.)])
    low, high = np.floor(cube.min(axis=0)).astype(int), np.ceil(cube.max(axis=0)).astype(int)
    roi = np.zeros(chromatic.shape, dtype=bool)
    roi[max(0, low[1]):high[1] + 1, max(0, low[0]):high[0] + 1] = True
    labels, count = ndimage.label(chromatic & roi)
    if not count:
        raise ValueError('No native liquid pixels detected')
    areas = np.bincount(labels.ravel())
    areas[0] = 0
    mask = labels == int(np.argmax(areas))
    if mask.sum() < 100:
        raise ValueError('Native liquid has too few visible pixels')
    return mask


def fit_far_boundary(mask, matrix):
    ys, xs = np.nonzero(mask)
    first, last = int(ys.min()), int(ys.max())
    # Record pixel-center positions; fitted edges lie halfway between the
    # first colored sample and its immediately adjacent uncolored sample.
    top = first - .5
    center_x = float(np.median(xs[ys == first]))
    middle = (first + last) // 2
    rows = []
    for y in range(first + 2, min(first + 18, middle)):
        positions = np.flatnonzero(mask[y])
        if len(positions) > 5:
            rows.append((float(y), positions[0] - .5, positions[-1] + .5))
    if len(rows) < 3:
        raise ValueError('Not enough unoccluded far-side boundary pixels')

    def corners(values):
        height, inset = values
        far = project(matrix, [(inset, height, 1.-inset), (1.-inset, height, 1.-inset)])
        near = project(matrix, [(inset, height, inset), (1.-inset, height, inset)])
        far = far[np.argsort(far[:, 0])]
        near = near[np.argsort(near[:, 0])]
        return np.array([far[0], far[1], near[1], near[0]])

    def residual(values):
        far_left, far_right, near_right, near_left = corners(values)
        result = [(min(far_left[1], far_right[1]) - top) * 3.]
        for y, left, right in rows:
            left_t = (y-far_left[1])/(near_left[1]-far_left[1])
            right_t = (y-far_right[1])/(near_right[1]-far_right[1])
            result.extend((far_left[0]+left_t*(near_left[0]-far_left[0])-left,
                           far_right[0]+right_t*(near_right[0]-far_right[0])-right))
        return result

    fit = optimize.least_squares(residual, (.5, .15), bounds=((.01, .001), (.999, .4)))
    height, inset = (float(v) for v in fit.x)
    error = float(np.sqrt(np.mean(np.square(residual(fit.x)))))
    if not fit.success or error > 1.:
        raise ValueError('Native top boundary did not fit: %.4f px' % error)
    return {'height': height, 'inset': inset,
            'boundary_rms_pixels': error,
            'far_edge_y': top, 'far_edge_center_x': center_x, 'observed_side_rows': rows,
            'surface_polygon': corners(fit.x).tolist(), 'colored_pixels': int(mask.sum())}


def analyze(folder, output, family, control=None):
    report = json.loads((folder / 'report.json').read_text())
    before, after = report['before'], report['after']
    if any(before[key] != after[key] for key in ('states', 'nbt', 'camera_position', 'camera_rotation')):
        raise ValueError('State or camera changed during capture')
    matrix, camera_error = camera_matrix(before['points'])
    pixel_calibration = None
    if control is not None:
        matrix, pixel_calibration = calibrate_pixels(control, matrix)
    image = Image.open(folder / 'frame.png').convert('RGB')
    mask = liquid_mask(image, matrix, family)
    fitted = fit_far_boundary(mask, matrix)
    fitted.update(schema=1, source=str(folder), native_states=before['states'],
                  camera_matrix=matrix.tolist(), camera_max_error_pixels=camera_error,
                  pixel_calibration=pixel_calibration,
                  image_sha256=hashlib.sha256((folder / 'frame.png').read_bytes()).hexdigest(),
                  method='camera-calibrated far-edge and side-segment least squares',
                  product_acceptance_claimed=False)
    output.mkdir(parents=True, exist_ok=False)
    Image.fromarray(np.uint8(mask) * 255).save(output / 'mask.png')
    overlay = image.copy()
    ImageDraw.Draw(overlay).polygon([tuple(p) for p in fitted['surface_polygon']], outline=(255, 0, 255), width=2)
    overlay.save(output / 'fit.png')
    (output / 'result.json').write_text(json.dumps(fitted, indent=2) + '\n')
    return fitted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--family', choices=('water', 'lava', 'snow'), default='water')
    parser.add_argument('--control', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.source, args.output, args.family, args.control), indent=2))


if __name__ == '__main__':
    main()

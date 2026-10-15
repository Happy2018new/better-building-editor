"""Compare observed portal pixels with the installed native shader equations.

Only animation phase and the documented diagnostic normal/texture conventions
are fitted. This is an investigation tool, not a renderer qualification gate.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

NORMALS = {'axis': (0., 0., -1.),
           'byte127': (-1./255., -1./255., -1.),
           'byte128': (1./255., 1./255., -1.)}
NORMALS.update({'inward_'+name: (normal[0], normal[1], -normal[2])
                for name, normal in list(NORMALS.items())})


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def surface_samples(image, camera, face='north', stride=2):
    screen = dict(camera['face_points'])[face]
    world = np.asarray(dict(camera['face_world_points'])[face], dtype=float)
    if not all(point['isInScreen'] for point in screen):
        raise ValueError('The measured face is not fully on screen')
    mask = Image.new('L', image.size)
    ImageDraw.Draw(mask).polygon([(point['screenX'], point['screenY']) for point in screen], fill=255)
    interior = np.asarray(mask.filter(ImageFilter.MinFilter(11))) != 0
    y, x = np.nonzero(interior)
    x, y = x[::stride], y[::stride]
    values = np.asarray(image.convert('RGB'))[y, x].astype(float)
    # Native magenta particles can pass in front of the otherwise opaque face.
    clear = ~((values[:, 0] > values[:, 1]*1.3+20) & (values[:, 2] > values[:, 1]+10))
    x, y, values = x[clear], y[clear], values[clear]
    if len(values) < 100:
        raise ValueError('Too few finite-surface pixels')
    equations, targets = [], []
    for point, (u, v) in zip(screen, ((0., 0.), (1., 0.), (1., 1.), (0., 1.))):
        sx, sy = point['screenX'], point['screenY']
        equations.extend(((sx, sy, 1., 0., 0., 0., -u*sx, -u*sy),
                          (0., 0., 0., sx, sy, 1., -v*sx, -v*sy)))
        targets.extend((u, v))
    transform = np.append(np.linalg.solve(np.asarray(equations), np.asarray(targets)), 1.).reshape(3, 3)
    mapped = transform @ np.asarray((x+.5, y+.5, np.ones(len(x))))
    u, v = mapped[:2] / mapped[2]
    points = (world[0] + u[:, None]*(world[1]-world[0]) +
              v[:, None]*(world[3]-world[0]))
    return points, values, x, y


def field_coordinates(points, camera, normal, depth_convention='unorm255'):
    eye = np.asarray(camera['position'])
    ray = points-eye
    denominator = ray @ normal
    depth_bytes = np.floor(np.arange(16)*255./16.)
    if depth_convention == 'float16':
        depths = (depth_bytes/255.).astype(np.float16).astype(float)*32.
    elif depth_convention == 'unorm256':
        depths = depth_bytes*(32./256.)
    else:
        depths = depth_bytes*(32./255.)
    t = 1.-depths[:, None]*float(normal @ normal)/denominator[None, :]
    parallax = t[:, :, None]*ray[None, :, :]+eye
    uv = parallax[:, :, :2]/16.
    angles = depths*np.pi*(5./7.)
    cosine, sine = np.cos(angles)[:, None], np.sin(angles)[:, None]
    tex_u = cosine*uv[:, :, 0]-sine*uv[:, :, 1]+cosine*depths[:, None]
    tex_v = sine*uv[:, :, 0]+cosine*uv[:, :, 1]+sine*depths[:, None]
    ix = np.floor(np.mod(tex_u, 1.)*256).astype(int)
    return ix, tex_v, depths


def predictions(field, starfield, colors, phase, flip_v=False):
    ix, tex_v, depths = field
    iy = np.floor(np.mod(tex_v+phase/256., 1.)*256).astype(int)
    if flip_v:
        iy = 255-iy
    lookup = colors.reshape(16, 3)[::-1]
    if flip_v:
        lookup = colors[::-1].reshape(16, 3)[::-1]
    sampled = starfield[iy, ix].astype(float)
    layers = np.rint(sampled*lookup[:, None, :]/255.*(1.-depths[:, None, None]/32.))
    return np.minimum(layers.sum(axis=0), 255.)


def fit(image, camera, starfield, colors, inward=False,
        depth_convention='unorm255', only_axis=False):
    points, actual, x, y = surface_samples(image, camera)
    candidates = []
    names = ('axis',) if only_axis else ('axis', 'byte127', 'byte128')
    if inward:
        names = tuple('inward_'+name for name in names)
    for normal_name in names:
        normal = np.asarray(NORMALS[normal_name])
        field = field_coordinates(points, camera, normal, depth_convention)
        for flip in (False, True):
            best = None
            for phase in range(256):
                expected = predictions(field, starfield, colors, phase, flip)
                error = float(np.mean((expected-actual)**2))
                if best is None or error < best['mse']:
                    best = {'phase': float(phase), 'mse': error}
            phase_center = best['phase']
            for phase in np.arange(phase_center-1., phase_center+1.001, .125):
                expected = predictions(field, starfield, colors, float(phase), flip)
                error = float(np.mean((expected-actual)**2))
                if error < best['mse']:
                    best = {'phase': float(phase) % 256., 'mse': error}
            expected = predictions(field, starfield, colors, best['phase'], flip)
            delta = np.abs(expected-actual)
            candidates.append(dict(best, normal=normal_name, flip_v=flip,
                                   depth_convention=depth_convention,
                                   rmse=float(np.sqrt(best['mse'])),
                                   rgb_mae=delta.mean(axis=0).tolist(),
                                   rgb_actual_mean=actual.mean(axis=0).tolist(),
                                   rgb_expected_mean=expected.mean(axis=0).tolist(),
                                   error_p95=float(np.percentile(delta, 95))))
    candidates.sort(key=lambda row: row['mse'])
    return {'sample_pixels': len(actual), 'best': candidates[0], 'conventions': candidates,
            'qualification': False,
            'limits': ['Animation phase is fitted and is not an independent clock measurement.',
                       'The north-face CPU equations investigate coordinate/attribute conventions.',
                       'A fit does not replace live lifecycle, UI, missing or opacity checks.']}


def comparison(image, camera, starfield, colors, best, output):
    points, actual, x, y = surface_samples(image, camera, stride=1)
    field = field_coordinates(points, camera, np.asarray(NORMALS[best['normal']]),
                              best.get('depth_convention', 'unorm255'))
    expected = predictions(field, starfield, colors, best['phase'], best['flip_v'])
    left, top, right, bottom = int(x.min()), int(y.min()), int(x.max())+1, int(y.max())+1
    size = (bottom-top, right-left, 3)
    panels = [np.full(size, 48, dtype=np.uint8) for _ in range(3)]
    for panel, values in zip(panels, (actual, expected, np.abs(actual-expected))):
        panel[y-top, x-left] = np.clip(values, 0, 255).astype(np.uint8)
    width, height = right-left, bottom-top
    result = Image.new('RGB', (width*3, height+24), (48, 48, 48))
    draw = ImageDraw.Draw(result)
    for index, (panel, label) in enumerate(zip(panels, ('Observed', 'CPU prediction', 'Absolute error'))):
        result.paste(Image.fromarray(panel), (index*width, 24))
        draw.text((index*width+4, 5), label, fill=(255, 255, 255))
    result.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--capture', default='end_gateway_native_front')
    parser.add_argument('--native-data', type=Path, default=Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/data'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-fit', type=Path,
                        help='Reuse a bound diagnostic fit to render its comparison without refitting')
    parser.add_argument('--inward', action='store_true',
                        help='Investigate the opposite native normal convention')
    parser.add_argument('--depth-convention', choices=('unorm255', 'float16', 'unorm256'),
                        default='unorm255', help='Investigate lowp conversion before UV calculation')
    parser.add_argument('--only-axis', action='store_true',
                        help='Investigate one normal convention without the two neutral-byte alternatives')
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    row = report['captures'][args.capture]
    path = args.report.parent / Path(row['capture']['path']).name
    if sha(path) != row['capture']['sha256']:
        raise ValueError('The bound capture changed')
    star_path = args.native_data / 'resource_packs/vanilla/textures/entity/end_portal.png'
    color_path = args.native_data / 'resource_packs/vanilla/textures/environment/end_portal_colors.png'
    with Image.open(star_path) as image:
        stars = np.asarray(image.convert('RGB'))
    with Image.open(color_path) as image:
        colors = np.asarray(image.convert('RGB'))
    with Image.open(path) as image:
        if args.reuse_fit:
            result = json.loads(args.reuse_fit.read_bytes())
            if (result['capture_sha256'] != sha(path) or
                    result['source_report_sha256'] != sha(args.report)):
                raise ValueError('The reused fit belongs to different evidence')
            result['reused_fit_sha256'] = sha(args.reuse_fit)
        else:
            result = fit(image, row['camera'], stars, colors, args.inward,
                         args.depth_convention, args.only_axis)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        preview = args.output.with_suffix('.png')
        comparison(image, row['camera'], stars, colors, result['best'], preview)
    result.update(capture=args.capture, source_report_sha256=sha(args.report),
                  capture_sha256=sha(path), host_sha256=sha(Path(__file__)),
                  native_shader_sha256={name: sha(args.native_data / 'shaders/glsl' / name)
                                        for name in ('end_portal.vertex', 'end_portal.fragment')},
                  texture_sha256={str(star_path): sha(star_path), str(color_path): sha(color_path)})
    result['comparison'] = {'path': str(preview), 'sha256': sha(preview)}
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'capture': args.capture, 'best': result['best'], 'qualification': False}))


if __name__ == '__main__':
    main()

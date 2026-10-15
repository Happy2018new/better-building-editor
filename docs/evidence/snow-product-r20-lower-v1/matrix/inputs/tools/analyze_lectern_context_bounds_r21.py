"""Record the retained west lectern discrepancy and native overhang evidence.

This is an offline diagnostic. The experimental native geometry is a resource
reference, not proof that the installed hardcoded world renderer uses it.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.model import Document
from projection.cell import foreground, actor_data
from projection.geometry_palette import prepare_palette
from projection.book_render_plan import appearance
from projection.block_registry import states


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rotated_bounds(cube, sign):
    origin, size = cube['origin'], cube['size']
    pivot = np.asarray(cube.get('pivot', [0., 0., 0.]), dtype=float)
    points = np.asarray(list(itertools.product(*[(origin[i], origin[i]+size[i])
                                                for i in range(3)]))) - pivot
    for axis, degrees in enumerate(cube.get('rotation', [0., 0., 0.])):
        angle = math.radians(degrees) * sign
        a, b = ((1, 2), (2, 0), (0, 1))[axis]
        first, second = points[:, a].copy(), points[:, b].copy()
        points[:, a] = first*math.cos(angle)-second*math.sin(angle)
        points[:, b] = first*math.sin(angle)+second*math.cos(angle)
    points += pivot
    points = (points + [8., 0., 8.]) / 16.
    return {'minimum': points.min(axis=0).tolist(), 'maximum': points.max(axis=0).tolist(),
            'corners_outside_unit_cell': int(((points < 0.) | (points > 1.)).any(axis=1).sum())}


def analyze(args):
    args.output.mkdir(parents=True, exist_ok=False)
    report = json.loads(args.report.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Need the complete restored comparison')
    if report.get('cleanup_errors'):
        raise ValueError('Comparison cleanup failed')
    row = report['rows']['lectern.book']
    doc = Document.from_data(row['document'])
    cell = doc.get((3, 3, 3))
    material = foreground(cell)
    palette = prepare_palette(doc.palette_data())
    if row['used']['block'] != dict(name=material[0], aux=material[1]):
        raise ValueError('World and candidate document use different materials')
    selected = {}
    camera = None
    for family in ('native', 'candidate'):
        label = family+'_lectern.book_motion0'
        capture = report['captures'][label]
        for sample in (capture['before'], capture['after']):
            signature = {key: sample[key] for key in ('camera', 'rotation', 'screen', 'foot')}
            if camera is None:
                camera = signature
            if signature != camera:
                raise ValueError('The retained cameras differ')
        receipt = capture['capture']
        path = Path(receipt['path'])
        if receipt.get('reliable') is not True or sha(path) != receipt['sha256']:
            raise ValueError('Changed or unreliable retained capture')
        with Image.open(path) as image:
            bounds = (image.width//2-180, image.height//2-150,
                      image.width//2+180, image.height//2+95)
            crop = image.convert('RGB').crop(bounds)
        crop_path = args.output/(family+'.png')
        crop.save(crop_path)
        pixels = np.asarray(crop).astype(int)
        r, g, b = np.moveaxis(pixels, -1, 0)
        mask = (r > g) & (g > b)
        columns = (60, 80, 90, 100, 110, 120, 140, 160, 180, 200, 240, 280, 310)
        selected[family] = {'source': str(path), 'source_sha256': receipt['sha256'],
            'crop_bounds': bounds, 'crop_sha256': sha(crop_path),
            'top_outline_crop_pixels': {str(x): int(np.flatnonzero(mask[:, x])[0])
                                       for x in columns if mask[:, x].any()}}
    native_model = json.loads(args.native_geometry.read_bytes())
    bounds = []
    for geometry in native_model['minecraft:geometry']:
        for bone in geometry['bones']:
            for cube in bone.get('cubes', []):
                if any(cube.get('rotation', [])):
                    bounds.append({'bone': bone['name'], 'origin': cube['origin'],
                        'size': cube['size'], 'rotation': cube['rotation'], 'pivot': cube['pivot'],
                        'right_handed': rotated_bounds(cube, 1),
                        'opposite_angle_sign_control': rotated_bounds(cube, -1)})
    fragment_relative = 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment'
    fragment = args.project/fragment_relative
    shader = fragment.read_text(encoding='ascii')
    context_test = ('any(lessThan(renderContext.xyz,vec3(0.9999))) ||' in shader and
                    'any(greaterThan(renderContext.xyz,vec3(2.0001))))) discard;' in shader)
    if not context_test:
        raise ValueError('The inspected context-center clipping predicate changed')
    original_sources = report.get('installed_sources', {})
    original_fragment_hash = next((original_sources.get(section, {}).get(fragment_relative)
                                   for section in ('files', 'body_files', 'owner_files')
                                   if fragment_relative in original_sources.get(section, {})), None)
    if original_fragment_hash is not None and original_fragment_hash != sha(fragment):
        raise ValueError('The inspected fragment differs from the original source snapshot')
    sheet = Image.new('RGB', (720, 269), '#252525')
    draw = ImageDraw.Draw(sheet)
    for index, family in enumerate(('native', 'candidate')):
        with Image.open(args.output/(family+'.png')) as crop:
            sheet.paste(crop, (index*360, 24))
        draw.text((index*360+4, 5), family+' west lectern, retained R20 frame', fill='white')
    sheet.save(args.output/'review.png')
    result = {'schema': 1, 'production_qualified': False, 'offline_only': True,
        'hypothesis': 'Packed context center-cell clipping removes lectern body overhang; '
                      'unclipped live/roundtrip/prepared versus public context control is still required.',
        'source_report': str(args.report.resolve()), 'report_sha256': sha(args.report),
        'tool_sha256': sha(Path(__file__)), 'camera': camera,
        'world_material': row['used']['block'], 'world_states': row['used']['states'],
        'document_material': material, 'document_states': states(material),
        'prepared_material_states': [(value, palette['states'].get(value))
                                     for value in palette['common']],
        'book_pose': appearance(material, actor_data(cell), report['engine']),
        'candidate_projection_parts': report['captures']['candidate_lectern.book_motion0']['before']['projection']['parts'],
        'context_fragment': str(fragment.resolve()), 'context_fragment_sha256': sha(fragment),
        'context_fragment_hash_in_original_report': original_fragment_hash,
        'context_center_clip_present': context_test,
        'native_geometry': str(args.native_geometry.resolve()),
        'native_geometry_sha256': sha(args.native_geometry), 'native_rotated_cube_bounds': bounds,
        'captures': selected,
        'limits': ['Experimental native JSON geometry is only a resource reference for overhang.',
                   'Both angle signs are shown; this tool does not resolve Bedrock rotation convention.',
                   'The original report does not attest unlisted shared shaders; the new runtime control must bind them.',
                   'Outline masks describe the retained silhouette, not page, pose or product acceptance.',
                   'The matched north frontal page qualification is not widened.']}
    (args.output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({key: result[key] for key in ('production_qualified', 'offline_only',
          'world_material', 'book_pose', 'context_center_clip_present', 'native_rotated_cube_bounds')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--native-geometry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    analyze(parser.parse_args())

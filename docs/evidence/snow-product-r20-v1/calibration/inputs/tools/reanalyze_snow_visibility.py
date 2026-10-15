"""Recheck saved native/editor snow captures without starting or modifying MC."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

from verify_snow_plant_visibility import capture_frame, compare_native, scope_checks


def stored_geometry(record, size):
    if record is None:
        return None
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).polygon(record['polygon'], fill=255)
    return mask


def stored_upper(record, size):
    if record is None:
        return {}
    result = {}
    for height, row in record.items():
        path = Path(row['mask'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('The saved upper-texel geometry mask changed: %s' % path)
        with Image.open(path) as source:
            result[int(height)] = source.convert('L')
        if result[int(height)].size != size:
            raise ValueError('The upper-texel geometry dimensions changed')
    return result


def reanalyze(source):
    raw = source.read_bytes()
    saved = json.loads(raw)
    if not saved.get('completed') or not saved.get('restored') or not saved.get('native_reference', {}).get('captured'):
        raise ValueError('A complete restored native-reference capture is required')
    plants = tuple(dict.fromkeys(row['plant'] for row in saved['rows']))
    heights = sorted({row['height'] for row in saved['rows'] if row['kind'] == 'covered'})
    blank = {row['plant']: row['editor']['path'] for row in saved['rows'] if row['kind'] == 'blank'}
    frames = {'editor': {}, 'projection': {}}
    rows = []
    for row in saved['rows']:
        plant, kind, height = row['plant'], row['kind'], row['height']
        if kind == 'blank':
            continue
        editor_crop = row['editor_pixels']['crop']
        editor_size = (editor_crop[2]-editor_crop[0], editor_crop[3]-editor_crop[1])
        editor = capture_frame(row['editor']['path'], editor_crop, blank[plant],
                               geometry=stored_geometry(row.get('editor_geometry'), editor_size))
        editor['above_snow'] = stored_upper(row.get('upper_geometry'), editor_size)
        crop = row['world_pixels']['crop']
        roi = stored_geometry(row.get('world_roi'), (crop[2]-crop[0], crop[3]-crop[1]))
        projection = capture_frame(row['world']['screenshot']['path'], crop,
                                   row['world']['hidden_screenshot']['path'], segmented=True, roi=roi)
        native = capture_frame(row['native']['screenshot']['path'], crop,
                               row['native']['hidden_screenshot']['path'], segmented=True, roi=roi)
        frames['editor'][(plant, kind, height)] = editor
        frames['projection'][(plant, kind, height)] = projection
        rows.append({'plant': plant, 'kind': kind, 'height': height,
                     'native_comparison': compare_native(native, projection, foliage=kind != 'snow')})
    scopes = {name: scope_checks(values, plants, heights) for name, values in frames.items()}
    scopes['projection']['semantic_controls'] = dict(scopes['projection'])
    scopes['projection']['passed'] = set(heights) == {0, 5} and all(row['native_comparison']['passed'] for row in rows)
    return {'schema_version': 1, 'source': str(source.resolve()),
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'source_runtime_reference': saved.get('runtime_reference'),
            'runtime_reference_passed': saved.get('runtime_reference_passed', False),
            'scopes': scopes, 'rows': rows,
            'passed': saved.get('runtime_reference_passed', False) and all(scope['passed'] for scope in scopes.values()),
            'scope': 'Offline reanalysis of unchanged screenshots with the current mask; no new runtime or visual evidence is created.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = reanalyze(args.source)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'report': str(args.output.resolve()), 'passed': report['passed'],
                      'editor_passed': report['scopes']['editor']['passed'],
                      'projection_passed': report['scopes']['projection']['passed']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

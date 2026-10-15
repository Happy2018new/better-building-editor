"""Preserve a small, hashed review set without copying source ZIPs or bursts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image, ImageDraw

from analyze_product_water import expected_mask

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / 'docs/evidence/water-production-final310-r15-v1'
BIOME = ROOT / 'docs/evidence/water-production-biome310-r15-v1'
PURE = ROOT / 'docs/evidence/water-production-fixed310-r15-v1'


def file_row(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh review set')
    args.output.mkdir(parents=True)
    selected = {
        'alpha-analysis.json': FINAL / 'alpha-analysis.json',
        'direction-analysis.json': FINAL / 'changed-owner-directions-analysis.json',
        'biome-analysis.json': BIOME / 'analysis-v3.json',
        'biome-initial-80pct-analysis.json': BIOME / 'analysis-v2.json',
        'pure-geometry-analysis.json': PURE / 'pure-only-analysis.json',
        'alpha-summary.json': FINAL / 'compact/summary.json',
        'alpha-contact.png': FINAL / 'compact/alpha-contact.png',
        'body-contact.png': FINAL / 'compact/body-contact.png',
        'biome-contact.png': BIOME / 'biome-contact.png',
        'alpha-launch-inputs.json': FINAL / 'launch-inputs.json',
        'biome-launch-inputs.json': BIOME / 'launch-inputs-host-v2.json',
    }
    index = {'schema': 1, 'copied_sources': {}, 'external_sources': {}, 'captures': {},
             'scope': 'Review derivatives and measured results; not a standalone raw replay package',
             'limitations': ['Full source ZIPs and burst PNGs remain outside this compact set.',
                             'All live runs install candidate profiles explicitly, not enabled production defaults.',
                             'East/falling world motion is newly tested; remaining cardinal world checks are historical.',
                             'Side UV continuity has no new quantitative acceptance in this review.']}
    for name, source in selected.items():
        shutil.copy2(source, args.output / name)
        index['copied_sources'][name] = file_row(source)
    reports = {'alpha': FINAL / 'alpha.json', 'direction': FINAL / 'changed-owner-directions.json',
               'editor_pure': FINAL / 'editor-pure-source.json',
               'missing_pure': FINAL / 'missing-pure-pool.json', 'biome': BIOME / 'report-v2.json'}
    outcome = {'schema': 1, 'reports': {}, 'pure_occupancy': None}
    loaded = {}
    for name, path in reports.items():
        source = loaded[name] = json.loads(path.read_bytes())
        index['external_sources'][name] = file_row(path)
        outcome['reports'][name] = {key: source.get(key) for key in
            ('completed', 'restored', 'source_unchanged', 'source_contract_sha256', 'session_binding',
             'frozen', 'routes', 'cases', 'controls', 'fixture_without_supports', 'error', 'cleanup_errors')}
        for label, capture in source['captures'].items():
            path = Path(capture['path'])
            current = file_row(path)
            if current['sha256'] != capture['sha256']:
                raise ValueError('Capture changed: ' + str(path))
            receipt = path.with_suffix('.capture.json')
            index['captures'][name + ':' + label] = dict(current, included=False,
                receipt=file_row(receipt) if receipt.exists() else None,
                captured_size=[capture['width'], capture['height']])
    for name, path in (('alpha_source_archive', FINAL / 'production-sources.zip'),
                       ('biome_source_archive', BIOME / 'production-sources-host-v2.zip')):
        index['external_sources'][name] = dict(file_row(path), included=False)
    for name, path in (('alpha_camera', FINAL / 'camera.json'), ('biome_camera', BIOME / 'camera.json'),
                       ('failed_biome_batch', BIOME / 'report.json')):
        index['external_sources'][name] = file_row(path)
    pool = loaded['missing_pure']
    outcome['pure_occupancy'] = {name: pool['extra_rows']['missing_pool_wet_' + name]['occupancy']
                               for name in ('occupied', 'restored')}
    sheet = Image.new('RGB', (1000, 300), 'white')
    draw = ImageDraw.Draw(sheet)
    controls = (('editor pure', loaded['editor_pure'], 'editor_source_wet'),
                ('missing four cells', pool, 'missing_pool_wet'),
                ('occupied cell hidden', pool, 'missing_pool_wet_occupied'),
                ('cleared cell restored', pool, 'missing_pool_wet_restored'))
    for column, (title, source, label) in enumerate(controls):
        capture = source['captures'][label]
        baseline_label = label.replace('_occupied', '').replace('_restored', '')
        mask = expected_mask(source['rows'][baseline_label], source, (capture['width'], capture['height']))
        ys, xs = np.nonzero(mask)
        crop = (int(xs.min()) - 24, int(ys.min()) - 24, int(xs.max()) + 25, int(ys.max()) + 90)
        with Image.open(capture['path']) as image:
            tile = image.convert('RGB').crop(crop)
            tile.thumbnail((240, 270), Image.Resampling.NEAREST)
            sheet.paste(tile, (column * 250 + (250 - tile.width) // 2, 24))
        draw.text((column * 250 + 5, 6), title, fill='black')
        index['captures'][title] = dict(file_row(Path(capture['path'])), crop=crop, included=False)
    sheet.save(args.output / 'pure-water-contact.png')
    (args.output / 'outcome.json').write_text(json.dumps(outcome, sort_keys=True, indent=2) + '\n', encoding='ascii')
    index['files'] = {path.name: {'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(args.output.iterdir()) if path.is_file()}
    (args.output / 'index.json').write_text(json.dumps(index, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'files': len(index['files']), 'bytes': sum(row['bytes'] for row in index['files'].values())}))


if __name__ == '__main__':
    main()

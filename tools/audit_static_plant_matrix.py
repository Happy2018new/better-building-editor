"""Audit original static-plant PNGs using the background capture contract."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps, ImageStat

from verify_fungus_remaining_matrix import ROOT, captures, digest, record, source_errors
from verify_debug_blueprints import write_json


def capture_status(capture, matrix):
    metadata = capture['capture']
    key = str(Path(capture['path']).resolve())
    errors = []
    if digest(Path(capture['path'])) != capture['sha256']:
        errors.append(key+': original PNG changed')
    flags = ('ok', 'reliable', 'background_only', 'native_resolution', 'background_safe')
    if not all(metadata.get(flag) for flag in flags):
        errors.append(key+': background capture gate failed')
    frame = metadata['frame']
    with Image.open(capture['path']) as image:
        if image.format != 'PNG' or image.size != (frame['width'], frame['height']):
            errors.append(key+': native PNG encoding or dimensions changed')
        if max(ImageStat.Stat(image.convert('RGB')).var) <= 1.:
            errors.append(key+': native PNG is blank')
    if frame['frame_qpc_100ns'] <= frame['request_qpc_100ns']:
        errors.append(key+': frame predates request')
    if metadata['game_pid'] != matrix['game_pid'] or metadata['owner'] != matrix['owner']:
        errors.append(key+': capture ownership differs')
    before, after = metadata['foreground_before'], metadata['foreground_after']
    if before['pid'] == matrix['game_pid'] or after['pid'] == matrix['game_pid']:
        errors.append(key+': the owned game was foreground')
    switch = None
    if before != after:
        switch = {'path': key, 'foreground_before': before,
                  'foreground_after': after, 'background_safe': metadata['background_safe'],
                  'reliable': metadata['reliable'],
                  'classification': 'Allowed ordinary switching between other applications' if not errors else 'Untrusted capture; errors retained'}
    return errors, switch


def audit(matrix_path, output, inspection_dir=None, source_root=ROOT, source_archive=None):
    if output.exists():
        raise ValueError('Audit output must be fresh')
    matrix = json.loads(matrix_path.read_bytes())
    errors, images, sheets, reports, switches = [], {}, [], [], []
    for case in matrix['rows']:
        path = Path(case['path'])
        if digest(path) != case['sha256']:
            raise ValueError('Original plant report changed')
        value = json.loads(path.read_bytes())
        reports.append(dict(record(path), **{key: value.get(key) for key in
                        ('plants', 'view', 'heights', 'native_target', 'completed', 'restored', 'passed',
                         'scopes', 'cleanup_errors', 'binding_read_failures')}))
        if value['cleanup_errors'] or not all(row['clean'] for row in value['native_cleanup']):
            errors.append(str(path)+': native cleanup is incomplete')
        if value['limits'] != {'native_recall': .75, 'native_precision': .75,
                               'native_edge_tolerance_pixels': 3}:
            errors.append(str(path)+': original pixel gates changed')
        for capture in captures(value):
            image_path = Path(capture['path'])
            key = str(image_path.resolve())
            if key in images:
                if images[key] != capture['sha256']:
                    errors.append(key+': duplicate capture hash differs')
                continue
            images[key] = capture['sha256']
            capture_errors, switch = capture_status(capture, matrix)
            errors.extend(capture_errors)
            if switch:
                switches.append(switch)
        rows = [row for row in value['rows'] if row['kind'] != 'blank']
        for row in rows:
            for mask in row['masks'].values():
                if digest(Path(mask['path'])) != mask['sha256']:
                    errors.append(mask['path']+': verdict mask changed')
        inspect = [row for row in rows if row['kind'] in ('plant', 'covered')]
        width, height = 420, 250
        sheet = Image.new('RGB', (width*4, len(inspect)*(height+28)), 'white')
        draw = ImageDraw.Draw(sheet)
        for index, row in enumerate(inspect):
            cells = [('native', row['native']['screenshot'], row['crop'])]
            cells.extend((mode, row['world'][mode]['screenshot'], row['crop']) for mode in ('full', 'missing'))
            cells.append(('editor', row['editor'], row['editor_crop']))
            for column, (label, capture, crop) in enumerate(cells):
                with Image.open(capture['path']) as image:
                    preview = ImageOps.contain(image.convert('RGB').crop(tuple(crop)), (width, height))
                x, y = column*width, index*(height+28)
                draw.text((x+8, y+8), '%s %s %s h%d %s' %
                          (row['plant'], value['view'], row['kind'], row['height'], label), fill='black')
                sheet.paste(preview, (x+(width-preview.width)//2, y+28))
        sheet_path = (inspection_dir/path.name if inspection_dir is not None else path).with_name(
            path.stem+'_inspect.png')
        if sheet_path.exists():
            raise ValueError('Inspection PNG must be fresh')
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(sheet_path)
        sheets.append(dict(record(sheet_path), inspection_only=True, rows=len(inspect)))
    frozen_path = Path(matrix['frozen_source']['path'])
    if digest(frozen_path) != matrix['frozen_source']['sha256']:
        errors.append('Frozen source manifest changed')
    frozen = json.loads(frozen_path.read_bytes())
    errors.extend('Frozen source changed: '+name for name in
                  source_errors(frozen, root=source_root, archive=source_archive))
    result = {'schema': 1, 'matrix': record(matrix_path), 'integrity_passed': not errors,
              'errors': errors, 'matrix_completed': matrix['completed'],
              'matrix_restored': matrix['restored'], 'matrix_passed': matrix['passed'],
              'capture_contract_source': record(Path(__file__).resolve().parents[1]/'tools/capture_native_window.py'),
              'capture_contract': 'Reliable nonblank owner-bound fresh frame; owned game is background before and after; ordinary switching between other applications is allowed',
              'foreground_changes_are_diagnostics': True, 'foreground_change_observations': switches,
              'frozen_source_root': str(source_root.resolve()),
              'source_archive': str(source_archive.resolve()) if source_archive is not None else None,
              'frozen_source_files_audited': len(frozen['hashes_sha256']),
              'unique_native_pngs_audited': len(images), 'reports': reports, 'inspection_sheets': sheets}
    write_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--inspection-dir', type=Path,
                        help='Write fresh contact sheets outside the original artifact directory')
    parser.add_argument('--frozen-source-root', type=Path, default=ROOT,
                        help='Original project root used for exact frozen-source checks')
    parser.add_argument('--source-archive', type=Path,
                        help='Exact original files preserved before restoring candidate resources')
    args = parser.parse_args()
    value = audit(args.matrix, args.output, args.inspection_dir,
                  args.frozen_source_root, args.source_archive)
    print(json.dumps({key: value[key] for key in
                      ('integrity_passed', 'errors', 'matrix_completed', 'matrix_restored',
                       'matrix_passed', 'unique_native_pngs_audited', 'foreground_change_observations',
                       'inspection_sheets')}, ensure_ascii=True), flush=True)
    return 0 if value['integrity_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

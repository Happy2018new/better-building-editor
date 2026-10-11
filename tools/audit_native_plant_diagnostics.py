"""Audit original background plant diagnostics and produce inspection-only sheets."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageOps

from audit_static_plant_matrix import capture_status
from verify_debug_blueprints import write_json
from verify_fungus_remaining_matrix import captures, digest, record, source_errors


def hashed_artifacts(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            yield value
        for child in value.values():
            yield from hashed_artifacts(child)
    elif isinstance(value, list):
        for child in value:
            yield from hashed_artifacts(child)


def inspection_sheet(report, report_path):
    rows = report.get('rows', [])
    rows = [row for row in rows if 'native' in row and 'paths' in row]
    if not rows:
        return None
    width, height, caption = 500, 300, 24
    sheet = Image.new('RGB', (width*2, len(rows)*(height+caption)), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        cells = (('native', row['native']['screenshot']),
                 ('direct_world', row['paths']['direct_world']['shown']))
        for column, (label, capture) in enumerate(cells):
            with Image.open(capture['path']) as image:
                preview = ImageOps.contain(image.convert('RGB').crop(tuple(row['crop'])),
                                           (width, height))
            x, y = column*width, index*(height+caption)
            draw.text((x+8, y+5), '%s %s %s' % (row['plant'], row['view'], label), fill='black')
            sheet.paste(preview, (x+(width-preview.width)//2, y+caption))
    path = report_path.with_name(report_path.stem+'_inspection.png')
    if path.exists():
        raise ValueError('Inspection PNG must be fresh')
    sheet.save(path)
    return dict(record(path), inspection_only=True)


def audit(report_paths, output):
    if output.exists():
        raise ValueError('Audit output must be fresh')
    errors, images, artifacts, reports, switches, sheets = [], {}, {}, [], [], []
    for report_path in report_paths:
        report = json.loads(report_path.read_bytes())
        reports.append(dict(record(report_path), completed=report['completed'],
                            restored=report['restored'], passed=report.get('passed')))
        if not report['completed'] or not report['restored'] or report.get('cleanup_errors'):
            errors.append(str(report_path)+': original diagnostic is incomplete or unrestored')
        values = list(captures(report))
        identity = report if 'game_pid' in report else values[0]['capture']
        for capture in values:
            key = str(Path(capture['path']).resolve())
            if key in images:
                if images[key] != capture['sha256']:
                    errors.append(key+': duplicate original capture hash differs')
                continue
            images[key] = capture['sha256']
            capture_errors, switch = capture_status(capture, identity)
            errors.extend(capture_errors)
            if capture['capture']['session_file'] != report['session_file']:
                errors.append(key+': capture session differs')
            if switch:
                switches.append(switch)
        for artifact in hashed_artifacts(report):
            path = Path(artifact['path'])
            key = str(path.resolve())
            if key in artifacts and artifacts[key] != artifact['sha256']:
                errors.append(key+': duplicate original artifact hash differs')
            artifacts[key] = artifact['sha256']
            if digest(path) != artifact['sha256']:
                errors.append(key+': original hashed artifact changed')
        if 'frozen_source' in report:
            frozen = json.loads(Path(report['frozen_source']['path']).read_bytes())
            errors.extend('Frozen asset source changed: '+name for name in source_errors(frozen))
        sheet = inspection_sheet(report, report_path)
        if sheet:
            sheets.append(sheet)
    result = {'schema': 1, 'integrity_passed': not errors, 'errors': errors,
              'reports': reports, 'unique_native_pngs_audited': len(images),
              'hashed_artifacts_audited': len(artifacts), 'inspection_sheets': sheets,
              'foreground_changes_are_diagnostics': True,
              'foreground_change_observations': switches,
              'scope': 'Original captures, masks and reports only; failed mesh verdicts remain failed'}
    write_json(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    value = audit(args.report, args.output)
    print(json.dumps(value), flush=True)
    return 0 if value['integrity_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

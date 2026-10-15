"""Verify capture receipts and compare badges to matched native-shell controls."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker_difference(picture, control, label):
    """Inspect the declared focus cell, excluding moving terrain and support blocks."""
    if picture.size != control.size:
        raise ValueError('Badge/control dimensions differ')
    bounds = ((940, 580, 1070, 700) if label.startswith('editor_')
              else (900, 500, 1110, 700))
    width, height = picture.size
    box = tuple(round(value * (width / 1994. if index % 2 == 0 else height / 1105.))
                for index, value in enumerate(bounds))
    a = np.asarray(picture.crop(box), dtype=np.int16)
    b = np.asarray(control.crop(box), dtype=np.int16)
    difference = np.abs(a - b).max(axis=2) > 12
    red, green, blue = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    if '_empty_' in label:
        colored = (a.min(axis=2) > 100) & (a.mean(axis=2) > b.mean(axis=2) + 12)
    elif '_unknown_' in label:
        colored = (red > 100) & (green > 70) & (blue < np.minimum(red, green) * .7)
    else:
        colored = (green > red + 25) & (green > blue + 15)
    mask = difference & colored
    ys, xs = np.nonzero(mask)
    count = int(mask.sum())
    return {'focus_box': list(box), 'marker_pixels': count,
            'changed_bbox': [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]
            if mask.any() else None,
            'observed_badge_difference': count >= 80,
            'limits': 'Fixed fixture focus; verify shape and occlusion in original captures too.'}


def read_controls(report_path):
    report = json.loads(report_path.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Matched control run failed')
    pictures = {}
    for label, receipt in report['captures'].items():
        if not label.endswith('_native'):
            continue
        path = report_path.parent / Path(receipt['path']).name
        if not receipt['ok'] or not receipt['reliable'] or digest(path) != receipt['sha256']:
            raise ValueError('Matched control capture is unreliable or stale')
        with Image.open(path) as original:
            pictures[label] = original.convert('RGB')
    return report, pictures


def retained_support(picture, unknown=False):
    """Require the lower fixture independently of marker visibility."""
    width, height = picture.size
    bounds = (895, 660, 1090, 845)
    box = tuple(round(value * (width / 1994. if index % 2 == 0 else height / 1105.))
                for index, value in enumerate(bounds))
    data = np.asarray(picture.crop(box), dtype=np.int16)
    red, green, blue = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    if unknown:
        mask = (red > 100) & (green > 70) & (blue < green * .7) & (red > green)
    else:
        mask = (green > red + 20) & (blue > red + 20) & (blue < green * 1.8)
    count = int(mask.sum())
    minimum = max(80, round(500 * width * height / (1994. * 1105.)))
    return {'focus_box': list(box), 'support_pixels': count, 'minimum_pixels': minimum,
            'expected_material': 'yellow_concrete' if unknown else 'cyan_concrete',
            'retained_support_observed': count >= minimum}


def retained_frame(label):
    mode = label.partition('_badge_')[2].partition('_later_')[0]
    return label.startswith('editor_') and mode in ('hidden', 'section')


def analyze(report_path, output, control_report=None):
    report = json.loads(report_path.read_bytes())
    if not report['completed'] or not report['restored'] or not report['source_unchanged']:
        raise ValueError('Capture run was incomplete, unrestored or changed sources')
    pictures, panels = {}, []
    for label, receipt in report['captures'].items():
        path = report_path.parent / Path(receipt['path']).name
        if not receipt['ok'] or not receipt['reliable'] or digest(path) != receipt['sha256']:
            raise ValueError('Capture receipt is unreliable or stale: ' + label)
        with Image.open(path) as original:
            picture = original.convert('RGB')
        pictures[label] = picture
        if label.startswith('editor_'):
            # The complete near-view fixture stays within the declared viewport.
            box = tuple(round(value * picture.width / 1994.) for value in (485,355,1525,846))
            picture = picture.crop(box)
        panel = picture.copy()
        panel.thumbnail((700,360))
        canvas = Image.new('RGB',(720,395),'#e8ebee')
        canvas.paste(panel,((720-panel.width)//2,30))
        ImageDraw.Draw(canvas).text((8,8),label,fill='black')
        panels.append(canvas)
    controls, control_pictures = ((report, pictures) if control_report is None
                                 else read_controls(control_report))
    rows = {}
    for label, picture in pictures.items():
        if not label.endswith('_badge'):
            continue
        control = label[:-6] + '_native'
        if control not in control_pictures:
            continue
        source, baseline = report['rows'][label]['source'], controls['rows'][control]['source']
        if source['cells'] != baseline['cells'] or source['camera'] != baseline['camera']:
            raise ValueError('Badge/control source associations differ')
        rows[label] = marker_difference(picture, control_pictures[control], label)
        for suffix in ('restored', 'full'):
            restored = label + '_' + suffix
            if restored in pictures:
                rows[restored] = marker_difference(pictures[restored], control_pictures[control], label)
    output.mkdir(parents=True,exist_ok=True)
    sheets=[]
    for start in range(0,len(panels),6):
        group=panels[start:start+6]
        sheet=Image.new('RGB',(1440,395*((len(group)+1)//2)),'white')
        for index,panel in enumerate(group):sheet.paste(panel,((index%2)*720,(index//2)*395))
        path=output/('review-%02d.png' % (start//6))
        sheet.save(path)
        sheets.append({'path':path.name,'sha256':digest(path)})
    support = {label: retained_support(picture, '_unknown_' in label) for label, picture in pictures.items()
               if retained_frame(label)}
    result={'schema':3,'report_sha256':digest(report_path),'rows':rows,'sheets':sheets,
            'retained_support': support,
            'all_retained_support_observed': bool(support) and all(
                row['retained_support_observed'] for row in support.values()),
            'control_report_sha256':digest(control_report) if control_report is not None else None,
            'all_matched_badges_observed':bool(rows) and all(row['observed_badge_difference'] for row in rows.values()),
            'pixel_acceptance':False}
    (output/'analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='ascii')
    print(json.dumps({'pairs':len(rows),'all_observed':result['all_matched_badges_observed'],'sheets':len(sheets)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--control-report', type=Path)
    args=parser.parse_args()
    analyze(args.report,args.output,args.control_report)


if __name__=='__main__':main()

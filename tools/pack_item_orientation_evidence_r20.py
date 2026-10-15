"""Retain cold downward-pose controls and replayable editor brightness evidence."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pack_item_plane_evidence_r20 as plane

ROOT = Path(__file__).resolve().parents[1]

README = """# Item-frame downward baseline and editor brightness controls

Production qualification remains **false**. The item-frame layout now applies
its 180-degree horizontal baseline to both upward and downward faces. Shelf
and campfire layouts remain outside this condition. No fragment shader,
shared body shader, material, mesh, or light calculation changes here.

The cold downward rotations 0, 45, and 90 degrees pass independent product,
actual native-body, and local native-edge gates. Each report completed with
restored fixtures, unchanged source snapshots, and no cleanup errors. The
previous 180-degree mismatch is retained in the earlier item-plane package
as a failed control. Native item visibility is established with the actual
player below the downward frame; an empty or stale native image cannot pass.

Brightness compares declared visible frame-body patches against each editor
frame's own hidden-item baseline before and after rendering. Existing
direction-dependent body brightness is allowed. The selected patches exclude
the source icon alpha and the editor's lower controls. Every patch must have
at least 16 pixels and at most 3 RGB levels of change; an injected 12-level
change must be rejected. The original six-face plain/enchanted controls and
the corrected downward sentinels are retained with their editor PNGs and
owner-bound receipts. This evidence supports leaving body lighting unchanged.

Full capture folders include original PNG bytes, sanitized receipts, calibration,
reports, and recomputed pixel analyses. `brightness/` retains only the editor
triplets needed for that measurement. `source/` freezes the analysis import
closure and current generated contract. Authentication tokens are omitted.
`shader-compile.json` records the 16 GLES 2/3 compile/link cases.

Run from Windows with Python, NumPy, and Pillow:

```powershell
python -B -X utf8 docs/evidence/item-orientation-r20-v1/verify_package.py --pixels
```

The verifier checks all retained bytes, rebases moved paths, and repeats the
frozen pose and brightness analyses without a game. Full ordinary-frame and
glow-frame matrices remain separate acceptance work; this package qualifies
only its measured poses and does not enable production rendering.
"""


def label_and_path(specification):
    label, path = specification.split('=', 1)
    if not label or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for character in label):
        raise ValueError('Evidence labels must be simple directory names')
    return label, Path(path).resolve()


def pack(captures, brightness, compiler, output):
    plane.pack(captures, output)
    summary = json.loads((output / 'summary.json').read_bytes())
    summary['scope'] = 'Cold downward horizontal baseline and independent editor body-brightness controls'
    summary['brightness'] = {}
    reports = []
    for specification in brightness:
        label, source = label_and_path(specification)
        raw = json.loads(source.read_bytes())
        if not raw['completed'] or raw['cleanup_errors'] or not raw['source_unchanged']:
            raise ValueError('Brightness evidence must finish restoration with stable sources')
        report = plane.sanitize(copy.deepcopy(raw), raw['session'].get('token'))
        report['captures'] = [row for row in report['captures'] if '_editor_' in row['label']]
        destination = output / 'brightness' / label
        destination.mkdir(parents=True, exist_ok=False)
        retained = {}
        plane.retain_captures(report, destination, raw['session'].get('token'), retained)
        target = destination / 'report.json'
        plane.save(target, report)
        reports.append(target)
        summary['brightness'][label] = {'original_report_sha256': plane.digest(source),
            'retained_report_sha256': plane.digest(target), 'retained_images': len(retained)}
    command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'tools/analyze_item_frame_brightness_r20.py')]
    for report in reports:
        command.extend(('--report', str(report)))
    command.extend(('--output', str(output / 'brightness/analysis')))
    subprocess.run(command, cwd=str(ROOT), check=True)
    analysis = json.loads((output / 'brightness/analysis/analysis.json').read_bytes())
    if not analysis['passed']:
        raise ValueError('Retained editor brightness evidence failed')
    summary['brightness_result'] = {'passed': analysis['passed'], 'rows': len(analysis['rows']),
        'maximum_rgb_change': max(row['maximum_rgb_change'] for row in analysis['rows'])}
    for relative in ('tools/analyze_item_frame_brightness_r20.py',
                     'tools/pack_item_orientation_evidence_r20.py',
                     'tools/verify_item_orientation_evidence_r20.py'):
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    shutil.copy2(ROOT / 'tools/verify_item_orientation_evidence_r20.py', output / 'verify_package.py')
    shutil.copy2(compiler, output / 'shader-compile.json')
    (output / 'README.md').write_text(README, encoding='ascii')
    (output / '.gitattributes').write_text('* -text -diff\n', encoding='ascii')
    plane.save(output / 'summary.json', summary)
    files = {path.relative_to(output).as_posix(): {'sha256': plane.digest(path), 'bytes': path.stat().st_size}
             for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'manifest.json'}
    plane.save(output / 'manifest.json', {'schema': 1, 'production_qualified': False,
        'original_package_root': str(output.resolve()), 'files': files})
    print(json.dumps({'files': len(files), 'bytes': sum(row['bytes'] for row in files.values()),
                      'brightness': summary['brightness_result'], 'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='append', required=True)
    parser.add_argument('--brightness', action='append', required=True)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pack(args.capture, args.brightness, args.compiler, args.output.resolve())

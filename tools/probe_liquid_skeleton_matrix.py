"""Read native skeleton shader matrices through signed24 diagnostic tile colors."""
import argparse
import json
import os
from pathlib import Path
import time

from PIL import Image

import probe_liquid_pose_channel as base
import probe_liquid_skeleton_packet as packet
import probe_liquid_skeleton_water as water
from _session import load_session

SET_MATRIX = '''saved=sys._liquid_water_ui
selected=%r
saved['groups']=[group._replace(uniforms=group.uniforms[:3]+((39686.,-1.,selected,1.),)) for group in saved['groups']]
_result=json.dumps({'selected':selected})
'''


def decode(path):
    with Image.open(path) as image:
        width, height = image.size
        rows = []
        for left in (.03, .53):
            values = []
            for index in range(16):
                column, row = index % 4, index // 4
                point = (round(width * (left + .44 * (column + .5) / 4.)),
                         round(height * (.08 + .84 * (row + .5) / 6.)))
                color = image.getpixel(point)[:3]
                code = (color[0] << 16) | (color[1] << 8) | color[2]
                values.append((code - 8388608) / 2048.)
            rows.append(values)
        return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != base.ROOT:
        parser.error('The session belongs to another project')
    report = {'schema': 1, 'completed': False, 'restored': False, 'captures': {}, 'matrices': {},
              'element_order': 'column major', 'maximum_quantization_error': 1. / 4096.,
              'scope': 'Native shader uniforms, not liquid shape or production acceptance'}

    def record():
        base.write(args.output, report)

    def ready(code=water.STATUS, key='ready'):
        deadline = time.monotonic() + 10.
        while True:
            row = base.run(client, code)
            if row[key]:
                return row
            if time.monotonic() >= deadline:
                raise RuntimeError('Native matrix UI did not become ready: ' + repr(row))
            time.sleep(.1)

    with base.Client(timeout=45) as client:
        try:
            report['ui_setup'] = base.run(client, packet.OPEN % 'modern_projection_liquid_matrix')
            report['ready'] = ready()
            for selected, label in enumerate(('WORLDVIEWPROJ', 'WORLDVIEW', 'PROJ', 'WORLD', 'BONE')):
                base.run(client, SET_MATRIX % float(selected))
                ready()
                time.sleep(.2)
                path = args.output.with_name(args.output.stem + '_' + label + '.png')
                report['captures'][label] = base.capture(args.session, args.owner, path, args.capture_exe)
                report['matrices'][label] = decode(path)
                record()
            report['completed'] = True
        except Exception as error:
            report['error'] = '%s: %s' % (type(error).__name__, error)
            raise
        finally:
            report['ui_cleanup'] = base.run(client, water.CLEAN)
            report['cleanup_state'] = ready(water.CLEAN_READY, 'restored')
            report['restored'] = bool(report['ui_cleanup'] and report['cleanup_state']['restored'])
            record()
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'], 'matrices': report['matrices']}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

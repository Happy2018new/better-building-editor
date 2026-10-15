"""Freeze board isolation and baseline controls before new hanging-sign frames."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import verify_sign_visuals as signs
from verify_hanging_sign_front_holdout import ControlledSignCheck, record_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--view', choices=('front', 'back'), action='append')
    parser.add_argument('--projection-mode', choices=('full', 'missing'), default='full')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Holdout output must be a new directory')
    executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
    helper = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER']).resolve(strict=True)
    if helper.name != 'capture_native_window.py':
        parser.error('Bind the reviewed WGC helper before setup')
    production = [record_file(path) for directory in ('behavior_pack', 'resource_pack')
                  for path in sorted((signs.ROOT / directory).rglob('*')) if path.is_file()]
    tool_paths = [Path(__file__), signs.ROOT / 'tools/verify_sign_visuals.py',
                  signs.ROOT / 'tools/sign_panel_oracle.py',
                  signs.ROOT / 'tools/verify_hanging_sign_front_holdout.py',
                  signs.ROOT / 'tools/verify_shulker_orientations.py',
                  signs.ROOT / 'tools/context_test_environment.py', helper, executable]
    frozen = {'schema': 1, 'scope': 'Fresh hanging-sign holdout; blank-derived board and repeated blank controls',
              'production': production, 'tools': [record_file(path) for path in tool_paths],
              'oracle': 'Largest solid wood rectangle in blank frame; original wood-color predicate; no shown-frame board adjustment',
              'response': 'Existing wood_composite response within independently detected board',
              'views': args.view or ['front', 'back'], 'projection_mode': args.projection_mode,
              'limits': {'minimum_difference': 20, 'minimum_color_response': 20,
                         'normalized_glyph_iou': .45, 'layout_center': .1, 'layout_size': .2,
                         'blank_repeat_changed_pixels': 0, 'outside_text_changed_pixels': 0,
                         'outside_text_native_bounds_margin': 2},
              'calibration_only': 'R7 native/editor/projection blank-frame board detection; historical failures unchanged'}
    args.output.mkdir(parents=True)
    (args.output / 'frozen_source.json').write_text(json.dumps(frozen, indent=2) + '\n', encoding='utf-8')
    signs.SignCheck = ControlledSignCheck
    sys.argv = [str(signs.ROOT / 'tools/verify_sign_visuals.py'), str(args.output),
                '--case', 'hanging_front_back', '--response', 'wood_composite',
                '--native-resolution', '--panel-isolation', 'wood_rectangle', '--blank-stability',
                '--projection-mode', args.projection_mode]
    for view in frozen['views']:
        sys.argv.extend(('--view', view))
    try:
        signs.main()
    finally:
        unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                        for row in production + frozen['tools'])
        (args.output / 'frozen_source_after.json').write_text(
            json.dumps({'production_and_tools_unchanged': unchanged}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

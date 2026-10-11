"""Freeze actual chest resources before a declared public top-view control."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import verify_chest_top_public_visuals as chest
from verify_hanging_sign_front_holdout import record_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case-limit', choices=(1, 2, 3), type=int, default=3)
    parser.add_argument('--target-height-offset', choices=(8, 16), type=int, default=8)
    parser.add_argument('--player-at-camera', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new holdout directory')
    helper = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER']).resolve(strict=True)
    executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
    production = [record_file(path) for directory in ('behavior_pack', 'resource_pack')
                  for path in sorted((ROOT / directory).rglob('*')) if path.is_file()]
    tool_paths = [Path(__file__), ROOT / 'tools/verify_chest_top_public_visuals.py',
                  ROOT / 'tools/verify_copper_chest_render.py', ROOT / 'tools/verify_sign_visuals.py',
                  ROOT / 'tools/shulker_pixels.py', ROOT / 'tools/verify_camera_projection.py',
                  ROOT / 'tools/visual_environment.py', helper, executable]
    frozen = {'schema': 1, 'scope': 'Unchanged public chest source cells; declared top camera; original gates',
              'checked_out_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'production': production, 'tools': [record_file(path) for path in tool_paths],
              'plans': chest.PLANS[:args.case_limit], 'target_height_offset': args.target_height_offset,
              'player_at_camera': args.player_at_camera,
              'candidate_reference_is_proposal_only': 'The legacy report candidate field names an unaccepted R7 proposal. Actual tested bytes are recorded here.',
              'limits': {'minimum_native_pixels': 1000, 'shape_iou': .82,
                         'scale_relative_error': .2, 'texture_cosine': .45,
                         'center_distance_pixels': 3, 'boundary_rms_pixels': 4}}
    args.output.mkdir(parents=True)
    (args.output / 'frozen_source.json').write_text(json.dumps(frozen, indent=2) + '\n', encoding='utf-8')
    sys.argv = [str(ROOT / 'tools/verify_chest_top_public_visuals.py'), str(args.output / 'report.json'),
                '--case-limit', str(args.case_limit), '--target-height-offset', str(args.target_height_offset)]
    if args.player_at_camera:
        sys.argv.append('--player-at-camera')
    try:
        chest.main()
    finally:
        unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                        for row in production + frozen['tools'])
        (args.output / 'frozen_source_after.json').write_text(
            json.dumps({'production_and_tools_unchanged': unchanged}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

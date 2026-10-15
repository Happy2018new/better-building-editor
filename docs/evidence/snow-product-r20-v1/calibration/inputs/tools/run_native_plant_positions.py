"""Run one reviewed native-only coordinate phase using the owned startup contract."""
import argparse
from pathlib import Path
import json

import supervise_snow_h0 as startup
from verify_native_plant_positions_phase import CONTRACT, run_phase

ROOT = Path(__file__).resolve().parents[1]


def validate_plan(path, expected_sha):
    plan = startup.validate_plan(path, expected_sha)
    if plan.get('native_coordinate_control') != CONTRACT or plan.get('plant_candidate') is not None:
        raise ValueError('Native coordinate phase must remain native-only and original-texture')
    if plan.get('texture_condition') != 'native_original':
        raise ValueError('Native coordinate phase rejects texture overrides')
    for key, relative in (('native_coordinate_runner', 'tools/run_native_plant_positions.py'),
                          ('native_coordinate_phase', 'tools/verify_native_plant_positions_phase.py')):
        if Path(plan['files'][key]['path']).resolve() != ROOT / relative:
            raise ValueError('Native coordinate plan belongs to another runner/phase')
    if plan['files']['native_stone_reference_roi']['sha256'] != CONTRACT['stone_reference_roi_sha256']:
        raise ValueError('Native coordinate frozen stone reference changed')
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = validate_plan(args.plan, args.plan_sha256)
    if not args.run:
        print(json.dumps({'review_only': True, 'new_launches': 0, 'plan_sha256': args.plan_sha256}))
        return 0
    report = startup.supervise(plan, startup.WindowsHost(), args.output, phase=run_phase)
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['diagnostic_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

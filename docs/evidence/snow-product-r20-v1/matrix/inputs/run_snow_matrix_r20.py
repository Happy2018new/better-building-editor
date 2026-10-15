"""Run the established snow matrix with explicit R20 camera and health gates."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', required=True, type=Path)
    parser.add_argument('--plant', action='append')
    parser.add_argument('--height', type=int, choices=range(8), action='append')
    parser.add_argument('--timeout', type=float, default=45)
    parser.add_argument('--max-handles', type=int, default=215000)
    parser.add_argument('--max-seconds', type=float, default=1200)
    args = parser.parse_args()
    sys.path.insert(0, str(args.project.resolve() / 'tools'))
    import verify_centered_snow_profiles as suite
    from _session import load_session
    from water_native_projection import validate_calibration
    from probe_product_water import snapshot_digest, snapshot_sources
    from check_native_dialogs import assertion_dialogs
    import probe_liquid_workspace as workspace
    from snow_native_projection_r20 import world_cell_roi

    session = load_session(live=True)
    calibration = json.loads(args.camera_calibration.read_bytes())
    binding = {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')}
    validate_calibration(calibration, binding, snapshot_digest(snapshot_sources(args.project)))
    suite.world_cell_roi = world_cell_roi
    original = suite.SignCheck
    started = time.monotonic()
    health = []

    class BoundedSnowCheck(original):
        def capture(self, label, tree=None):
            if time.monotonic() - started >= args.max_seconds:
                raise RuntimeError('R20 snow matrix time budget reached; restore before continuing')
            dialogs = [row for row in assertion_dialogs() if row['pid'] == session['game_pid']]
            if dialogs:
                raise RuntimeError('Owned native assertion blocks snow capture: ' + repr(dialogs))
            sample = dict(workspace.transport.metrics(session['session_file'], session['owner']), label=label)
            health.append(sample)
            if sample['handles'] >= args.max_handles:
                raise RuntimeError('R20 snow native handle budget reached; restore before recycling')
            return original.capture(self, label, tree)

    suite.SignCheck = BoundedSnowCheck
    try:
        report = suite.run(args)
    finally:
        args.output.with_name('health.json').write_text(json.dumps(health, indent=2), encoding='utf8')
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'restored', 'elapsed_seconds')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

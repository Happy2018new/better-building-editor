"""Run the established snow matrix with explicit R20 camera and health gates."""
import argparse
from datetime import datetime, timezone
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
    parser.add_argument('--direct-backdrop', action='store_true')
    parser.add_argument('--target-lift', type=int, choices=range(16, 65), default=32)
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
    if args.direct_backdrop:
        from snow_contrast_direct_r20 import SETUP
        suite.SETUP_BACKDROP = SETUP
    original = suite.SignCheck
    started = time.monotonic()
    health = []
    load_commands = {suite.LOAD % (name, height, kind) for name in suite.NAMES for height in range(8)
                     for kind in ('blank', 'plant', 'snow', 'covered')}
    target_command = '_result=json.dumps(tuple(b.player_origin()[i]+(6,32,6)[i] for i in range(3)))'
    pause = ROOT / '.runtime/snow-r20-pause.json'
    acknowledgement = ROOT / '.runtime/snow-r20-pause-ack.json'

    class BoundedSnowCheck(original):
        def run(self, code):
            if code in load_commands and pause.exists():
                paused = time.monotonic()
                acknowledgement.write_text(json.dumps({'owner': session['owner'],
                    'game_pid': session['game_pid'], 'game_identity': session['game_identity'],
                    'row_boundary': True, 'captures_drained': True,
                    'at_utc': datetime.now(timezone.utc).isoformat()}, indent=2), encoding='utf8')
                try:
                    while pause.exists():
                        if time.monotonic() - paused > 600:
                            raise RuntimeError('Snow WGC pause exceeded ten minutes; restore')
                        time.sleep(.1)
                finally:
                    acknowledgement.unlink(missing_ok=True)
            if code == target_command:
                code = '_result=json.dumps(tuple(b.player_origin()[i]+(6,%d,6)[i] for i in range(3)))' % args.target_lift
            return original.run(self, code)

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

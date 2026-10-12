"""Capture one byte-identical-frame epoch through the frozen native harness."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from liquid_static_coordinate_epochs import check, verify_strip
from liquid_coordinate_markers import fingerprint, write

index = sys.argv.index('--static-plan')
PLAN = Path(sys.argv[index + 1]).resolve()
del sys.argv[index:index + 2]
index = sys.argv.index('--static-epoch')
EPOCH = sys.argv[index + 1]
del sys.argv[index:index + 2]
FIXTURE = ROOT / '.runtime/capture_static_water_controls_r9.py'
spec = importlib.util.spec_from_file_location('static_coordinate_fixture', FIXTURE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ORIGINAL = base.frozen.execute_controls


def execute(harness, options, runtime_args, report):
    from _session import load_session
    from _window import background_guard_state
    import verify_wet_actor_visuals as wet
    plan = json.loads(PLAN.read_bytes())
    check(plan)
    expected = [row['case'] for row in plan['geometry_sequences']]
    if options.case != expected or options.cell_origin != plan['origin']:
        raise ValueError('Frozen static geometry cases or origin changed')
    if fingerprint(plan['target'])['sha256'] != plan['assets'][EPOCH]['sha256']:
        raise ValueError('Installed static epoch differs from frozen bitmap')
    phase = verify_strip(plan['target'], EPOCH)
    for sequence in plan['geometry_sequences']:
        document = base.source_document(sequence['case'])
        cells = [(tuple(options.cell_origin[i] + pos[i] - base.FOCUS[i] for i in range(3)),
                  base.frozen.encode(value)) for pos, value in document.blocks.items()]
        platform = wet.camera_side_platform(cells, tuple(plan['camera_offset']))
        source = base.fixture_plan(sequence['case'], tuple(options.cell_origin), platform)
        if json.loads(json.dumps(source['controls'])) != sequence['controls']:
            raise ValueError('Source differs from independent native geometry controls')
    report.update(static_coordinate_plan=fingerprint(PLAN), static_epoch=EPOCH,
        static_epoch_asset=plan['assets'][EPOCH], phase_independent_strip=phase,
        static_runner=fingerprint(Path(__file__)), native_uv_accepted=False, production_accepted=False)
    frame = harness.frame

    def guarded_frame(label, pose):
        if datetime.now(timezone.utc) >= datetime(2026, 10, 12, 22, 20, tzinfo=timezone.utc):
            raise RuntimeError('Native experiment deadline reached; restore')
        session = load_session(live=True)
        status = background_guard_state(session['game_pid'], Path(session['game_executable']).name)
        if not status['window_noactivate'] or not status['background_safe']:
            raise RuntimeError('Owned background contract changed')
        if fingerprint(plan['target'])['sha256'] != plan['assets'][EPOCH]['sha256']:
            raise RuntimeError('Installed marker changed during native capture')
        return frame(label, pose)

    harness.frame = guarded_frame
    try:
        return ORIGINAL(harness, options, runtime_args, report)
    finally:
        harness.frame = frame


base.frozen.execute_controls = execute
if __name__ == '__main__':
    raise SystemExit(base.frozen.main())

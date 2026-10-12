"""Add a remote opaque atlas witness to the unchanged reviewed water harness."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from liquid_static_cube_epochs import add_cube, check_alias
from liquid_coordinate_markers import fingerprint

spec = importlib.util.spec_from_file_location('same_alias_static', ROOT / 'tools/capture_liquid_static_coordinates.py')
static = importlib.util.module_from_spec(spec)
spec.loader.exec_module(static)
original_plan = static.base.fixture_plan
original_execute = static.execute


def fixture_plan(identity, origin, platform):
    return add_cube(original_plan(identity, origin, platform), static.base.frozen.native_reference)


def execute(harness, options, runtime_args, report):
    plan = json.loads(static.PLAN.read_bytes())
    check_alias(plan)
    frame = harness.frame

    def checked_frame(label, pose):
        check_alias(plan)
        return frame(label, pose)

    harness.frame = checked_frame
    report.update(opaque_cube_surfaces=deepcopy(plan['cube_surfaces']),
        opaque_cube_alias=plan['cube_alias_override'], opaque_cube_runner=fingerprint(Path(__file__)),
        cube_sampling_accepted=False, native_uv_accepted=False, production_accepted=False)
    try:
        return original_execute(harness, options, runtime_args, report)
    finally:
        harness.frame = frame


static.base.fixture_plan = fixture_plan
static.base.frozen.fixture_plan = fixture_plan
static.base.frozen.execute_controls = execute
if __name__ == '__main__':
    raise SystemExit(static.base.frozen.main())

"""Attach the passed owner-bound prefixture runtime check to the frozen cube harness."""
import json
import os
from pathlib import Path

import capture_liquid_static_cube as cube
from liquid_coordinate_markers import fingerprint

original_execute = cube.execute


def execute(harness, options, runtime_args, report):
    path = Path(os.environ['MCDEV_LIQUID_RUNTIME_HEALTH'])
    health = json.loads(path.read_bytes())
    if (not all(health.get(key) for key in ('passed', 'completed', 'binding_verified', 'timer_cleanup_verified'))
            or health['session_file'] != os.environ['MCDEV_SESSION_FILE']
            or health['owner'] != os.environ['MCDEV_OWNER']):
        raise ValueError('Owner-bound runtime health did not pass before the fixture')
    report['runtime_health_before_fixture'] = fingerprint(path)
    report['r12_capture_runner'] = fingerprint(Path(__file__))
    return original_execute(harness, options, runtime_args, report)


cube.static.base.frozen.execute_controls = execute
if __name__ == '__main__':
    raise SystemExit(cube.static.base.frozen.main())

"""Add the declared capture cutoff around the exact frozen F-world host."""
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import sys

WORK = Path(__file__).resolve().parent
record = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
sys.path.insert(0, str(Path(record['project']) / 'tools'))
import probe_liquid_pose_channel as base

original = base.capture


def bounded_capture(*args, **kwargs):
    assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-22T23:25:00+00:00'), '07:25 capture cutoff'
    return original(*args, **kwargs)


base.capture = bounded_capture
target = WORK / 'run_product_v2_f_world_v2.py'
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name='__main__')

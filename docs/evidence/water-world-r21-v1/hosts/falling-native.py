"""Bind four unchanged falling controls to native water/support corner pixels."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-state-v7'
TARGET = OUTPUT / 'falling-native-skyward.json'
DIAGNOSTIC = OUTPUT / 'falling-native-skyward-points.json'
assert not TARGET.exists() and not DIAGNOSTIC.exists()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe
import analyze_product_water as analysis
from water_native_projection import query_code

bound = json.loads((OUTPUT / 'start.json').read_bytes())
os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER='water-r20-v7',
                  MCDEV_ALLOW_USER_FOREGROUND='1')
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
          'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'source_contract_sha256': probe.snapshot_digest(probe.snapshot_sources(PROJECT)),
          'completed': False, 'restored': False, 'window_actions': [], 'rows': {}}
original_check = probe.blueprints.BlueprintCheck
original_capture = probe.base.capture
state = {'check': None, 'source': None, 'point_sets': None}


class GeometryCheck(original_check):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        state['check'] = self

    def run(self, code, *args, **kwargs):
        result = super().run(code, *args, **kwargs)
        if isinstance(result, dict) and all(key in result for key in ('case', 'control', 'cells')):
            state['source'] = result
        return result


def capture_points(*args, **kwargs):
    check = state['check']
    ready = check.run(probe.WORLD_STATE)
    row = {'route': 'full', 'case': 'falling', 'source': state['source'], 'ready': ready,
           'camera': check.run(probe.CAMERA_STATE)}
    if state['point_sets'] is None:
        point_sets = {}
        for index, (shape, polygon) in enumerate(analysis.water_polygons(ready['shapes'])):
            point_sets['water_' + str(index)] = polygon
        for index, box in enumerate(analysis.fixture_solid_boxes(row)):
            x0, y0, z0, x1, y1, z1 = box
            corners = ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
                       (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1))
            for face, indices in enumerate(analysis.FACE_INDICES):
                point_sets['solid_%d_%d' % (index, face)] = [corners[item] for item in indices]
        assert any(key.startswith('water_') for key in point_sets)
        state['point_sets'] = point_sets
        report['point_sets'] = point_sets
        report['plan_source'] = state['source']
        report['plan_ready'] = ready
    code = query_code(state['point_sets'])
    record = {'before': check.run(code), 'state_before': row}
    captured = original_capture(*args, **kwargs)
    record.update(after=check.run(code), state_after=check.run(probe.WORLD_STATE),
                  capture_sha256=captured['sha256'], capture_size=[captured['width'], captured['height']],
                  capture_path=captured['path'])
    report['rows'][Path(captured['path']).stem] = record
    probe.base.write(DIAGNOSTIC, report)
    return captured


probe.blueprints.BlueprintCheck = GeometryCheck
probe.base.capture = capture_points
sys.argv = [str(PROJECT / 'tools/probe_product_water.py'), '--session', bound['session_file'],
            '--owner', 'water-r20-v7', '--capture-exe', str(ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'),
            '--launch-inputs', str(OUTPUT / 'launch-inputs.json'), '--output', str(TARGET),
            '--camera-calibration', str(OUTPUT / 'calibration.json'), '--world-fixture-lift-y', '64',
            '--world-view-scale', '.5', '--max-seconds', '300', '--max-handles', '220000',
            '--frozen', '--visibility-controls', '--measure-budgets', '--route', 'full',
            '--case', 'falling', '--falling-skyward']
try:
    result = probe.main()
    report['completed'] = result == 0
except Exception:
    report['error'] = traceback.format_exc()
    result = 1
finally:
    probe.blueprints.BlueprintCheck = original_check
    probe.base.capture = original_capture
    if TARGET.exists():
        original = json.loads(TARGET.read_bytes())
        report['restored'] = original.get('restored') is True
        report['source_unchanged'] = original.get('source_unchanged') is True
        report['source_report_sha256'] = hashlib.sha256(TARGET.read_bytes()).hexdigest()
        report['session_binding'] = original['session_binding']
    probe.base.write(DIAGNOSTIC, report)
print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
raise SystemExit(result)

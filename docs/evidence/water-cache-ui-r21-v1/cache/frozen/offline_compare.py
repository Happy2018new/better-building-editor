"""Compare the exact saved baseline with the candidate without a game or SDK."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'behavior_pack/modern_projection/projection/liquid_viewport.py'
BASELINE = '0898a8f6'
BASELINE_SHA256 = 'd07472df91d4c4cd93c2d7d84cd37c34c00cdac72ade470d290a6e125b0531cf'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from tests.test_liquid_viewport import LiquidControlsTests, POSE
from projection import liquid_transport
from projection.liquid_viewport import LiquidControls


def baseline_class():
    source = subprocess.check_output(['git', 'show', BASELINE + ':' + SOURCE], cwd=str(ROOT))
    assert hashlib.sha256(source).hexdigest() == BASELINE_SHA256
    module = ModuleType('projection._depth_cache_baseline_r21')
    module.__package__ = 'projection'
    exec(compile(source, BASELINE + ':' + SOURCE, 'exec'), module.__dict__)
    return module.LiquidControls


def observe(control_class):
    fixture = LiquidControlsTests(methodName='runTest')
    fixture.setUp()
    fixture.controls = control_class(fixture.registry, fixture.model)
    fixture.settle()
    renderer = fixture.entry['renderer']
    view_at = mock.Mock(return_value=fixture.view)
    pose_at = mock.Mock(return_value=POSE)
    with mock.patch.object(liquid_transport, 'validate_uniforms',
                           wraps=liquid_transport.validate_uniforms) as source_validation, \
            mock.patch.object(fixture.controls.renderer_factory, 'validate',
                              wraps=fixture.controls.renderer_factory.validate) as pose_validation, \
            mock.patch.object(renderer, 'restore_publication',
                              wraps=renderer.restore_publication) as restore:
        for tick in range(60):
            assert fixture.controls.update(fixture.groups, view_at, pose_at,
                                           (-.5, -.25), .3 + tick / 60.)
    return {
        'steady_ticks': 60,
        'source_payload_validations': source_validation.call_count,
        'pose_validations': pose_validation.call_count,
        'view_callbacks': view_at.call_count,
        'pose_callbacks': pose_at.call_count,
        'publication_restore_calls': restore.call_count,
        'native_payloads': [list(key) + [list(value)]
                            for key, value in sorted(fixture.model.values.items())],
        'native_submissions': [control.doll.calls for control in fixture.dolls],
        'surface_visibility': [control.visible for control in fixture.surfaces],
        'control_geometry': [[control.position, control.size]
                             for control in fixture.dolls + fixture.surfaces],
    }


def main():
    baseline, candidate = observe(baseline_class()), observe(LiquidControls)
    assert baseline['source_payload_validations'] == 60
    assert candidate['source_payload_validations'] == 0
    for field in baseline:
        if field != 'source_payload_validations':
            assert baseline[field] == candidate[field], field
    report = {
        'offline_only': True,
        'game_started': False,
        'production_qualified': False,
        'original_elapsed_failures_resolved': False,
        'baseline_ref': BASELINE,
        'baseline_source_sha256': BASELINE_SHA256,
        'candidate_source_sha256': hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
        'baseline': baseline,
        'candidate': candidate,
        'passed': True,
    }
    output = Path(__file__).with_name('offline-comparison.json')
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()

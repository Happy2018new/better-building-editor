"""Complete existing visible-animation checks on unchanged R27 original PNGs."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
HOST = ROOT / '.runtime/round-20261022/water-merged-fullA-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = WORK / 'product-animation-analysis-v1.json'
    assert not output.exists()
    binding = json.loads((HOST / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project'])
    sys.path.insert(0, str(project / '.agents/skills/pyreact-debugging/scripts'))
    for name in ('_session', '_window'):
        module = importlib.import_module(name)
        relative = Path(module.__file__).resolve().relative_to(project.resolve()).as_posix()
        assert sha(Path(module.__file__)) == binding['source_sha256'][relative]
    sys.path.insert(0, str(project / 'tools'))
    sys.path.insert(0, str(HOST))
    import calibration_host
    calibration_activation = calibration_host.activate()
    calibration_report = calibration_host.validate_report(HOST / 'product-v2-camera-seam-v1.json', calibration_activation)
    anchor_path = ROOT / '.runtime/round-20261022/water-editor-anchor-candidate-v1/analysis_anchor_host.py'
    assert sha(anchor_path) == '0ceecf6190a97f6d9215c0e510a78fd08c0a936a50e50279fd449078b1ab7a83'
    spec = importlib.util.spec_from_file_location('r27_frozen_anchor_host', anchor_path)
    anchor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(anchor)
    anchor_activation = anchor.activate()
    base = importlib.import_module('analyze_product_water')
    source = HOST / 'product-v2-a-v1.json'
    source_sha = sha(source)
    result = base.analyze(source)
    assert sha(source) == source_sha
    with output.open('x', encoding='ascii') as stream:
        json.dump(result, stream, indent=2)
    flow_path = ROOT / '.runtime/round-20261022/root-water-fullA-v2-anchor-analysis-v1/flow-analysis-v1.json'
    assert sha(flow_path) == '8792412bc92c364d3bafe9177c1ee8073c0e9fc3186089951366cfdc6deeb44f'
    flow = json.loads(flow_path.read_bytes())
    failed = [key for key, row in result['animation'].items() if not row['passed']]
    report = {'schema': 1, 'source_report': str(source), 'source_report_sha256': source_sha,
              'product_analysis_sha256': sha(output), 'flow_analysis_sha256': sha(flow_path),
              'product_evidence_valid': result['evidence_valid'],
              'animation_rows': len(result['animation']), 'animation_failed': failed,
              'visible_animation_passed': result['observed_product_gates']['animation'],
              'physical_flow_passed': flow['passed'], 'physical_flow_rows': len(flow['rows']),
              'existing_A_capture_and_direction_and_visibility_passed': bool(
                  result['evidence_valid'] and result['observed_product_gates']['animation'] and flow['passed']
                  and len(result['animation']) == len(flow['rows']) == 15),
              'source_unchanged': True, 'anchor_activation': anchor_activation,
              'calibration_activation': calibration_activation, 'calibration_report': calibration_report,
              'speed_magnitude_measured': False, 'native_RGB_parity_claimed': False,
              'new_MC_started': False, 'RPC_dispatched': False,
              'complete_current_source_release_qualified': False}
    with (WORK / 'summary.json').open('x', encoding='ascii') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: report[key] for key in (
        'product_evidence_valid', 'animation_rows', 'animation_failed', 'visible_animation_passed',
        'physical_flow_passed', 'physical_flow_rows', 'existing_A_capture_and_direction_and_visibility_passed',
        'speed_magnitude_measured', 'new_MC_started')}))


if __name__ == '__main__':
    main()

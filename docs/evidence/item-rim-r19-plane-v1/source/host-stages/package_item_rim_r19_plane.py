"""Archive valid causal pixels and invalid cold attempts without credentials."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'docs/evidence/item-rim-r19-plane-v1'
PACKAGE.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def sanitized(value):
    if isinstance(value, dict):
        return {key: sanitized(data) for key, data in value.items() if key.lower() != 'token'}
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    return value


def archive(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == '.json':
        save(target, sanitized(json.loads(source.read_bytes())))
    else:
        shutil.copy2(source, target)


raw = ROOT / '.runtime/item-edge-r19-depth-fine-v1'
report = sanitized(json.loads((raw / 'report.json').read_bytes()))
original_report = copy.deepcopy(report)
captured = {}
for row in report['captures']:
    source = Path(row['capture']['path'])
    assert sha(source) == row['capture']['sha256']
    target = PACKAGE / 'causal/captures' / source.name
    archive(source, target)
    captured[str(source)] = str(target)
    row['capture']['path'] = str(target)
    receipt = source.with_suffix('.capture.json')
    archive(receipt, target.with_suffix('.capture.json'))
    saved = json.loads(target.with_suffix('.capture.json').read_bytes())
    saved['path'] = str(target)
    save(target.with_suffix('.capture.json'), saved)
save(PACKAGE / 'causal/report.json', report)
result = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tools/analyze_item_frame_edge_r19.py'),
    str(PACKAGE / 'causal/report.json'), str(PACKAGE / 'causal/recomputed')], cwd=str(ROOT),
    check=True, capture_output=True, text=True, encoding='utf-8')
(PACKAGE / 'causal/analysis.stdout.txt').write_text(result.stdout, encoding='utf-8')
original = json.loads((raw / 'review-v1/analysis.json').read_bytes())
recomputed = json.loads((PACKAGE / 'causal/recomputed/analysis.json').read_bytes())
for data in (original, recomputed):
    data.pop('source_sha256')
assert original == recomputed, 'Rebased report changed causal measurements'
assert sha(raw / 'review-v1/comparison.png') == sha(PACKAGE / 'causal/recomputed/comparison.png')

for source in (ROOT / '.runtime/item-rim-r19-review-v1/inputs').rglob('*'):
    if source.is_file():
        archive(source, PACKAGE / 'source/capture' / source.relative_to(ROOT / '.runtime/item-rim-r19-review-v1/inputs'))
for relative in ('tools/analyze_item_frame_edge_r19.py', 'tools/analyze_visible_items_r16.py',
    'tools/analyze_item_sprite_sides.py', 'tools/item_sprite_edge_pixels.py',
    'tools/item_sprite_capture_contract.py', 'tools/analyze_item_sprite_product.py',
    'tools/analyze_item_sprite_closeup.py', 'tools/analyze_liquid_workspace.py',
    'tools/run_visible_items_r16.py', 'tools/generate_item_icon_catalog.py',
    'tools/data/item_icon_catalog_nemc_3.10.0.420447.json', 'tests/test_item_pose_acceptance.py',
    'resource_pack/models/modern_projection/item_icons/cf75a6e96b2d3e06_mesh.json',
    'resource_pack/textures/models/modern_projection/item_icons/cf75a6e96b2d3e06.png'):
    archive(ROOT / relative, PACKAGE / 'source/current' / relative)
for name in ('candidate.json', 'original-mesh.json', 'launch-sources.json'):
    archive(ROOT / '.runtime/item-edge-r19-candidate-control' / name, PACKAGE / 'candidate' / name)
archive(Path('D:/bbe-r18-item-glint/resource_pack/models/modern_projection/item_icons/cf75a6e96b2d3e06_mesh.json'),
    PACKAGE / 'candidate/cf75a6e96b2d3e06_mesh.json')

failures = []
for version in range(1, 5):
    suffix = '' if version == 1 else '-v' + str(version)
    control = ROOT / '.runtime' / ('item-edge-r19-candidate-control' + suffix)
    ready = json.loads((control / 'ready-summary.json').read_bytes())
    state = json.loads(Path(ready['session_file']).read_bytes())
    target = PACKAGE / 'cold-failures' / ('v' + str(version))
    summary = {'version': version, 'accepted': False, 'session': ready,
        'final_state': state['state'], 'production_qualified': False}
    assert state['state'] == 'stopped'
    reasons = {
        1: 'Owned MCDK exited before capture client binding; no acceptance report or pixels',
        2: 'Native assertion dialog invalidated noactivation guard; execute_code was blocked before dispatch',
        3: 'Independent stone calibration produced a blank white WGC frame; no item acceptance capture started',
        4: 'Three bounded render-readiness WGC checks remained the same blank white image; acceptance capture not started'}
    summary['reason'] = reasons[version]
    for source in control.iterdir():
        if (source.name in ('ready-summary.json', 'process-samples.json', 'native-assertions.json',
                'front-command.json', 'side-command.json') or source.name.startswith('warmup-')
                or source.name.endswith('.stderr.txt')):
            archive(source, target / source.name)
    samples = control / 'process-samples.json'
    if samples.is_file():
        values = json.loads(samples.read_bytes())
        summary['maximum_handles'] = max(row['handles'] for row in values)
    if version == 3:
        source = ROOT / '.runtime/item-plane-r19-front-v3'
        data = json.loads((source / 'report.json').read_bytes())
        summary.update({'source_unchanged': data['source_unchanged'], 'cleanup_errors': data['cleanup_errors'],
            'completed': data['completed'], 'acceptance_captures': len(data['captures'])})
        for name in ('report.json', 'camera.json', 'camera_front_shown.png', 'camera_front_shown.capture.json'):
            archive(source / name, target / name)
    save(target / 'summary.json', summary)
    failures.append(summary)
for name in ('item_edge_r19_candidate_stage.py', 'item_edge_r19_candidate_stage_v3.py',
    'item_edge_r19_candidate_stage_v4.py', 'item_edge_r19_candidate.py'):
    archive(ROOT / '.runtime' / name, PACKAGE / 'source/host-stages' / name)

validation = {'production_qualified': False, 'causal_evidence_valid': recomputed['evidence_valid'],
    'rebased_measurements_equal': True, 'comparison_png_identical': True, 'cold_candidate_accepted': False,
    'baseline_restore_changed_pixels': recomputed['baseline_restore']['changed_pixels'],
    'candidate_change': 'front_z_pixels 15.0 -> 14.75 only; size 8.0, thickness 0.5 and glint unchanged',
    'tests': {'command': 'python -X utf8 -m unittest tests.test_item_pose_acceptance tests.test_item_sprite_pixels tests.test_item_icon_catalog',
        'passed': 40}, 'failures': failures}
save(PACKAGE / 'verification.json', validation)
entries = {path.relative_to(PACKAGE).as_posix(): {'sha256': sha(path), 'bytes': path.stat().st_size}
    for path in sorted(PACKAGE.rglob('*')) if path.is_file()}
save(PACKAGE / 'manifest.json', {'schema': 1, 'production_qualified': False, 'files': entries})
print(json.dumps({'package': str(PACKAGE), 'files': len(entries),
    'causal_evidence_valid': recomputed['evidence_valid'], 'measurements_equal': True, 'cold_candidate_accepted': False}))

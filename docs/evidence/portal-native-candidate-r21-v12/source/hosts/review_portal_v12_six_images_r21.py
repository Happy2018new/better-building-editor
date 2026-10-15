"""Record the bounded six-image result and independently recheck frozen bytes."""
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/portal-r21-native-candidate-v12'
CONTROL = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
OUTPUT = ROOT / '.runtime/portal-native-candidate-observed-r21-v12-json-readback'
DEPENDENCIES = ROOT / '.runtime/portal-native-candidate-host-dependencies-r21-v12'
sys.path[:0] = [str(PROJECT / '.agents/skills/pyreact-debugging/scripts'), str(PROJECT / 'tools'), str(DEPENDENCIES / 'tools')]
from probe_product_water import snapshot_digest, snapshot_sources
from PIL import Image

frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(PROJECT) == frozen
assert snapshot_digest(frozen) == 'a568dddc531e7eea610d24f18b12369adddb6de081105f52834611d7f8217918'
report = json.loads((OUTPUT / 'report.json').read_bytes())
finalize = json.loads((CONTROL / 'finalize-summary.json').read_bytes())
assert all(report[key] for key in ('completed', 'restored', 'source_unchanged'))
assert len(report['captures']) == 6 and not report['cleanup_errors']
assert finalize['runtime_released'] and finalize['state'] == 'stopped' and not finalize['ready']
notes = {
    'end_gateway_editor': 'Cyan/green starfield visible on the top and vertical faces of the stepped gateway fixture, above stone supports.',
    'end_gateway_full': 'Near north-facing L-shaped gateway starfield and stone supports are visible.',
    'end_gateway_missing': 'Same empty-world missing-mode L-shaped north starfield and supports are visible.',
    'end_portal_editor': 'One cyan starfield horizontal portal plane is visible above stone supports.',
    'end_portal_full': 'Near oblique top view shows the cyan horizontal portal plane and stone supports.',
    'end_portal_missing': 'Same empty-world missing-mode oblique top plane and supports are visible.'}
images = {}
for label, row in report['captures'].items():
    path = OUTPUT / (label + '.png')
    with Image.open(path) as opened:
        size = list(opened.size)
    assert all(row['capture'][key] for key in ('ok', 'reliable', 'foreground_unchanged'))
    assert row['capture']['agent_activation_allowed'] is False
    images[label] = {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'size': size, 'actually_opened_by_portal_agent': True, 'observed': notes[label],
                     'visibility': row.get('visibility'), 'capture_receipt_sha256': hashlib.sha256(
                         path.with_suffix('.capture.json').read_bytes()).hexdigest()}
review = {'schema': 1, 'source_contract_sha256': snapshot_digest(frozen), 'source_count': len(frozen),
          'frozen_bytes_independently_rechecked_after_finalize': True,
          'completed': True, 'restored': True, 'source_unchanged': True, 'cleanup_errors': [],
          'elapsed_seconds': report['elapsed_seconds'], 'images': images,
          'memory_boundary_count': len(report['memory_boundaries']),
          'minimum_available_commit_bytes': min(row['commit_available_bytes'] for row in report['memory_boundaries']),
          'failed_memory_boundaries': sum(not row['passed'] for row in report['memory_boundaries']),
          'finalize': finalize, 'native_gate': False, 'normal_time': True,
          'product_or_clone_resources_changed': False,
          'attempts': [{'stage': 'original import', 'rpc_calls': 0, 'captures': 0, 'failure': 'Missing pure host analysis dependency'},
                       {'stage': 'frozen dependency closure', 'captures': 0, 'restored': True, 'source_unchanged': True,
                        'failure': 'Direct RPC nested-object conversion replaced deep NBT tuples with transport placeholders'},
                       {'stage': 'frozen JSON readback adapter', 'captures': 6, 'restored': True, 'source_unchanged': True}],
          'watcher_startup_manifest_read_error_retained': True,
          'post_ready_exact_watcher_coverage_receipt': str(CONTROL / 'watcher-before-capture.json'),
          'qualification': False, 'pixel_acceptance': False,
          'limits': ['One editor pose and one near world pose per family only.',
                     'Missing mode was an empty-world route; occupancy transitions remain open.',
                     'Normal-TIME speed/direction, opacity, distant fog, other faces and full lifecycle remain open.',
                     'UI appearance is visibly present; exact native UI matrices and native appearance equivalence remain unqualified.',
                     'Game exited 0xC0000409 after the single normal-close request; normal exit is not accepted.']}
path = OUTPUT / 'runtime-review.json'
assert not path.exists()
path.write_text(json.dumps(review, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({key: review[key] for key in ('completed', 'restored', 'source_unchanged', 'elapsed_seconds',
                                              'source_contract_sha256', 'minimum_available_commit_bytes',
                                              'failed_memory_boundaries', 'qualification')}))

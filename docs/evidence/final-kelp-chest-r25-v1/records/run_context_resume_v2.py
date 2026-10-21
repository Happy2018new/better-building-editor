"""Run unchanged T04 semantics against exact frozen manifest bytes, preserving host EOL differences."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from frozen_guard import verify

manifest = verify()
PROJECT = Path(manifest['project'])
sys.path.insert(0, str(PROJECT / 'tools'))
import transform_missing_r23 as missing
original = HERE / 'run_context_final.py'
assert hashlib.sha256(original.read_bytes()).hexdigest() == manifest['evidence_hosts']['run_context_final.py']
receipt_path = HERE / 't04-resume-v2-receipt.json'
assert not receipt_path.exists()
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
           'original_driver_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
           'resume_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'original_preflight_failed': True, 'original_preflight_failed_before_rpc': True,
           'original_preflight_relative': 'behavior_pack/modern_projection/projection/rail_render_profile.py',
           'production_or_frozen_file_changes': False, 'source_binding': 'Every SOURCE_PATHS entry is checked against the exact frozen manifest SHA; complete frozen_guard also remains unchanged.',
           'host_comparisons': []}
for relative in missing.SOURCE_PATHS:
    host = (ROOT / relative).read_bytes()
    frozen = (PROJECT / relative).read_bytes()
    frozen_sha = hashlib.sha256(frozen).hexdigest()
    assert frozen_sha == manifest['files'][relative]
    receipt['host_comparisons'].append({'relative': relative,
        'host_sha256': hashlib.sha256(host).hexdigest(), 'frozen_sha256': frozen_sha,
        'exact_equal': host == frozen,
        'crlf_to_lf_equal': host.replace(b'\r\n', b'\n') == frozen.replace(b'\r\n', b'\n'),
        'host_bytes': len(host), 'frozen_bytes': len(frozen)})
source = original.read_text(encoding='utf8')
needle = "  source=(ROOT/relative).read_bytes()\n  assert (args.project/relative).read_bytes()==source,relative"
assert source.count(needle) == 1
replacement = "  source=(args.project/relative).read_bytes()\n  assert hashlib.sha256(source).hexdigest()==frozen['files'][relative],relative"
source = source.replace(needle, replacement)
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
try:
    exec(compile(source, str(original), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
finally:
    receipt['source_unchanged_after'] = verify() == manifest
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')

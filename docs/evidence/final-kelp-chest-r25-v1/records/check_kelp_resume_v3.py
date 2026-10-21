"""Preserve the first FAIL and classify only verified empty preview slots on resume."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from frozen_guard import verify
import public_entry_host

manifest = verify()
original = HERE / 'check_kelp.py'
assert hashlib.sha256(original.read_bytes()).hexdigest() == manifest['evidence_hosts']['check_kelp.py']
failed = json.loads((HERE / 'kelp/report.json').read_bytes())
assert not failed['completed'] and failed['restored'] and failed['source_unchanged']
assert 'public_entry_host.py' in failed['traceback'] and "row['controls']" in failed['traceback']
assert not (HERE / 'kelp-resume-v3').exists()
receipt = {'started_at': datetime.now(timezone.utc).isoformat(),
           'source_commit': manifest['source_commit'], 'source_unchanged': True,
           'original_driver_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
           'resume_wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'original_fail_report_sha256': hashlib.sha256((HERE / 'kelp/report.json').read_bytes()).hexdigest(),
           'classification': 'Only non-region-owner slots with name=None, no pending and no count/palette cells are excluded. Every active region owner must remain ready, named, current-signature/current-cache, and successfully submitted; active-owner coverage is exact.',
           'preserved_previous_resume': 'kelp-resume-v2/report.json', 'palette_layers_scope': 'part data indices 0:3 only; remaining tuple metadata excluded', 'production_changes': False, 'frozen_hosts_changed': False}
controls = public_entry_host.CONTROLS
assert controls.count('rows=[]') == 1
controls = controls.replace('rows=[]', 'rows=[]\nempty=[]\nactive_seen=set()')
needle = " part=s.tiles.parts[key]\n if not preview.ready(part['name']):continue"
replacement = """ part=s.tiles.parts[key]
 if part['name'] is None:
  counts=[sum(len(value) for value in layer.values()) for layer in part['data'][:3]]
  assert key not in s.tiles.region_owners,key
  assert part['count']==0 and not part['pending'] and counts==[0,0,0],(key,part['count'],part['pending'],counts)
  empty.append({'key':key,'name':part['name'],'count':part['count'],'pending':part['pending'],'palette_counts':counts,'region_owner':key in s.tiles.region_owners,'ready_none':preview.ready(None)})
  continue
 if key in s.tiles.region_owners:
  active_seen.add(key)
  assert preview.ready(part['name']) and not part['pending'],key
  assert part['signature']==s.preview_signature(),key
  assert part['bank'] in part.get('cache',{}) and part['cache'][part['bank']][0]==part['data'] and part['cache'][part['bank']][1]==part['name'] and part.get('source') in part['cache'][part['bank']][2],key
 if not preview.ready(part['name']):continue"""
assert controls.count(needle) == 1
controls = controls.replace(needle, replacement)
needle = "'models':rows})"
assert controls.count(needle) == 1
controls = controls.replace(needle, "'models':rows,'verified_empty_slots':empty})")
needle = "assert rows and all(row['current_signature'] for row in rows)"
assert controls.count(needle) == 1
controls = controls.replace(needle, needle + "\nassert active_seen==s.tiles.region_owners,(active_seen,s.tiles.region_owners)")
receipt['controls_payload_sha256'] = hashlib.sha256(controls.encode('utf8')).hexdigest()
public_entry_host.CONTROLS = controls
source = original.read_text(encoding='utf8')
needle = "OUT=HERE/'kelp';OUT.mkdir(exist_ok=False)"
assert source.count(needle) == 1
source = source.replace(needle, "OUT=HERE/'kelp-resume-v3';OUT.mkdir(exist_ok=False)")
(HERE / 'kelp-resume-v3-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
try:
    exec(compile(source, str(original), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
finally:
    receipt['source_unchanged_after'] = verify() == manifest
    (HERE / 'kelp-resume-v3-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')

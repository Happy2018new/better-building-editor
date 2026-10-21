"""Correct only the frozen host's sample census; keep the original failed preflight."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from frozen_guard import verify
manifest = verify()
import public_entry_host as entry
controls = entry.CONTROLS
assert controls.count('rows=[]') == 1
controls = controls.replace('rows=[]', 'rows=[]\nempty=[]\nactive_seen=set()')
needle = " part=s.tiles.parts[key]\n if not preview.ready(part['name']):continue"
replacement = """ part=s.tiles.parts[key]
 if part['name'] is None:
  counts=[sum(len(value) for value in layer.values()) for layer in part['data'][:3]]
  assert key not in s.tiles.region_owners,key
  assert part['count']==0 and not part['pending'] and counts==[0,0,0],(key,part['count'],part['pending'],counts)
  empty.append({'key':key,'name':None,'count':0,'pending':False,'palette_counts':counts,'region_owner':False})
  continue
 if key in s.tiles.region_owners:
  active_seen.add(key)
  assert preview.ready(part['name']) and not part['pending'],key
  assert part['signature']==s.preview_signature(),key
  assert part['bank'] in part.get('cache',{}) and part['cache'][part['bank']][0]==part['data'] and part['cache'][part['bank']][1]==part['name'] and part.get('source') in part['cache'][part['bank']][2],key
 if not preview.ready(part['name']):continue"""
assert controls.count(needle) == 1
controls = controls.replace(needle, replacement)
needle = "assert rows and all(row['current_signature'] for row in rows)"
assert controls.count(needle) == 1
controls = controls.replace(needle, needle + "\nassert active_seen==s.tiles.region_owners,(active_seen,s.tiles.region_owners)")
controls = controls.replace("'models':rows})", "'models':rows,'verified_empty_slots':empty})")
entry.CONTROLS = controls
original = HERE / 'check_t02.py'
assert hashlib.sha256(original.read_bytes()).hexdigest() == manifest['evidence_hosts']['check_t02.py']
receipt_path = HERE / 'check-resume-v2-receipt.json'
assert not receipt_path.exists()
source = original.read_text(encoding='utf8')
needle = "            samples = sum(foreground(cell)[0] != 'minecraft:stone' for cell in oracle.document.blocks.values())"
replacement = """            from collections import Counter
            counts = Counter(foreground(cell)[0] for cell in oracle.document.blocks.values())
            expected_samples = {'minecraft:oak_stairs': 8, 'minecraft:oak_slab': 2,
                                'minecraft:trapdoor': 8, 'minecraft:ladder': 4, 'minecraft:stone_button': 6}
            assert dict((key, counts[key]) for key in expected_samples) == expected_samples
            samples = sum(counts[key] for key in expected_samples)
            report['fixture_material_counts'] = dict(counts)"""
assert source.count(needle) == 1
source = source.replace(needle, replacement)
needle = "                row = {'operation': operation, 'data': base.transform(check, oracle, operation, evidence=report)}"
replacement = """                if operation in ('undo', 'redo'):
                    getattr(oracle, operation)()
                    check.run('assert s.action(s.editor.%s)\\n_result=True' % operation)
                    data = base.verify(check, oracle, 'T02 ' + operation, report)
                else:
                    data = base.transform(check, oracle, operation, evidence=report)
                row = {'operation': operation, 'data': data}"""
assert source.count(needle) == 1
source = source.replace(needle, replacement)
receipt = {'started_at': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
           'original_driver_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
           'resume_driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'first_preflight_failure': {'before_mc_launch': True, 'observed_nonstone': 32,
                                      'explanation': '28 direction samples plus four colored markers; nonstone count is not the direction count.'},
           'expected_direction_samples': {'oak_stairs': 8, 'oak_slab': 2, 'trapdoor': 8, 'ladder': 4, 'stone_button': 6},
           'frozen_original_unchanged': True, 'production_changes': False}
receipt['history_api_correction'] = 'Undo/redo use Editor.undo/redo and Session.action, as the existing frozen transform acceptance driver does; these are not named Editor.run tools.'
receipt['preview_control_correction'] = 'Reuse already verified strict active-owner coverage and verified empty non-owner classification from kelp v4; all active owners still require current cache/signature/native success.'
receipt['controls_payload_sha256'] = hashlib.sha256(controls.encode('utf8')).hexdigest()
receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
try:
    exec(compile(source, str(original), 'exec'), {'__name__': '__main__', '__file__': str(Path(__file__).resolve())})
finally:
    receipt['source_unchanged_after'] = verify() == manifest
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')

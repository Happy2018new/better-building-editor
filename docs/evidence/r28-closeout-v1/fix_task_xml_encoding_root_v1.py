"""Preserve console bytes and make the archived UTF-16 XML declaration accurate."""
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/evidence/r28-closeout-v1'
path = OUT / 'hibernation-task.xml'
raw = path.read_bytes()
# This exact output is entirely ASCII, avoiding guesses about the console code page.
text = raw.decode('ascii')
assert 'encoding="UTF-16"' in text
assert not (OUT / 'hibernation-task-export.stdout.bin').exists()
(OUT / 'hibernation-task-export.stdout.bin').write_bytes(raw)
encoded = text.encode('utf-16')
tree = ET.fromstring(encoded)
ns = {'t': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
assert tree.find('t:Triggers/t:TimeTrigger/t:StartBoundary', ns).text == '2026-10-23T08:00:00+08:00'
assert tree.find('t:Actions/t:Exec/t:Command', ns).text.lower() == r'c:\windows\system32\shutdown.exe'
assert tree.find('t:Actions/t:Exec/t:Arguments', ns).text == '/h'
path.write_bytes(encoded)
shutil.copyfile(__file__, OUT / Path(__file__).name)
receipt_path = OUT / 'root-review.json'
receipt = json.loads(receipt_path.read_bytes())
receipt['XML_archive_encoding_correction'] = {
    'original_console_bytes_preserved': 'hibernation-task-export.stdout.bin',
    'original_output_all_ASCII_with_UTF16_declaration': True,
    'archived_XML_encoded_UTF16_to_match_original_declaration': True,
    'decoded_text_unchanged': encoded.decode('utf-16') == text,
    'XML_parsed_and_trigger_command_arguments_verified': True,
    'scheduled_task_modified': False,
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf8')
entries = []
for item in sorted(OUT.rglob('*')):
    if item.is_file() and item.name != 'index.json':
        data = item.read_bytes()
        entries.append({'path': item.relative_to(OUT).as_posix(), 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest()})
(OUT / 'index.json').write_text(json.dumps({'entries': entries, 'hibernation_observed': False}, indent=2, sort_keys=True) + '\n', encoding='utf8')
print(json.dumps({'archive_files': len(entries) + 1, 'XML_parse_passed': True,
                  'original_console_bytes_preserved': True, 'scheduled_task_modified': False}))

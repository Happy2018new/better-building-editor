"""Retain the failed preparation and adapt patterns to the original line ending."""
import json
from pathlib import Path

work = Path(__file__).resolve().parent
original = work / 'prepare_candidate.py'
text = original.read_text('utf-8')
text = text.replace('candidate = raw.replace(old, new)',
    "line_end = b'\\r\\n' if b'\\r\\n' in raw else b'\\n'\n"
    "new = new.replace(b'\\r\\n', line_end)\ncandidate = raw.replace(old, new)")
text = text.replace('assert candidate.count(before) == 1',
    "before = before.replace(b'\\r\\n', line_end)\n"
    "after = after.replace(b'\\r\\n', line_end)\nassert candidate.count(before) == 1")
with (work/'prepare_candidate_v2.py').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(text)
with (work/'preparation-failure-v1.json').open('x', encoding='utf-8') as stream:
    json.dump(dict(phase='offline candidate preparation', MC_started=False,
        error='AssertionError: CRLF-only search pattern did not match original LF tool',
        original_script_retained=True, shared_tool_modified=False,
        candidate_or_binding_emitted_before_failure=False,
        next_script='prepare_candidate_v2.py'), stream, indent=2)

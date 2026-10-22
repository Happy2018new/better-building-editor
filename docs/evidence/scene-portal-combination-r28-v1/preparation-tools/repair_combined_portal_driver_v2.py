"""Fix only Py2 compile-label Unicode coercion; retain the first driver/results."""
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent / 'scene-portal-combination-v1'
source = here / 'verify_combined_portal_controls.py'
target = here / 'verify_combined_portal_controls_v2.py'
assert not target.exists()
data = source.read_bytes()
old = b"eval(compile(raw(relative), module.__file__, 'exec'), module.__dict__)"
new = b"eval(compile(raw(relative), relative, 'exec'), module.__dict__)"
assert data.count(old) == 1
target.write_bytes(data.replace(old, new, 1))
receipt = {'first_driver': source.name, 'first_driver_sha256': hashlib.sha256(data).hexdigest(),
    'second_driver': target.name, 'second_driver_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'actual_first_Py2_exit_code': 1,
    'first_failure': "UnicodeEncodeError at compile(raw(relative), module.__file__, 'exec')",
    'only_change': {'old': old.decode('ascii'), 'new': new.decode('ascii')},
    'why': 'Py2 compile coerces a Unicode absolute filename through ASCII. Use the exact ASCII relative source label; filesystem I/O still resolves actual combined paths.',
    'candidate_or_product_sources_modified': False, 'control_expectations_modified': False,
    'first_Py3_driver_succeeded': True, 'fresh_Py2_and_Py3_runs_required': True}
(here / 'portal-driver-preparation-history.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
print(json.dumps({'driver_ready': target.name, 'only_compile_label_changed': True}))

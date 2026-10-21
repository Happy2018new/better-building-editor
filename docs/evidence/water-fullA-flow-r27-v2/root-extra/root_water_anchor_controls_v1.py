"""Re-execute the reviewed coordinate controls with a fresh root receipt only."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / '.runtime/round-20261022/water-editor-anchor-candidate-v1/run_controls.py'
before = source.read_bytes()
target = source.parent / 'root-controls-v1.json'
assert not target.exists()
tree = ast.parse(before, filename=str(source))
changed = 0
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and node.value == 'controls-v1.json':
        node.value = target.name
        changed += 1
assert changed == 1
exec(compile(tree, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
assert source.read_bytes() == before
report = json.loads(target.read_bytes())
assert report['passed'] and len(report['coordinate_controls']) == 5
assert len(report['negative_controls']) == 10 and all(row['rejected'] for row in report['negative_controls'])
print(json.dumps({'root_control_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'reviewed_source_sha256': hashlib.sha256(before).hexdigest(),
    'only_AST_change': 'Fresh receipt filename', 'verification_logic_modified': False}))

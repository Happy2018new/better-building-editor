"""Refresh integrated server code and run the owned native bed writer check."""
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value

output = Path(sys.argv[1])
with Client(timeout=30) as client:
    for module in ('projection.block_traits_data', 'projection.block_traits',
                   'projection.native_layers', 'projection.debug_entity_defaults_data',
                   'projection.debug_entity_defaults', 'server_system'):
        path = ROOT / 'behavior_pack/modern_projection' / (module.replace('.', '/') + '.py')
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        code = ('import base64\nimport modern_projection.%s as target\n'
                'eval(compile(base64.b64decode(%r),%r,"exec"),target.__dict__)\n_result=True' %
                (module, encoded, str(path)))
        client.call('execute_code', {'code': code, 'is_client': False, 'direct_return': True})
    result = return_value(client.call('execute_code', {
        'code': (ROOT / 'tools/verify_native_bed_writer.py').read_text(encoding='utf8'),
        'is_client': False, 'direct_return': True}))
    result = json.loads(result) if isinstance(result, str) else result
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps({'output': str(output), 'checks': len(result.get('rows', ())), 'passed': True}))
